from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class CloudinaryURLWrapper:
    def __init__(self, url):
        self.url = url
    
    def __str__(self):
        return self.url or ""
    
    @property
    def name(self):
        return self.url

    def delete(self, *args, **kwargs):
        # Graceful no-op for file-deletion cleanups
        pass

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    profile_pic_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    @property
    def profile_pic(self):
        if self.profile_pic_url:
            return CloudinaryURLWrapper(self.profile_pic_url)
        return None

    @profile_pic.setter
    def profile_pic(self, value):
        if isinstance(value, CloudinaryURLWrapper):
            self.profile_pic_url = value.url
        elif hasattr(value, 'url'):
            self.profile_pic_url = value.url
        else:
            self.profile_pic_url = value

    @property
    def followers_count(self):
        from .redis_utils import get_user_stats
        followers, _ = get_user_stats(self.user.id, lambda: (
            Follow.objects.filter(following=self.user).count(),
            Follow.objects.filter(follower=self.user).count()
        ))
        return followers

    @property
    def following_count(self):
        from .redis_utils import get_user_stats
        _, following = get_user_stats(self.user.id, lambda: (
            Follow.objects.filter(following=self.user).count(),
            Follow.objects.filter(follower=self.user).count()
        ))
        return following

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.create(user=instance)

class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    caption = models.TextField(max_length=1000, blank=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    video_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Post by {self.user.username} at {self.created_at}"

    @property
    def image(self):
        if self.image_url:
            return CloudinaryURLWrapper(self.image_url)
        return None

    @image.setter
    def image(self, value):
        if isinstance(value, CloudinaryURLWrapper):
            self.image_url = value.url
        elif hasattr(value, 'url'):
            self.image_url = value.url
        else:
            self.image_url = value

    @property
    def video(self):
        if self.video_url:
            return CloudinaryURLWrapper(self.video_url)
        return None

    @video.setter
    def video(self, value):
        if isinstance(value, CloudinaryURLWrapper):
            self.video_url = value.url
        elif hasattr(value, 'url'):
            self.video_url = value.url
        else:
            self.video_url = value

    @property
    def likes_count(self):
        from .redis_utils import get_like_count
        return get_like_count(self.id, lambda: self.likes.count())

    @property
    def comments_count(self):
        return self.comments.count()

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} liked {self.post.id}"

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on post {self.post.id}"

class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_relations')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follower_relations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} saved post {self.post.id}"

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('follow', 'Follow'),
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='notifications', blank=True, null=True)
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.receiver.username} from {self.sender.username} ({self.notification_type})"

class Story(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    image_url = models.URLField(max_length=500, blank=True, null=True)
    video_url = models.URLField(max_length=500, blank=True, null=True)
    music_url = models.URLField(max_length=500, blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Story by {self.user.username} at {self.created_at}"

    @property
    def image(self):
        if self.image_url:
            return CloudinaryURLWrapper(self.image_url)
        return None

    @image.setter
    def image(self, value):
        if isinstance(value, CloudinaryURLWrapper):
            self.image_url = value.url
        elif hasattr(value, 'url'):
            self.image_url = value.url
        else:
            self.image_url = value

    @property
    def video(self):
        if self.video_url:
            return CloudinaryURLWrapper(self.video_url)
        return None

    @video.setter
    def video(self, value):
        if isinstance(value, CloudinaryURLWrapper):
            self.video_url = value.url
        elif hasattr(value, 'url'):
            self.video_url = value.url
        else:
            self.video_url = value

    @property
    def music(self):
        if self.music_url:
            return CloudinaryURLWrapper(self.music_url)
        return None

    @music.setter
    def music(self, value):
        if isinstance(value, CloudinaryURLWrapper):
            self.music_url = value.url
        elif hasattr(value, 'url'):
            self.music_url = value.url
        else:
            self.music_url = value
