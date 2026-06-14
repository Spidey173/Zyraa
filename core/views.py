import logging
logger = logging.getLogger(__name__)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from .models import UserProfile, Post, Like, Comment, Follow, Bookmark, Notification, Story
from .forms import RegistrationForm, UserProfileForm, PostForm, CommentForm

def landing(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'core/landing.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            messages.success(request, "Registration successful! You can now log in.")
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'core/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'core/login.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('landing')

@login_required
def home(request):
    from .redis_utils import get_cached_feed, check_rate_limit, RedisKeys, redis_client
    
    # Rate Limiting check
    if not check_rate_limit(request.user.id, limit=60, prefix="home_feed"):
        return JsonResponse({'error': 'Rate limit exceeded. Please wait a minute.'}, status=429)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            
            # Map files if direct upload was bypassed (e.g., in unit tests)
            if not post.image_url and form.cleaned_data.get('image'):
                post.image = form.cleaned_data.get('image')
            if not post.video_url and form.cleaned_data.get('video'):
                post.video = form.cleaned_data.get('video')
                
            post.save()
            
            # Asynchronously fan out the new post to followers
            from .tasks import fanout_new_post_task
            fanout_new_post_task.delay(post.id)
            
            messages.success(request, "Post published successfully!")
            return redirect('home')
    else:
        form = PostForm()

    page = request.GET.get('page', '1')
    try:
        page = int(page)
    except ValueError:
        page = 1

    post_ids = get_cached_feed(request.user.id, page=page, page_size=5)
    
    if post_ids:
        posts_dict = {p.id: p for p in Post.objects.filter(id__in=post_ids).select_related('user', 'user__profile').prefetch_related('likes', 'comments')}
        posts_list = [posts_dict[pid] for pid in post_ids if pid in posts_dict]
    else:
        # Fallback
        followed_users = Follow.objects.filter(follower=request.user).values_list('following', flat=True)
        posts_query = Post.objects.filter(
            Q(user__in=followed_users) | Q(user=request.user)
        ).select_related('user', 'user__profile').prefetch_related('likes', 'comments')
        
        if not posts_query.exists():
            posts_query = Post.objects.all().select_related('user', 'user__profile').prefetch_related('likes', 'comments')
            
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        paginator = Paginator(posts_query, 5)
        try:
            posts_list = paginator.page(page).object_list
        except (EmptyPage, PageNotAnInteger):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'posts_html': ''})
            posts_list = []
            
        # Write first page to cache safely
        from .redis_utils import REDIS_AVAILABLE
        if page == 1 and REDIS_AVAILABLE and redis_client:
            try:
                pipeline = redis_client.pipeline()
                feed_key = RedisKeys.feed(request.user.id)
                for p in posts_query[:100]:
                    pipeline.zadd(feed_key, {p.id: p.created_at.timestamp()})
                pipeline.execute()
            except Exception as e:
                logger.warning(f"Failed to populate feed cache in Redis: {e}")

    # Add interactive flags for template compatibility
    post_ids_list = [post.id for post in posts_list]
    liked_post_ids = set(Like.objects.filter(user=request.user, post_id__in=post_ids_list).values_list('post_id', flat=True))
    bookmarked_post_ids = set(Bookmark.objects.filter(user=request.user, post_id__in=post_ids_list).values_list('post_id', flat=True))
    for post in posts_list:
        post.is_liked_by_user = post.id in liked_post_ids
        post.is_bookmarked_by_user = post.id in bookmarked_post_ids

    # Dynamic suggestions
    followed_users = Follow.objects.filter(follower=request.user).values_list('following', flat=True)
    suggested_users = User.objects.exclude(
        id__in=followed_users
    ).exclude(id=request.user.id).select_related('profile')[:5]

    # Real Stories logic
    import datetime
    from django.utils import timezone
    from collections import defaultdict
    import json

    active_stories = Story.objects.filter(
        created_at__gte=timezone.now() - datetime.timedelta(hours=24)
    ).select_related('user', 'user__profile').order_by('created_at')

    stories_by_user = defaultdict(list)
    for story in active_stories:
        stories_by_user[story.user].append({
            'id': story.id,
            'image_url': story.image.url if story.image else None,
            'video_url': story.video.url if story.video else None,
            'music_url': story.music.url if story.music else None,
            'caption': story.caption,
            'created_at': story.created_at.strftime('%I:%M %p')
        })

    story_bubbles = []
    story_bubbles_json = []
    for user, user_stories in stories_by_user.items():
        story_bubbles.append({
            'user': user,
            'stories': user_stories
        })
        story_bubbles_json.append({
            'username': user.username,
            'profile_pic': user.profile.profile_pic.url if user.profile.profile_pic else None,
            'stories': user_stories
        })

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'core/post_list_partial.html', {'posts': posts_list})

    context = {
        'form': form,
        'posts': posts_list,
        'suggested_users': suggested_users,
        'story_users': story_bubbles,
        'story_bubbles_json': json.dumps(story_bubbles_json),
    }
    return render(request, 'core/home.html', context)

