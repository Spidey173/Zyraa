import logging
from celery import shared_task
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
import datetime
from .models import Notification, Post, Story, Follow
from .redis_utils import redis_client, RedisKeys, REDIS_AVAILABLE

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=5,
    autoretry_for=(Exception,)
)
def create_notification_task(self, sender_id, receiver_id, notification_type, post_id=None):
    """
    Creates a Notification instance asynchronously and triggers a WebSocket dispatch.
    """
    # Rate-limiting/deduplication lock using Redis (if available)
    if REDIS_AVAILABLE and redis_client:
        lock_key = f"lock:notification:{sender_id}:{receiver_id}:{notification_type}:{post_id or 0}"
        try:
            is_locked = redis_client.set(lock_key, "1", ex=5, nx=True)
            if not is_locked:
                logger.warning(f"Duplicate notification task ignored: {lock_key}")
                return False
        except Exception as e:
            logger.warning(f"Redis error during lock check in create_notification_task: {e}")
        
    try:
        sender = User.objects.get(id=sender_id)
        receiver = User.objects.get(id=receiver_id)
        post = Post.objects.get(id=post_id) if post_id else None
        
        # Don't notify self
        if sender == receiver:
            return False
            
        with transaction.atomic():
            notification, created = Notification.objects.get_or_create(
                sender=sender,
                receiver=receiver,
                post=post,
                notification_type=notification_type
            )
            
            if created:
                # Increment the unread count in Redis (if available)
                if REDIS_AVAILABLE and redis_client:
                    try:
                        redis_key = RedisKeys.unread_notifications(receiver_id)
                        redis_client.incr(redis_key)
                    except Exception as e:
                        pass
                
                # Push the notification real-time via Django Channels (WebSocket)
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f"user_notifications_{receiver_id}",
                        {
                            "type": "send_notification",
                            "data": {
                                "id": notification.id,
                                "sender_username": sender.username,
                                "sender_profile_pic": sender.profile.profile_pic.url if sender.profile.profile_pic else None,
                                "notification_type": notification_type,
                                "post_id": post_id,
                                "created_at": "Just now"
                            }
                        }
                    )
        return True
    except Exception as exc:
        logger.error(f"Failed to create notification: {exc}")
        raise self.retry(exc=exc)

@shared_task
def fanout_new_post_task(post_id):
    """
    Pushes post_id into the Redis sorted feed sets of all followers (write-on-write model).
    """
    try:
        post = Post.objects.select_related('user').get(id=post_id)
        author = post.user
        timestamp = post.created_at.timestamp()
        
        # Write to Redis if available
        if REDIS_AVAILABLE and redis_client:
            try:
                # Add post to author's own feed
                redis_client.zadd(RedisKeys.feed(author.id), {post_id: timestamp})
                
                # Query followers in chunks to avoid memory spikes under load
                follower_ids_qs = Follow.objects.filter(following=author).values_list('follower_id', flat=True)
                
                # Batch write to Redis via pipeline, executing in chunks of 1000
                chunk_size = 1000
                pipeline = redis_client.pipeline()
                count = 0
                
                for fid in follower_ids_qs.iterator(chunk_size=chunk_size):
                    feed_key = RedisKeys.feed(fid)
                    pipeline.zadd(feed_key, {post_id: timestamp})
                    # Cap the feed at 500 items to conserve Redis memory
                    pipeline.zremrangebyrank(feed_key, 0, -501)
                    count += 1
                    
                    if count % chunk_size == 0:
                        pipeline.execute()
                        pipeline = redis_client.pipeline() # Reset pipeline
                        
                # Execute any remaining commands
                if count % chunk_size != 0:
                    pipeline.execute()
            except Exception as e:
                logger.error(f"Redis connection error during fanout task: {e}")
        
    except Post.DoesNotExist:
        logger.error(f"Post {post_id} does not exist for fanout.")

@shared_task
def cleanup_expired_stories_task():
    """
    Deletes stories older than 24 hours from database and Cloudinary storage.
    """
    expiration_time = timezone.now() - datetime.timedelta(hours=24)
    expired_stories = Story.objects.filter(created_at__lt=expiration_time)
    
    import cloudinary.uploader
    
    count = 0
    for story in expired_stories:
        try:
            if story.image:
                cloudinary.uploader.destroy(story.image.name)
            if story.video:
                cloudinary.uploader.destroy(story.video.name)
            if story.music:
                cloudinary.uploader.destroy(story.music.name)
        except Exception as e:
            logger.error(f"Failed to delete story {story.id} assets from Cloudinary: {e}")
            
        story.delete()
        count += 1
    logger.info(f"Successfully cleaned up {count} expired stories.")

@shared_task
def prune_presence_task():
    """
    Finds and removes users from presence_users ZSET who haven't sent a heartbeat
    within the last 30 seconds, and broadcasts their offline status via channels.
    """
    import time
    from .redis_utils import redis_client, REDIS_AVAILABLE
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    if not REDIS_AVAILABLE or not redis_client:
        return 0

    try:
        now = time.time()
        cutoff = now - 30.0  # 30 seconds threshold
        
        # Find expired users (score < cutoff)
        expired_users_bytes = redis_client.zrangebyscore("presence_users", "-inf", cutoff)
        if not expired_users_bytes:
            return 0
            
        expired_users = [u.decode('utf-8') if isinstance(u, bytes) else u for u in expired_users_bytes]
        
        # Remove expired users from ZSET
        redis_client.zrem("presence_users", *expired_users)
        
        # Broadcast offline update to group
        channel_layer = get_channel_layer()
        if channel_layer:
            for username in expired_users:
                async_to_sync(channel_layer.group_send)(
                    "online_presence",
                    {
                        "type": "presence_update",
                        "username": username,
                        "status": "offline"
                    }
                )
        return len(expired_users)
    except Exception as e:
        logger.error(f"Error during prune_presence_task: {e}")
        return 0

