from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from core.models import UserProfile, Post, Like, Comment, Follow, Bookmark, Notification
from core.forms import RegistrationForm, PostForm

class ZyraModelTests(TestCase):
    def setUp(self):
        from core.redis_utils import redis_client, REDIS_AVAILABLE
        if REDIS_AVAILABLE and redis_client:
            redis_client.flushdb()
        self.user1 = User.objects.create_user(username='userone', password='testpassword123', email='userone@example.com')
        self.user2 = User.objects.create_user(username='usertwo', password='testpassword123', email='usertwo@example.com')

    def test_profile_creation_signal(self):
        self.assertIsNotNone(self.user1.profile)
        self.assertEqual(self.user1.profile.bio, "")

    def test_post_creation_and_properties(self):
        post = Post.objects.create(user=self.user1, caption="Test post caption")
        self.assertEqual(post.likes_count, 0)
        self.assertEqual(post.comments_count, 0)
        self.assertEqual(str(post), f"Post by userone at {post.created_at}")

    def test_like_system(self):
        post = Post.objects.create(user=self.user1, caption="Test post caption")
        like = Like.objects.create(user=self.user2, post=post)
        self.assertEqual(post.likes_count, 1)

    def test_comment_system(self):
        post = Post.objects.create(user=self.user1, caption="Test post caption")
        comment = Comment.objects.create(user=self.user2, post=post, content="Cool post!")
        self.assertEqual(post.comments_count, 1)
        self.assertEqual(comment.content, "Cool post!")

    def test_follow_system(self):
        Follow.objects.create(follower=self.user1, following=self.user2)
        self.assertEqual(self.user1.profile.following_count, 1)
        self.assertEqual(self.user2.profile.followers_count, 1)