@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post.objects.select_related('user', 'user__profile'), id=post_id)
    comments = post.comments.select_related('user', 'user__profile')
    is_liked = post.likes.filter(user=request.user).exists()

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.post = post
            comment.save()
            messages.success(request, "Comment added.")
            return redirect('post_detail', post_id=post.id)
    else:
        form = CommentForm()

    context = {
        'post': post,
        'comments': comments,
        'is_liked': is_liked,
        'form': form,
    }
    return render(request, 'core/post_detail.html', context)

@login_required
def like_post(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        
        from .redis_utils import increment_like_count
        if not created:
            like.delete() # Unlike if already liked
            liked = False
            increment_like_count(post.id, -1)
        else:
            liked = True
            increment_like_count(post.id, 1)
            # Create Activity notification via Celery
            if post.user != request.user:
                from .tasks import create_notification_task
                create_notification_task.delay(request.user.id, post.user.id, 'like', post.id)
        
        # Real-time Channels broadcast
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"post_likes_{post.id}",
                {
                    "type": "send_like_update",
                    "likes_count": post.likes_count
                }
            )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'liked': liked,
                'likes_count': post.likes_count
            })
        
        # Redirect back to previous page
        next_url = request.META.get('HTTP_REFERER', 'home')
        return redirect(next_url)
    return redirect('home')

@login_required
def comment_post(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.post = post
            comment.save()
            
            # Create Activity notification via Celery
            if post.user != request.user:
                from .tasks import create_notification_task
                create_notification_task.delay(request.user.id, post.user.id, 'comment', post.id)
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                profile_pic_url = comment.user.profile.profile_pic.url if comment.user.profile.profile_pic else None
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'id': comment.id,
                        'username': comment.user.username,
                        'user_url': f'/user/{comment.user.username}/',
                        'profile_pic': profile_pic_url,
                        'content': comment.content,
                        'created_at': 'Just now'
                    }
                })
            messages.success(request, "Comment added.")
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        
        next_url = request.META.get('HTTP_REFERER', 'post_detail')
        if next_url == 'post_detail':
            return redirect('post_detail', post_id=post.id)
        return redirect(next_url)
    return redirect('home')

@login_required
def user_profile(request, username):
    profile_user = get_object_or_404(User.objects.select_related('profile'), username=username)
    posts = profile_user.posts.all().prefetch_related('likes', 'comments')
    
    is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()
    
    # Check if we are viewing our own profile
    is_self = (request.user == profile_user)
    
    profile_form = None
    if is_self:
        if request.method == 'POST':
            profile_form = UserProfileForm(request.POST, request.FILES, instance=profile_user.profile)
            if profile_form.is_valid():
                profile = profile_form.save(commit=False)
                if not profile.profile_pic_url and profile_form.cleaned_data.get('profile_pic'):
                    profile.profile_pic = profile_form.cleaned_data.get('profile_pic')
                profile.save()
                messages.success(request, "Profile updated successfully!")
                return redirect('user_profile', username=username)
        else:
            profile_form = UserProfileForm(instance=profile_user.profile)

    saved_posts = []
    if is_self:
        saved_posts = list(Post.objects.filter(bookmarks__user=profile_user).select_related('user', 'user__profile').prefetch_related('likes', 'comments'))
        saved_post_ids = [post.id for post in saved_posts]
        liked_saved_ids = set(Like.objects.filter(user=request.user, post_id__in=saved_post_ids).values_list('post_id', flat=True))
        for post in saved_posts:
            post.is_liked_by_user = post.id in liked_saved_ids
            post.is_bookmarked_by_user = True

    posts = list(posts)
    post_ids = [post.id for post in posts]
    liked_post_ids = set(Like.objects.filter(user=request.user, post_id__in=post_ids).values_list('post_id', flat=True))
    bookmarked_post_ids = set(Bookmark.objects.filter(user=request.user, post_id__in=post_ids).values_list('post_id', flat=True))
    for post in posts:
        post.is_liked_by_user = post.id in liked_post_ids
        post.is_bookmarked_by_user = post.id in bookmarked_post_ids

    context = {
        'profile_user': profile_user,
        'posts': posts,
        'saved_posts': saved_posts,
        'is_following': is_following,
        'is_self': is_self,
        'profile_form': profile_form,
    }
    return render(request, 'core/user_profile.html', context)

