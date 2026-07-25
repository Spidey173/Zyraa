import os
import sys
import django
import urllib.request

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from core.models import UserProfile, Post, Comment, Like, Follow, Story

def fetch_content(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read()
    except Exception as e:
        print(f"Warning: Failed to fetch {url}: {e}")
        return None

def seed():
    print("Seeding database with valid Cloudinary media files...")
    
    # 1. Create Demo Users
    users_data = [
        {'username': 'bruce_banner', 'bio': 'Scientist. Always angry. 🧪'},
        {'username': 'wanda_maximoff', 'bio': 'Chaos magic ✨'},
        {'username': 'steve_rogers', 'bio': 'I can do this all day. 🛡️'},
        {'username': 'tony_stark', 'bio': 'Genius, billionaire, playboy, philanthropist. ⚡️'},
        {'username': 'natasha_romanoff', 'bio': 'Black Widow 🕷️'}
    ]

    users = {}
    for udata in users_data:
        try:
            user, created = User.objects.get_or_create(username=udata['username'], defaults={'email': f"{udata['username']}@example.com"})
            if created:
                user.set_password('password123')
                user.save()
            user.profile.bio = udata['bio']
            user.profile.save()
            users[udata['username']] = user
        except Exception as e:
            print(f"Error creating user {udata['username']}: {e}")

    # 2. Seed Sample Image Posts (only if user has fewer than 2 posts)
    sample_images = [
        ("bruce_banner", "On your left! Beautiful morning for a run. 🏃‍♂️💨", "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&auto=format&fit=crop"),
        ("wanda_maximoff", "Not perfect, just trying to do my best. 🕯️", "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop"),
        ("steve_rogers", "Working late in the lab. Big discoveries coming soon! 🔬🧪 #science", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&auto=format&fit=crop"),
    ]

    for username, caption, img_url in sample_images:
        u = users.get(username)
        if u and u.posts.filter(image__isnull=False).count() < 2:
            try:
                print(f"Creating image post for {username}...")
                img_data = fetch_content(img_url)
                post = Post.objects.create(user=u, caption=caption)
                if img_data:
                    post.image.save(f"{username}_post.jpg", ContentFile(img_data), save=True)
                else:
                    post.save()
            except Exception as e:
                print(f"Warning: Image post creation skipped for {username}: {e}")

    # 3. Seed Sample Video Reels (only if less than 2 reels exist)
    if Post.objects.exclude(video='').exclude(video__isnull=True).count() < 2:
        sample_reels = [
            ("tony_stark", "Testing out the new high-speed setup! 🎥⚡️ #reels", "https://assets.mixkit.co/videos/preview/mixkit-tree-with-yellow-flowers-1173-large.mp4"),
            ("natasha_romanoff", "Ocean waves crashing on the coast 🌊 Relaxing vibes.", "https://assets.mixkit.co/videos/preview/mixkit-waves-in-the-water-1164-large.mp4"),
        ]

        for username, caption, video_url in sample_reels:
            u = users.get(username)
            if u:
                try:
                    print(f"Uploading reel video for {username}...")
                    vid_data = fetch_content(video_url)
                    post = Post.objects.create(user=u, caption=caption)
                    if vid_data:
                        post.video.save(f"{username}_reel.mp4", ContentFile(vid_data), save=True)
                    else:
                        post.save()
                except Exception as e:
                    print(f"Warning: Video reel creation skipped for {username}: {e}")

    print("Database seeding completed safely!")

if __name__ == '__main__':
    try:
        seed()
    except Exception as main_exc:
        print(f"Non-fatal error in seed script: {main_exc}")
