import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile, Post, Comment, Like, Follow, Story

def seed():
    print("Seeding/updating database with working media URLs...")

    # Demo user accounts
    demo_users_data = [
        {'username': 'bruce_banner', 'bio': 'Scientist. Always angry. 🧪'},
        {'username': 'wanda_maximoff', 'bio': 'Chaos magic ✨'},
        {'username': 'steve_rogers', 'bio': 'I can do this all day. 🛡️'},
        {'username': 'tony_stark', 'bio': 'Genius, billionaire, playboy, philanthropist. ⚡️'},
        {'username': 'natasha_romanoff', 'bio': 'Black Widow 🕷️'}
    ]

    users = {}
    for udata in demo_users_data:
        user, created = User.objects.get_or_create(username=udata['username'], defaults={'email': f"{udata['username']}@example.com"})
        if created:
            user.set_password('password123')
            user.save()
        user.profile.bio = udata['bio']
        user.profile.save()
        users[udata['username']] = user

    # Fix or create demo image posts
    sample_images = [
        ("bruce_banner", "On your left! Beautiful morning for a run. 🏃‍♂️💨", "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1080&auto=format&fit=crop"),
        ("wanda_maximoff", "Not perfect, just trying to do my best. 🕯️", "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1080&auto=format&fit=crop"),
        ("steve_rogers", "Working late in the lab. Big discoveries coming soon! 🔬🧪 #science", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1080&auto=format&fit=crop"),
    ]

    for username, caption, img_url in sample_images:
        u = users.get(username)
        if u:
            post, created = Post.objects.get_or_create(
                user=u,
                caption=caption,
                defaults={'image': img_url}
            )
            # If image string is broken local path, update it to working image URL
            if not created and (not str(post.image).startswith('http') or not post.image):
                post.image = img_url
                post.save()

    # Create / update video Reels posts
    sample_reels = [
        ("tony_stark", "Testing out the new high-speed camera setup! 🎥⚡️ #reels #tech", "https://assets.mixkit.co/videos/preview/mixkit-tree-with-yellow-flowers-1173-large.mp4"),
        ("natasha_romanoff", "Ocean waves crashing on the coast 🌊 Relaxing vibes.", "https://assets.mixkit.co/videos/preview/mixkit-waves-in-the-water-1164-large.mp4"),
        ("bruce_banner", "Nature hike through the mist 🌲✨ #outdoors", "https://assets.mixkit.co/videos/preview/mixkit-forest-stream-in-the-sunlight-529-large.mp4"),
    ]

    for username, caption, video_url in sample_reels:
        u = users.get(username)
        if u:
            post, created = Post.objects.get_or_create(
                user=u,
                caption=caption,
                defaults={'video': video_url}
            )
            if not created and (not str(post.video).startswith('http') or not post.video):
                post.video = video_url
                post.save()

    print("Seed complete! All posts updated with active working media.")

if __name__ == '__main__':
    seed()
