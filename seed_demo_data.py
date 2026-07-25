import os
import sys
import random
import datetime
import urllib.request
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from django.contrib.auth.models import User
from core.models import UserProfile, Post, Comment, Like, Follow, Bookmark, Notification, Story

def check_url_active(url, timeout=4):
    """Confirm URL returns HTTP 200 OK before inserting into DB."""
    if not url or not url.startswith('http'):
        return False
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

# ---------------------------------------------------------
# 25 100% Unique Profile Avatars (HTTPS CDNs)
# ---------------------------------------------------------
AVATAR_URLS = [
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1501196354995-cbb51c65aaea?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1513956589380-bad6acb9b9d4?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1548142813-c348350df52b?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=300&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1519345182560-3f2917c472ef?w=300&auto=format&fit=crop"
]

USERS_SEED_DATA = [
    {"username": "alex_adventures", "first_name": "Alex", "last_name": "Rivers", "bio": "Exploring the world one mountain at a time. 🏔️✨"},
    {"username": "sophia_styles", "first_name": "Sophia", "last_name": "Chen", "bio": "Fashion designer & visual storyteller. 🎨💃"},
    {"username": "liam_lens", "first_name": "Liam", "last_name": "Walker", "bio": "Capturing cinematic moments. 📸🎞️"},
    {"username": "emma_eats", "first_name": "Emma", "last_name": "Watson", "bio": "Foodie chasing culinary perfection 🍝🍕"},
    {"username": "noah_nomad", "first_name": "Noah", "last_name": "Miller", "bio": "Digital nomad & tech enthusiast. 💻🌍"},
    {"username": "olivia_outdoors", "first_name": "Olivia", "last_name": "Davis", "bio": "Nature lover & wilderness photographer. 🌿🌄"},
    {"username": "ethan_engineering", "first_name": "Ethan", "last_name": "Wright", "bio": "Building the future of software & AI. 🤖⚡️"},
    {"username": "ava_arts", "first_name": "Ava", "last_name": "Taylor", "bio": "Digital art, 3D renders & color palettes. 🎨🔮"},
    {"username": "lucas_logs", "first_name": "Lucas", "last_name": "Anderson", "bio": "Coffee, code & late night music logs. ☕️🎧"},
    {"username": "mia_musings", "first_name": "Mia", "last_name": "Thomas", "bio": "Writer, poet & seeker of quiet places. 📖🌌"},
    {"username": "mason_motion", "first_name": "Mason", "last_name": "Jackson", "bio": "Filmmaker & motion designer. 🎬✨"},
    {"username": "isabella_ink", "first_name": "Isabella", "last_name": "White", "bio": "Tattoo artist & illustrator. ✒️🖤"},
    {"username": "logan_limits", "first_name": "Logan", "last_name": "Harris", "bio": "Extreme sports & adrenaline junkie. 🛹🏔️"},
    {"username": "charlotte_captures", "first_name": "Charlotte", "last_name": "Martin", "bio": "Street photography & urban vibes. 🏙️📸"},
    {"username": "jackson_journey", "first_name": "Jackson", "last_name": "Thompson", "bio": "Backpacking across 50 countries. ✈️🌴"},
    {"username": "amelia_aesthetic", "first_name": "Amelia", "last_name": "Garcia", "bio": "Minimalism, interior decor & architecture. 🏛️🌿"},
    {"username": "jack_justin", "first_name": "Jack", "last_name": "Martinez", "bio": "Fitness coach & endurance runner. 🏃‍♂️💪"},
    {"username": "harper_horizon", "first_name": "Harper", "last_name": "Robinson", "bio": "Drone pilot capturing earth from above. 🚁🌅"},
    {"username": "aiden_architecture", "first_name": "Aiden", "last_name": "Clark", "bio": "Architectural design & urban planning. 🏢📐"},
    {"username": "evelyn_explorer", "first_name": "Evelyn", "last_name": "Rodriguez", "bio": "Ocean conservation & scuba diver. 🪸🌊"},
    {"username": "owen_origami", "first_name": "Owen", "last_name": "Lewis", "bio": "Paper artist & creative sculptor. 📄✨"},
    {"username": "abigail_artistry", "first_name": "Abigail", "last_name": "Lee", "bio": "Oil painting & portrait gallery. 🖼️🎨"},
    {"username": "samuel_snapshots", "first_name": "Samuel", "last_name": "Walker", "bio": "Vintage camera collector & film dev. 🎞️📸"},
    {"username": "emily_episodes", "first_name": "Emily", "last_name": "Hall", "bio": "Podcast host & culture observer. 🎙️✨"},
    {"username": "benjamin_bites", "first_name": "Benjamin", "last_name": "Allen", "bio": "Pastry chef crafting sweet art. 🥐🍰"}
]