class ZyraViewTests(TestCase):
    def setUp(self):
        from core.redis_utils import redis_client, REDIS_AVAILABLE
        if REDIS_AVAILABLE and redis_client:
            redis_client.flushdb()
        self.client = Client()
        self.user1 = User.objects.create_user(username='userone', password='testpassword123')
        self.user2 = User.objects.create_user(username='usertwo', password='testpassword123')
        self.post = Post.objects.create(user=self.user2, caption="Hello world")

    def test_landing_page_unauthenticated(self):
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connect without boundaries")

    def test_landing_page_redirects_when_authenticated(self):
        self.client.login(username='userone', password='testpassword123')
        response = self.client.get(reverse('landing'))
        self.assertRedirects(response, reverse('home'))

    def test_login_flow(self):
        response = self.client.post(reverse('login'), {
            'username': 'userone',
            'password': 'testpassword123'
        })
        self.assertRedirects(response, reverse('home'))

    def test_post_creation_view(self):
        self.client.login(username='userone', password='testpassword123')
        response = self.client.post(reverse('home'), {
            'caption': 'My first automated post'
        })
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(Post.objects.filter(caption='My first automated post').exists())

    def test_post_creation_view_with_video(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username='userone', password='testpassword123')
        video_data = b'fake video file content'
        video_file = SimpleUploadedFile('test.mp4', video_data, content_type='video/mp4')
        response = self.client.post(reverse('home'), {
            'caption': 'Post with video',
            'video': video_file
        })
        self.assertRedirects(response, reverse('home'))
        post = Post.objects.get(caption='Post with video')
        self.assertTrue(post.video.name.endswith('.mp4'))
        # Clean up files created during test
        post.video.delete()

    def test_like_post_view(self):
        self.client.login(username='userone', password='testpassword123')
        # POST to toggle like
        response = self.client.post(reverse('like_post', args=[self.post.id]))
        self.assertEqual(Like.objects.filter(user=self.user1, post=self.post).count(), 1)
        
        # POST again to toggle unlike
        self.client.post(reverse('like_post', args=[self.post.id]))
        self.assertEqual(Like.objects.filter(user=self.user1, post=self.post).count(), 0)

    def test_follow_user_view(self):
        self.client.login(username='userone', password='testpassword123')
        response = self.client.post(reverse('follow_user', args=[self.user2.username]))
        self.assertTrue(Follow.objects.filter(follower=self.user1, following=self.user2).exists())

    def test_like_post_view_ajax(self):
        self.client.login(username='userone', password='testpassword123')
        response = self.client.post(
            reverse('like_post', args=[self.post.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertTrue(data['liked'])
        self.assertEqual(data['likes_count'], 1)

    def test_comment_post_view_ajax(self):
        self.client.login(username='userone', password='testpassword123')
        response = self.client.post(
            reverse('comment_post', args=[self.post.id]),
            {'content': 'AJAX comment content'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['comment']['content'], 'AJAX comment content')

    def test_explore_view_no_query(self):
        self.client.login(username='userone', password='testpassword123')
        response = self.client.get(reverse('explore'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/explore.html')
        self.assertContains(response, 'Explore Zyra')

    def test_explore_view_search_query(self):
        self.client.login(username='userone', password='testpassword123')
        response = self.client.get(reverse('explore'), {'q': 'world'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hello world')

    def test_reels_view(self):
        self.client.login(username='userone', password='testpassword123')
        post_with_vid = Post.objects.create(user=self.user2, caption="Reel caption", video="posts/videos/fake.mp4")
        response = self.client.get(reverse('reels'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/reels.html')
        self.assertContains(response, 'Reel caption')

    def test_toggle_bookmark_ajax(self):
        self.client.login(username='userone', password='testpassword123')
        response = self.client.post(
            reverse('toggle_bookmark', args=[self.post.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['bookmarked'])
        self.assertTrue(Bookmark.objects.filter(user=self.user1, post=self.post).exists())

    def test_notifications_view(self):
        self.client.login(username='userone', password='testpassword123')
        self.client.post(reverse('follow_user', args=[self.user2.username]))
        self.client.login(username='usertwo', password='testpassword123')
        response = self.client.get(reverse('notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/notifications.html')
        self.assertContains(response, 'userone')

    def test_delete_post_ajax(self):
        # Login as owner (user2)
        self.client.login(username='usertwo', password='testpassword123')
        response = self.client.post(
            reverse('delete_post', args=[self.post.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertFalse(Post.objects.filter(id=self.post.id).exists())

    def test_delete_post_unauthorized(self):
        # Login as non-owner (user1) trying to delete user2's post
        self.client.login(username='userone', password='testpassword123')
        response = self.client.post(
            reverse('delete_post', args=[self.post.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['success'])
        self.assertTrue(Post.objects.filter(id=self.post.id).exists())

    def test_create_story(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username='userone', password='testpassword123')
        image_data = b'fake image data'
        image_file = SimpleUploadedFile('story.jpg', image_data, content_type='image/jpeg')
        music_data = b'fake music data'
        music_file = SimpleUploadedFile('song.mp3', music_data, content_type='audio/mpeg')
        
        response = self.client.post(reverse('create_story'), {
            'image': image_file,
            'music': music_file,
            'caption': 'My image story with music'
        })
        self.assertRedirects(response, reverse('home'))
        from core.models import Story
        story = Story.objects.get(caption='My image story with music')
        self.assertEqual(story.user, self.user1)
        self.assertTrue(story.image.name.endswith('.jpg'))
        self.assertTrue(story.music.name.endswith('.mp3'))
        
        # Clean up files created during test
        story.image.delete()
        story.music.delete()

class ZyraRedisIntegrationTests(TestCase):
    def setUp(self):
        from core.redis_utils import redis_client
        self.redis = redis_client
        if self.redis:
            self.redis.flushdb()
        self.user1 = User.objects.create_user(username='tester1', password='testpassword123')
        self.user2 = User.objects.create_user(username='tester2', password='testpassword123')
        self.post = Post.objects.create(user=self.user1, caption="Integration Test Post")

    def tearDown(self):
        if self.redis:
            self.redis.flushdb()

    def test_likes_count_caching(self):
        from core.redis_utils import increment_like_count, get_like_count
        
        # Test increment
        new_count = increment_like_count(self.post.id, 1)
        self.assertEqual(new_count, 1)
        
        # Test get_like_count using cache
        cached_count = get_like_count(self.post.id, lambda: 999) # 999 is fallback, should not be called
        self.assertEqual(cached_count, 1)
        
        # Test get_like_count fallback if not cached
        if self.redis:
            self.redis.delete(f"post:{self.post.id}:stats")
        fallback_count = get_like_count(self.post.id, lambda: 5)
        self.assertEqual(fallback_count, 5)

    def test_follower_stats_caching(self):
        from core.redis_utils import increment_follower_stats, get_user_stats
        
        # Populate initial stats cache (0, 0)
        get_user_stats(self.user1.id, lambda: (0, 0))
        get_user_stats(self.user2.id, lambda: (0, 0))
        
        increment_follower_stats(self.user1.id, self.user2.id, 1)
        
        # user1 following count should be 1. user2 followers count should be 1.
        followers, following = get_user_stats(self.user1.id, lambda: (10, 10))
        self.assertEqual(following, 1)
        self.assertEqual(followers, 0)
        
        followers2, following2 = get_user_stats(self.user2.id, lambda: (10, 10))
        self.assertEqual(followers2, 1)
        self.assertEqual(following2, 0)

    def test_rate_limiting(self):
        from core.redis_utils import check_rate_limit
        
        # First 3 requests should be allowed
        self.assertTrue(check_rate_limit(self.user1.id, limit=3, prefix="test_limit"))
        self.assertTrue(check_rate_limit(self.user1.id, limit=3, prefix="test_limit"))
        self.assertTrue(check_rate_limit(self.user1.id, limit=3, prefix="test_limit"))
        
        # 4th request should be blocked
        self.assertFalse(check_rate_limit(self.user1.id, limit=3, prefix="test_limit"))

    def test_feed_caching_and_fanout(self):
        from core.redis_utils import get_cached_feed
        from core.tasks import fanout_new_post_task
        
        # Make user2 follow user1
        Follow.objects.create(follower=self.user2, following=self.user1)
        
        # Trigger fanout
        fanout_new_post_task(self.post.id)
        
        # Check user2 cached feed contains post.id
        cached_posts = get_cached_feed(self.user2.id, page=1, page_size=5)
        self.assertIn(self.post.id, cached_posts)

    def test_presence_heartbeat_and_pruning(self):
        from core.consumers import update_user_presence, remove_user_presence
        from core.tasks import prune_presence_task
        from core.redis_utils import redis_client
        import time
        from asgiref.sync import async_to_sync
        
        # Update presence
        async_to_sync(update_user_presence)(self.user1.username)
        
        # Check ZSET score
        score = self.redis.zscore("presence_users", self.user1.username)
        self.assertIsNotNone(score)
        
        # Run pruning - user should NOT be pruned as score is fresh
        pruned_count = prune_presence_task()
        self.assertEqual(pruned_count, 0)
        self.assertIsNotNone(self.redis.zscore("presence_users", self.user1.username))
        
        # Manually set score to be old (expired)
        self.redis.zadd("presence_users", {self.user1.username: time.time() - 35.0})
        
        # Run pruning - user should now be pruned
        pruned_count = prune_presence_task()
        self.assertEqual(pruned_count, 1)
        self.assertIsNone(self.redis.zscore("presence_users", self.user1.username))

    def test_fanout_chunking_execution(self):
        from core.tasks import fanout_new_post_task
        
        # Create many followers for user1 to verify chunking logic works without issues
        users = [User(username=f'chunk_follower_{i}', password='p') for i in range(15)]
        User.objects.bulk_create(users)
        
        created_users = User.objects.filter(username__startswith='chunk_follower_')
        follows = [Follow(follower=u, following=self.user1) for u in created_users]
        Follow.objects.bulk_create(follows)
        
        # Call fanout
        fanout_new_post_task(self.post.id)
        
        # Verify feed contains the post for one of the followers
        from core.redis_utils import get_cached_feed
        cached_posts = get_cached_feed(created_users[0].id, page=1, page_size=5)
        self.assertIn(self.post.id, cached_posts)

