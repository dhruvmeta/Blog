# myapp/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if user.is_anonymous:
            await self.close()
        else:
            # Create a group for this user
            self.group_name = f"user_{user.id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        user = self.scope['user']
        if not user.is_anonymous:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Optional: handle messages from the client
        pass

    async def send_notification(self, event):
        """
        Called when a notification message is sent to this user's group
        """
        await self.send(text_data=json.dumps(event["notification"]))