@login_required
def follow_user(request, username):
    if request.method == 'POST':
        target_user = get_object_or_404(User, username=username)
        is_following = False
        if target_user != request.user:
            follow, created = Follow.objects.get_or_create(follower=request.user, following=target_user)
            
            from .redis_utils import increment_follower_stats
            if not created:
                follow.delete() # Unfollow
                is_following = False
                increment_follower_stats(request.user.id, target_user.id, -1)
            else:
                is_following = True
                increment_follower_stats(request.user.id, target_user.id, 1)
                # Create Activity notification via Celery
                from .tasks import create_notification_task
                create_notification_task.delay(request.user.id, target_user.id, 'follow')
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'following': is_following,
                'followers_count': target_user.profile.followers_count,
                'following_count': target_user.profile.following_count
            })

        next_url = request.META.get('HTTP_REFERER', 'user_profile')
        if 'user' in next_url:
            return redirect('user_profile', username=username)
        return redirect(next_url)
    return redirect('home')

@login_required
def followers_list(request, username):
    profile_user = get_object_or_404(User, username=username)
    followers = Follow.objects.filter(following=profile_user).select_related('follower', 'follower__profile')
    
    # Check follow state for each follower from current user perspective
    followers = list(followers)
    follower_users = [follow.follower for follow in followers]
    followed_user_ids = set(Follow.objects.filter(follower=request.user, following__in=follower_users).values_list('following_id', flat=True))
    for follow in followers:
        follow.follower.is_followed_by_user = follow.follower.id in followed_user_ids
        
    context = {
        'profile_user': profile_user,
        'followers': followers,
    }
    return render(request, 'core/followers_list.html', context)

@login_required
def following_list(request, username):
    profile_user = get_object_or_404(User, username=username)
    following_relations = Follow.objects.filter(follower=profile_user).select_related('following', 'following__profile')
    
    # Check follow state for each following user from current user perspective
    following_relations = list(following_relations)
    following_users = [relation.following for relation in following_relations]
    followed_user_ids = set(Follow.objects.filter(follower=request.user, following__in=following_users).values_list('following_id', flat=True))
    for relation in following_relations:
        relation.following.is_followed_by_user = relation.following.id in followed_user_ids
        
    context = {
        'profile_user': profile_user,
        'following_relations': following_relations,
    }
    return render(request, 'core/following_list.html', context)

@login_required
def explore_view(request):
    query = request.GET.get('q', '').strip()
    users_results = []
    posts_results = []
    
    if query:
        users_results = User.objects.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        ).exclude(id=request.user.id).select_related('profile')
        
        posts_results = Post.objects.filter(
            caption__icontains=query
        ).select_related('user', 'user__profile').prefetch_related('likes', 'comments')
        
        users_results = list(users_results)
        followed_user_ids = set(Follow.objects.filter(follower=request.user, following__in=users_results).values_list('following_id', flat=True))
        for u in users_results:
            u.is_followed_by_user = u.id in followed_user_ids
            
        posts_results = list(posts_results)
        post_ids = [post.id for post in posts_results]
        liked_post_ids = set(Like.objects.filter(user=request.user, post_id__in=post_ids).values_list('post_id', flat=True))
        for post in posts_results:
            post.is_liked_by_user = post.id in liked_post_ids
    else:
        from django.db.models import Count
        posts_results = list(Post.objects.annotate(
            num_likes=Count('likes')
        ).order_by('-num_likes', '-created_at').select_related('user', 'user__profile').prefetch_related('likes', 'comments'))
        
        post_ids = [post.id for post in posts_results]
        liked_post_ids = set(Like.objects.filter(user=request.user, post_id__in=post_ids).values_list('post_id', flat=True))
        for post in posts_results:
            post.is_liked_by_user = post.id in liked_post_ids

    context = {
        'query': query,
        'users_results': users_results,
        'posts': posts_results,
    }
    return render(request, 'core/explore.html', context)

