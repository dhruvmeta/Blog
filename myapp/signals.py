from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Reaction, Comment, Subscription, Notification
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def _send_ws_notification(receiver, notif_type, instance, sender_user):
    """
    Send real-time notification over Channels to the receiver.
    """
    channel_layer = get_channel_layer()
    group_name = f"user_{receiver.id}"

    # Build dynamic message based on notification type
    if notif_type == "like":
        message = f"{sender_user.name} liked your post (ID: {instance.post.id})"
    elif notif_type == "dislike":
        message = f"{sender_user.name} disliked your post (ID: {instance.post.id})"
    elif notif_type == "comment":
        message = f"{sender_user.name} commented on your post (ID: {instance.post.id}): \"{instance.content}\""
    elif notif_type == "follow":
        message = f"{sender_user.name} subscribed to you"
    else:
        message = f"New {notif_type} from {sender_user.name}"

    data = {
        "type": "send_notification",
        "notification": {
            "type": notif_type,
            "sender": {
                "id": sender_user.id,
                "username": sender_user.name,
            },
            "message": message,
            "post_id": getattr(instance, "post_id", None),
            "comment_id": getattr(instance, "id", None) if notif_type == "comment" else None
        }
    }

    async_to_sync(channel_layer.group_send)(group_name, data)


# Reaction Notification
@receiver(post_save, sender=Reaction)
def reaction_notification(sender, instance, created, **kwargs):
    if created and instance.post.user != instance.user:
        Notification.objects.create(
            sender=instance.user,
            receiver=instance.post.user,
            notification_type=instance.reaction_type,  # 'like' or 'dislike'
            post=instance.post
        )
        _send_ws_notification(instance.post.user, instance.reaction_type, instance, instance.user)


# Comment Notification
@receiver(post_save, sender=Comment)
def comment_notification(sender, instance, created, **kwargs):
    if created and instance.post.user != instance.user:
        Notification.objects.create(
            sender=instance.user,
            receiver=instance.post.user,
            notification_type='comment',
            post=instance.post,
            comment=instance
        )
        _send_ws_notification(instance.post.user, "comment", instance, instance.user)


# Subscription Notification
@receiver(post_save, sender=Subscription)
def subscription_notification(sender, instance, created, **kwargs):
    if created and instance.subscribed_to != instance.subscriber:
        Notification.objects.create(
            sender=instance.subscriber,
            receiver=instance.subscribed_to,
            notification_type='follow'
        )
        _send_ws_notification(instance.subscribed_to, "follow", instance, instance.subscriber)
