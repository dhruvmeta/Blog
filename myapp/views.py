from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .serializers import *
from rest_framework.views import APIView
from .models import *
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework import permissions
from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.contrib.auth import authenticate
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework.response import Response
# import all redis setting
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache import cache
from django.views.decorators.cache import cache_page

# Create your views here.

def get_tokens_for_user(user):
    if not user.is_active:
      raise AuthenticationFailed("User is not active")

    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class UserRegister(APIView):
    def post(self,request):
        serializers=UserSerializer(data=request.data)
        if serializers.is_valid():
            password=serializers.validated_data['password']
            # convert to hash 
            serializers.validated_data['password']=make_password(password)
            emp=serializers.save()
            # sub ="Welcome!!!"
            # msg =f"Dear User !\nYour Account has been created with us !\nEnjoy our service .\nif any query ,contact us at \nmetadhruv4@gmail.com | 7435820532"
            # from_Email=settings.EMAIL_HOST_USER
            # to_email=[emp.email]
            # send_mail(subject=sub,message=msg,from_email=from_Email,recipient_list=to_email)
            token=get_tokens_for_user(emp)
            return Response({'token': token, 'data':serializers.data}, status=status.HTTP_201_CREATED)
        return Response(serializers.errors,status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            raise AuthenticationFailed('Email and password are required')

        user = authenticate(email=email, password=password)
        if user is None:
            raise AuthenticationFailed('Invalid email or password')

        if not user.is_active:
            raise AuthenticationFailed('Account is disabled')

        serializer = UserSerializer(user)

        return Response({
            'token': get_tokens_for_user(user),
            'data': serializer.data,
            "message": f"Welcome {user.name}, you have logged in successfully!"
        }, status=status.HTTP_200_OK)
# update to creator

class CreatorUpdate(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request):
        user = request.user
        if user.is_admin:
            return Response({"message": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)
        serializer = CreatorSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CreatorPost(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = PostSerializer(data=request.data)
        # Check if user is a creator
        if user.is_creator:
            if serializer.is_valid():
                serializer.save(user=user)
                return Response(
                    {"message": "Post created successfully", "data": serializer.data},
                    status=status.HTTP_201_CREATED
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)
        

    def get(self,request):
        user = request.user
        if user.is_creator:
            posts = Post.objects.filter(user=user)
            serializer = UserPostSerializer(posts, many=True)
            return Response({"message": "Posts fetched successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    def patch(self,request,pk):
        user = request.user
        post = get_object_or_404(Post, pk=pk)
        if user.is_creator and post.user == user:
            serializer = PostSerializer(post, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Post updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    def delete(self, request, pk):
        user = request.user
        post = get_object_or_404(Post, pk=pk)
        if user.is_creator and post.user == user:
            post.delete()
            return Response({"message": "Post deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"message": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)
        
class PostReactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        post = get_object_or_404(Post, pk=pk)
        reaction_type = request.data.get('reaction_type')

        if reaction_type not in ['like', 'dislike']:
            return Response({"message": "Invalid reaction type"}, status=status.HTTP_400_BAD_REQUEST)

        reaction, created = Reaction.objects.get_or_create(post=post, user=user, defaults={'reaction_type': reaction_type})

        if not created:
            if reaction.reaction_type == reaction_type:
                reaction.delete()
                return Response({"message": f"{reaction_type.capitalize()} removed"}, status=status.HTTP_200_OK)
            else:
                reaction.reaction_type = reaction_type
                reaction.save()

        return Response({"message": f"{reaction_type.capitalize()} added"}, status=status.HTTP_200_OK)

class PostCommentView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        post = get_object_or_404(Post, pk=pk)
        comment_text = request.data.get('content')

        if not comment_text:
            return Response({"error": "Content is required"}, status=status.HTTP_400_BAD_REQUEST)

        Comment.objects.create(post=post, user=user, content=comment_text)
        return Response({"message": "Comment added successfully"}, status=status.HTTP_201_CREATED)

    def patch(self, request, pk):
        user = request.user
        comment = get_object_or_404(Comment, pk=pk)

        if user != comment.user:
            return Response(
                {"message": "You are not authorized to perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )

        comment_text = request.data.get('content')
        if not comment_text:
            return Response(
                {"message": "Content field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

    #  correct field name
        comment.content = comment_text
        comment.save()

        return Response(
            {"message": "Comment updated successfully"},
            status=status.HTTP_200_OK
        )
      
    def delete(self,request,pk):
        user = request.user
        comment = get_object_or_404(Comment, pk=pk)
        if user == comment.user:
            comment.delete()
            return Response({"message": "Comment deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"message": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)

class SubscribeView(APIView):

    def post(self, request, pk):
        user = request.user
        try:
            subscribed_to = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=404)

        if Subscription.objects.filter(subscriber=user, subscribed_to=subscribed_to).exists():
            return Response({'detail': 'Already subscribed.'}, status=400)

        Subscription.objects.create(subscriber=user, subscribed_to=subscribed_to)
        return Response({'detail': 'Subscription created successfully.'}, status=201)
    
class UnsubscribeView(APIView):


    def delete(self, request, pk):
        user = request.user
        try:
            subscribed_to = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=404)

        Subscription.objects.filter(subscriber=user, subscribed_to=subscribed_to).delete()
        return Response({'detail': 'Subscription deleted successfully.'}, status=204)
    
class UserFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 1 Get IDs of users this user is subscribed to (following)
        subscribed_ids = Subscription.objects.filter(subscriber=user).values_list('subscribed_to', flat=True)

        # 2 Posts from subscribed users (top priority)
        posts_from_subscribed = Post.objects.filter(user_id__in=subscribed_ids)

        # 3 Recent posts (not from subscribed users)
        recent_posts = Post.objects.exclude(user_id__in=subscribed_ids).order_by('-created_at')[:20]

        # 4 Combine them in priority order
        final_posts = list(posts_from_subscribed) + list(recent_posts)

        # 5 Remove duplicates while preserving order
        seen = set()
        unique_posts = []
        for post in final_posts:
            if post.id not in seen:
                seen.add(post.id)
                unique_posts.append(post)

        # 6 Serialize and return
        serializer = feedSerializer(unique_posts, many=True)
        return Response(serializer.data)
    
class NotificationListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Return only unread notifications for the authenticated user
        (where is_read=False).
        """
        unread_notifications = Notification.objects.filter(
            receiver=request.user,
            is_read=False
        ).order_by('-created_at')  # optional: latest first

        serializer = NotificationSerializer(unread_notifications, many=True)
        return Response(serializer.data)

class NotificationMarkAllReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Mark all user's notifications as read.
        """
        Notification.objects.filter(receiver=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "All notifications marked read."})

