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
# Verified High-Quality Media Collections (HTTPS CDNs / Cloudinary)
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
    "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=300&auto=format&fit=crop"
]

PHOTO_POST_URLS = [
    "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1426604966848-d7adac402bff?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1534972195531-d756b9bfa9f2?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1476514525535-ce74f45814d0?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1503220317375-aaad61436b1b?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1473448912268-2022ce9509d8?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1511447333015-45b65e60f6d5?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1538805060514-97d9cc17730c?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1508921912186-1d1a45ebb3c1?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1513584684374-8bab748fbf90?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=1080&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1080&auto=format&fit=crop"
]

VIDEO_POST_URLS = [
    "https://res.cloudinary.com/demo/video/upload/v1687352345/samples/elephants.mp4",
    "https://res.cloudinary.com/demo/video/upload/v1687352345/samples/sea-turtle.mp4",
    "https://res.cloudinary.com/demo/video/upload/v1687352345/samples/dance-2.mp4",
    "https://res.cloudinary.com/demo/video/upload/v1687352345/samples/cld-sample-video.mp4",
    "https://res.cloudinary.com/demo/video/upload/v1687352345/samples/bike.mp4",
    "https://res.cloudinary.com/demo/video/upload/v1687352345/samples/sea-turtle.mp4",
    "https://res.cloudinary.com/demo/video/upload/v1687352345/samples/elephants.mp4"
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

def seed_database():
    print("\n==================================================")
    print("      RESETTING & SEEDING DEMO APPLICATION DATA    ")
    print("==================================================\n")

    failed_media_count = 0
    
    with transaction.atomic():
        print("1. Purging all existing database data...")
        Notification.objects.all().delete()
        Bookmark.objects.all().delete()
        Like.objects.all().delete()
        Comment.objects.all().delete()
        Follow.objects.all().delete()
        Story.objects.all().delete()
        Post.objects.all().delete()
        UserProfile.objects.all().delete()
        User.objects.all().delete()
        print("   -> Existing database successfully cleared.")

        print("\n2. Creating 25 unique users & profiles...")
        created_users = []
        for idx, udata in enumerate(USERS_SEED_DATA):
            avatar_url = AVATAR_URLS[idx % len(AVATAR_URLS)]
            
            # Validate avatar URL before assigning
            if not check_url_active(avatar_url):
                print(f"   -> Warning: Avatar URL check failed for {udata['username']}. Using fallback.")
                avatar_url = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300&auto=format&fit=crop"
                failed_media_count += 1
                
            user = User.objects.create_user(
                username=udata['username'],
                email=f"{udata['username']}@zyraa.app",
                first_name=udata['first_name'],
                last_name=udata['last_name'],
                password='Password123!'
            )
            
            # Update user profile pic & bio
            profile = user.profile
            profile.bio = udata['bio']
            profile.profile_pic = avatar_url
            profile.save()
            
            created_users.append(user)

        print(f"   -> Successfully created {len(created_users)} users.")

        print("\n3. Creating 150 unique posts (mixing photos & videos)...")
        created_posts = []
        images_count = 0
        videos_count = 0
        
        # Build pool of verified photo & video URLs
        verified_photos = []
        for purl in PHOTO_POST_URLS:
            if check_url_active(purl):
                verified_photos.append(purl)
            else:
                failed_media_count += 1

        verified_videos = []
        for vurl in VIDEO_POST_URLS:
            if check_url_active(vurl):
                verified_videos.append(vurl)
            else:
                failed_media_count += 1

        print(f"   -> Verified {len(verified_photos)} active photo URLs & {len(verified_videos)} active video URLs.")

        target_total_posts = 150
        for post_idx in range(target_total_posts):
            author = random.choice(created_users)
            caption = random.choice(CAPTIONS)
            
            # Random upload date across the past 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            created_time = timezone.now() - datetime.timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            # 2:1 ratio of Images to Videos (~100 images, ~50 videos)
            is_video = (post_idx % 3 == 0) and (len(verified_videos) > 0)
            
            if is_video:
                video_url = verified_videos[post_idx % len(verified_videos)]
                post = Post.objects.create(
                    user=author,
                    caption=caption,
                    video=video_url
                )
                videos_count += 1
            else:
                photo_url = verified_photos[post_idx % len(verified_photos)]
                post = Post.objects.create(
                    user=author,
                    caption=caption,
                    image=photo_url
                )
                images_count += 1
                
            # Override created_at timestamp
            Post.objects.filter(id=post.id).update(created_at=created_time)
            created_posts.append(post)

        print(f"   -> Successfully created {len(created_posts)} posts ({images_count} images, {videos_count} videos).")

        print("\n4. Generating social graph (Likes, Comments, Follows, Bookmarks)...")
        likes_count = 0
        comments_count = 0
        follows_count = 0
        bookmarks_count = 0

        # Follow relationships
        for user in created_users:
            # Each user follows 5 to 15 other users
            follow_targets = random.sample([u for u in created_users if u != user], k=random.randint(5, 15))
            for target in follow_targets:
                Follow.objects.create(follower=user, following=target)
                follows_count += 1

        # Likes & Comments & Bookmarks on posts
        for post in created_posts:
            # Likes
            likers = random.sample(created_users, k=random.randint(5, 20))
            for liker in likers:
                Like.objects.create(user=liker, post=post)
                likes_count += 1

            # Comments
            commenters = random.sample(created_users, k=random.randint(1, 6))
            for commenter in commenters:
                Comment.objects.create(
                    user=commenter,
                    post=post,
                    content=random.choice(COMMENTS)
                )
                comments_count += 1

            # Bookmarks
            if random.random() < 0.3:
                savers = random.sample(created_users, k=random.randint(1, 5))
                for saver in savers:
                    Bookmark.objects.get_or_create(user=saver, post=post)
                    bookmarks_count += 1

    print("\n==================================================")
    print("        ZYRA DEMO DATA SEEDING COMPLETE           ")
    print("==================================================")
    print(f"  Users created       : {len(created_users)}")
    print(f"  Posts created       : {len(created_posts)}")
    print(f"  Images created      : {images_count}")
    print(f"  Videos created      : {videos_count}")
    print(f"  Comments created    : {comments_count}")
    print(f"  Likes created       : {likes_count}")
    print(f"  Follows created     : {follows_count}")
    print(f"  Bookmarks created   : {bookmarks_count}")
    print(f"  Failed media count  : {failed_media_count}")
    print("==================================================\n")

if __name__ == '__main__':
    seed_database()
