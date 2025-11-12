from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.conf import settings

# -------------------------------
# User and User Manager
# -------------------------------
class UserManager(BaseUserManager):
    def create_user(self, email, name, tc, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(
            email=self.normalize_email(email),
            name=name,
            tc=tc,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, tc, password=None):
        user = self.create_user(email=email, name=name, tc=tc, password=password)
        user.is_admin = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    email = models.EmailField(verbose_name="Email Address", max_length=255, unique=True)
    name = models.CharField(max_length=200)
    tc = models.BooleanField(verbose_name="Terms and Conditions Accepted")
    
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_creator = models.BooleanField(default=False)
    is_viewer = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "tc"]

    def __str__(self):
        return self.name

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return self.is_admin


# -------------------------------
# Profile Model (Followers)
# -------------------------------
class Subscription(models.Model):
    subscriber = models.ForeignKey(User, related_name='subscriptions', on_delete=models.CASCADE)
    subscribed_to = models.ForeignKey(User, related_name='subscribers', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('subscriber', 'subscribed_to')

# -------------------------------
# Post, Comment, Reaction Models
# -------------------------------
class Post(models.Model):
    POST_TYPE_CHOICES = [
        ('post', 'Post'),
        ('note', 'Note')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='uploads/', blank=True, null=True)
    post_type = models.CharField(max_length=10, choices=POST_TYPE_CHOICES, default='post')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.post_type} - {self.title or 'No Title'}"
    
    def is_visible_to(self, viewer):
        profile = self.user.profile
        if profile.is_public:
            return True
        # Only followers can see if private
        return profile.followers.filter(pk=viewer.profile.pk).exists()


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.email} on {self.post.title or 'Post'}"


class Reaction(models.Model):
    LIKE = 'like'
    DISLIKE = 'dislike'

    REACTION_CHOICES = [
        (LIKE, 'Like'),
        (DISLIKE, 'Dislike'),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=7, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reaction_type.capitalize()} by {self.user.email} on {self.post.title}"

    @staticmethod
    def count_reactions(post):
        counts = {Reaction.LIKE: 0, Reaction.DISLIKE: 0}
        reactions = post.reactions.values('reaction_type').annotate(count=models.Count('id'))
        for r in reactions:
            counts[r['reaction_type']] = r['count']
        return counts

    @classmethod
    def likes(cls, post):
        return post.reactions.filter(reaction_type=cls.LIKE).count()

    @classmethod
    def dislikes(cls, post):
        return post.reactions.filter(reaction_type=cls.DISLIKE).count()

#-------------------------------
#Notification Model
# -------------------------------
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('follow', 'Follow'),
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('post', 'Post'),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, blank=True, null=True, related_name='notifications')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, blank=True, null=True, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        # Prevent duplicate notifications
        unique_together = [['sender', 'receiver', 'notification_type', 'post', 'comment']]

    def __str__(self):
        return f"Notification from {self.sender.email} to {self.receiver.email} ({self.notification_type})"
    
    def to_dict(self):
        """
        A simple serializable representation used for websocket push.
        """
        return {
            "id": self.pk,
            "sender_id": self.sender_id,
            "sender_email": getattr(self.sender, "email", None),
            "sender_username": getattr(self.sender, "username", None),
            "receiver_id": self.receiver_id,
            "notification_type": self.notification_type,
            "post_id": self.post_id,
            "comment_id": self.comment_id,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat(),
        }
    
    def get_notification_message(self):
        """
        Generate a human-readable message based on notification type
        """
        sender_name = self.sender.get_full_name() or self.sender.username
        
        messages = {
            'follow': f"{sender_name} followed you",
            'like': f"{sender_name} liked your post",
            'comment': f"{sender_name} commented on your post",
            'post': f"{sender_name} posted something new",
        }
        
        return messages.get(self.notification_type, "New notification")