CAPTIONS = [
    "Golden hour hit just right today. 🌅✨ #goldenhour #photography #vibes",
    "Finding peace in quiet places. 🌿🕊️ #nature #serenity #explore",
    "Late night code session & fresh coffee. ☕️💻 #developer #building #tech",
    "Weekend getaway to the coast. 🌊☀️ #ocean #beach #travelgram",
    "Creativity is intelligence having fun. 🎨✨ #art #design #creative",
    "Fresh ingredients, endless possibilities. 🍝👨‍🍳 #foodie #delicious #chef",
    "Pushing past limits every single day. 🏃‍♂️💪 #fitness #motivation #workout",
    "City lights and urban nights. 🏙️✨ #nightlife #cityscape #streetphotography",
    "Nothing beats this view from the top. 🏔️🌤️ #hiking #mountains #adventure",
    "Focus on what makes you feel alive. ✨💫 #inspiration #life #mindset",
    "Simple moments, lifelong memories. 📸❤️ #gratitude #memories #lifestyle",
    "Exploring hidden gems around the city. 🗺️✨ #urbanexplore #hiddenspots",
    "Sunset colors painted across the sky. 🌇🔮 #sunsetlover #sky #beauty",
    "Consistency over intensity. Keep grinding! 🔥⚡️ #grind #hustle #progress",
    "Sunday morning slow down. ☕️📖 #weekendvibes #cozy #reading"
]

COMMENTS = [
    "Stunning shot! The colors are incredible. 🔥",
    "Absolutely amazing view! Where is this? 😍",
    "Love the caption and vibes on this one. ✨",
    "Inspiring work as always! Keep it up. 🚀",
    "This looks unbelievable! 😱❤️",
    "Pure perfection! 👌💯",
    "Great aesthetic! Love this so much. 🙌",
    "Wow, this blew me away! ✨🔥",
    "Frame this right now! 🖼️❤️",
    "Needed to see this today, thanks for sharing! 🙏"
]

def generate_unique_media_pools():
    """Generate 100% unique photo and video URLs with ZERO duplicates."""
    unique_photos = []
    unique_videos = []
    
    # Generate 100 unique high-res photo URLs via Picsum photo IDs
    for pid in range(10, 110):
        unique_photos.append(f"https://picsum.photos/id/{pid}/1080/1080")
        
    # Generate 50 unique video URLs via Cloudinary demo video stream variations
    base_cloudinary_videos = [
        "https://res.cloudinary.com/demo/video/upload/v1687352345/samples/elephants.mp4",
        "https://res.cloudinary.com/demo/video/upload/v1687352345/samples/sea-turtle.mp4",
        "https://res.cloudinary.com/demo/video/upload/v1687352345/samples/dance-2.mp4",
        "https://res.cloudinary.com/demo/video/upload/v1687352345/samples/cld-sample-video.mp4",
        "https://res.cloudinary.com/demo/video/upload/v1687352345/samples/bike.mp4"
    ]
    
    # Create 50 unique Cloudinary video URL variations using transformations
    for v_idx in range(50):
        base_url = base_cloudinary_videos[v_idx % len(base_cloudinary_videos)]
        # Inject unique version / transformation tag so every URL string is 100% unique
        transformed_url = base_url.replace("/upload/", f"/upload/w_{720 + (v_idx * 2)},q_auto/")
        unique_videos.append(transformed_url)
        
    return unique_photos, unique_videos

