from django.urls import path
from .views import *


urlpatterns = [
    path('register/', UserRegister.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('creator-update/', CreatorUpdate.as_view(), name='creator-update'),
    path('create-post/', CreatorPost.as_view(), name='create-post'),
    path('create-post/<int:pk>/', CreatorPost.as_view(), name='update-post'),
    path('post-reaction/<int:pk>/', PostReactionView.as_view(), name='post-reaction'),
    path('post-comment/<int:pk>/', PostCommentView.as_view(), name='post-comment'),
    path('subscribe/<int:pk>/', SubscribeView.as_view(), name='subscribe'),
    path('unsubscribe/<int:pk>/', UnsubscribeView.as_view(), name='unsubscribe'),
    path('feed/', UserFeedView.as_view(), name='user-feed'),
    path('notifications/', NotificationListAPIView.as_view(), name='notifications-list'),
    path('notifications/mark-all/', NotificationMarkAllReadAPIView.as_view(), name='notifications-mark-all'),
    
]