@login_required
def reels_view(request):
    # Filter posts that have a video file
    reels = Post.objects.exclude(video_url='').exclude(video_url__isnull=True).select_related('user', 'user__profile').prefetch_related('likes', 'comments')
    reels = list(reels)
    post_ids = [post.id for post in reels]
    liked_post_ids = set(Like.objects.filter(user=request.user, post_id__in=post_ids).values_list('post_id', flat=True))
    bookmarked_post_ids = set(Bookmark.objects.filter(user=request.user, post_id__in=post_ids).values_list('post_id', flat=True))
    for post in reels:
        post.is_liked_by_user = post.id in liked_post_ids
        post.is_bookmarked_by_user = post.id in bookmarked_post_ids
    return render(request, 'core/reels.html', {'posts': reels})

@login_required
def toggle_bookmark(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)
        if not created:
            bookmark.delete()
            bookmarked = False
        else:
            bookmarked = True
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'bookmarked': bookmarked})
        
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    return redirect('home')

@login_required
def notifications_view(request):
    notifications = request.user.notifications.all().select_related('sender', 'sender__profile', 'post')
    notifications.update(is_read=True)
    
    # Reset unread count in Redis safely
    from .redis_utils import redis_client, RedisKeys, REDIS_AVAILABLE
    if REDIS_AVAILABLE and redis_client:
        try:
            redis_client.delete(RedisKeys.unread_notifications(request.user.id))
        except Exception as e:
            logger.warning(f"Failed to reset notification count in Redis: {e}")
    
    return render(request, 'core/notifications.html', {'notifications': notifications})

@login_required
def delete_post(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        if post.user == request.user:
            post.delete()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            messages.success(request, "Post deleted successfully.")
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
            messages.error(request, "You cannot delete this post.")
    return redirect('home')

@login_required
def create_story_view(request):
    if request.method == 'POST':
        image_url = request.POST.get('cloudinary_image_url')
        video_url = request.POST.get('cloudinary_video_url')
        music_url = request.POST.get('cloudinary_music_url')
        
        image_file = request.FILES.get('image')
        video_file = request.FILES.get('video')
        music_file = request.FILES.get('music')
        caption = request.POST.get('caption', '')
        
        if image_url or video_url or image_file or video_file:
            story = Story.objects.create(
                user=request.user,
                caption=caption
            )
            
            if image_url:
                story.image_url = image_url
            elif image_file:
                story.image = image_file
                
            if video_url:
                story.video_url = video_url
            elif video_file:
                story.video = video_file
                
            if music_url:
                story.music_url = music_url
            elif music_file:
                story.music = music_file
                
            story.save()
            messages.success(request, "Story shared successfully!")
        else:
            messages.error(request, "You must upload either a photo or video to share a story.")
    return redirect('home')

import time
import cloudinary.utils

@login_required
def get_cloudinary_signature(request):
    """
    Returns secure credentials for client-side direct uploading to Cloudinary.
    """
    timestamp = int(time.time())
    params = {
        'timestamp': timestamp,
        'folder': 'zyra_uploads',
    }
    
    signature = cloudinary.utils.api_sign_request(
        params,
        cloudinary.config().api_secret
    )
    
    return JsonResponse({
        'signature': signature,
        'timestamp': timestamp,
        'api_key': cloudinary.config().api_key,
        'cloud_name': cloudinary.config().cloud_name,
        'folder': 'zyra_uploads',
    })