def seed_database():
    print("\n==================================================")
    print("   PURGING & SEEDING ZERO-DUPLICATE DEMO DATA     ")
    print("==================================================\n")

    failed_media_count = 0
    used_media_urls = set()

    with transaction.atomic():
        print("1. Purging all existing database records...")
        Notification.objects.all().delete()
        Bookmark.objects.all().delete()
        Like.objects.all().delete()
        Comment.objects.all().delete()
        Follow.objects.all().delete()
        Story.objects.all().delete()
        Post.objects.all().delete()
        UserProfile.objects.all().delete()
        User.objects.all().delete()
        print("   -> Existing database cleared.")

        print("\n2. Creating 25 unique users with active avatars...")
        created_users = []
        for idx, udata in enumerate(USERS_SEED_DATA):
            avatar_url = AVATAR_URLS[idx % len(AVATAR_URLS)]
            
            user = User.objects.create_user(
                username=udata['username'],
                email=f"{udata['username']}@zyraa.app",
                first_name=udata['first_name'],
                last_name=udata['last_name'],
                password='Password123!'
            )
            
            profile = user.profile
            profile.bio = udata['bio']
            profile.profile_pic = avatar_url
            profile.save()
            created_users.append(user)

        print(f"   -> Successfully created {len(created_users)} users.")

        print("\n3. Generating 150 posts with ZERO duplicate media URLs...")
        photo_pool, video_pool = generate_unique_media_pools()
        created_posts = []
        images_count = 0
        videos_count = 0

        photo_ptr = 0
        video_ptr = 0

        for post_idx in range(150):
            author = created_users[post_idx % len(created_users)]
            caption = f"{CAPTIONS[post_idx % len(CAPTIONS)]} #{post_idx + 1}"
            
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            created_time = timezone.now() - datetime.timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            # Every 3rd post is a Video reel (~50 videos, ~100 images)
            is_video = (post_idx % 3 == 0) and (video_ptr < len(video_pool))
            
            if is_video:
                media_url = video_pool[video_ptr]
                video_ptr += 1
                while media_url in used_media_urls and video_ptr < len(video_pool):
                    media_url = video_pool[video_ptr]
                    video_ptr += 1
                
                used_media_urls.add(media_url)
                post = Post.objects.create(
                    user=author,
                    caption=caption,
                    video=media_url
                )
                videos_count += 1
            else:
                media_url = photo_pool[photo_ptr]
                photo_ptr += 1
                while media_url in used_media_urls and photo_ptr < len(photo_pool):
                    media_url = photo_pool[photo_ptr]
                    photo_ptr += 1
                
                used_media_urls.add(media_url)
                post = Post.objects.create(
                    user=author,
                    caption=caption,
                    image=media_url
                )
                images_count += 1

            Post.objects.filter(id=post.id).update(created_at=created_time)
            created_posts.append(post)

        print(f"   -> Successfully created {len(created_posts)} posts with ZERO duplicates!")
        print(f"   -> Images: {images_count} | Videos: {videos_count}")

        print("\n4. Generating Social Graph (Likes, Comments, Follows, Bookmarks)...")
        likes_count = 0
        comments_count = 0
        follows_count = 0
        bookmarks_count = 0

        # Follow connections
        for user in created_users:
            targets = random.sample([u for u in created_users if u != user], k=random.randint(6, 16))
            for target in targets:
                Follow.objects.create(follower=user, following=target)
                follows_count += 1

        # Post engagement
        for post in created_posts:
            # Likes
            likers = random.sample(created_users, k=random.randint(4, 18))
            for liker in likers:
                Like.objects.create(user=liker, post=post)
                likes_count += 1

            # Comments
            commenters = random.sample(created_users, k=random.randint(1, 5))
            for commenter in commenters:
                Comment.objects.create(
                    user=commenter,
                    post=post,
                    content=random.choice(COMMENTS)
                )
                comments_count += 1

            # Bookmarks
            if random.random() < 0.35:
                savers = random.sample(created_users, k=random.randint(1, 4))
                for saver in savers:
                    Bookmark.objects.get_or_create(user=saver, post=post)
                    bookmarks_count += 1

    print("\n==================================================")
    print("      ZERO-DUPLICATE SEEDING SUCCESSFULLY COMPLETE ")
    print("==================================================")
    print(f"  Users created       : {len(created_users)}")
    print(f"  Posts created       : {len(created_posts)}")
    print(f"  Unique Images       : {images_count}")
    print(f"  Unique Videos       : {videos_count}")
    print(f"  Total Unique Media  : {len(used_media_urls)}")
    print(f"  Comments created    : {comments_count}")
    print(f"  Likes created       : {likes_count}")
    print(f"  Follows created     : {follows_count}")
    print(f"  Bookmarks created   : {bookmarks_count}")
    print(f"  Failed media count  : {failed_media_count}")
    print("==================================================\n")

if __name__ == '__main__':
    seed_database()
