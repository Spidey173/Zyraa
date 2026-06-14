import json
import time
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .redis_utils import redis_client, REDIS_AVAILABLE

@database_sync_to_async
def update_user_presence(username):
    if REDIS_AVAILABLE and redis_client:
        try:
            redis_client.zadd("presence_users", {username: time.time()})
        except Exception:
            pass

@database_sync_to_async
def remove_user_presence(username):
    if REDIS_AVAILABLE and redis_client:
        try:
            redis_client.zrem("presence_users", username)
        except Exception:
            pass

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_name = f"user_notifications_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        # Track presence in Redis ZSET asynchronously
        await update_user_presence(self.user.username)
        await self.channel_layer.group_add("online_presence", self.channel_name)
        await self.channel_layer.group_send(
            "online_presence",
            {
                "type": "presence_update",
                "username": self.user.username,
                "status": "online"
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            
        if hasattr(self, "user") and self.user.is_authenticated:
            # Remove from presence set
            await remove_user_presence(self.user.username)
            await self.channel_layer.group_send(
                "online_presence",
                {
                    "type": "presence_update",
                    "username": self.user.username,
                    "status": "offline"
                }
            )
            await self.channel_layer.group_discard("online_presence", self.channel_name)

    async def receive_json(self, content):
        if content.get("type") == "heartbeat" and hasattr(self, "user") and self.user.is_authenticated:
            await update_user_presence(self.user.username)

    async def send_notification(self, event):
        await self.send_json(event["data"])

    async def presence_update(self, event):
        await self.send_json({
            "type": "presence",
            "username": event["username"],
            "status": event["status"]
        })

class PostConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.post_id = self.scope['url_route']['kwargs']['post_id']
        self.group_name = f"post_likes_{self.post_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_like_update(self, event):
        await self.send_json({
            "type": "like_update",
            "likes_count": event["likes_count"]
        })
