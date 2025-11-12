from rest_framework import serializers
from .models import *


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class CreatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_creator']

class UserPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id','title','content','file','post_type','created_at']

class PostSerializer(serializers.ModelSerializer):
    post_type = serializers.CharField(required=True)

    class Meta:
        model = Post
        fields = ['content', 'file', 'post_type','title']

    def validate(self, attrs):
        post_type = attrs.get('post_type')
        file = attrs.get('file')
        content = attrs.get('content')

        # If post_type == "post", file is required
        if post_type == 'post' and not file:
            raise serializers.ValidationError({
                'file': 'This field is required when post_type is "post".'
            })

        # If post_type == "note", content is required
        if post_type == 'note' and not content:
            raise serializers.ValidationError({
                'content': 'This field is required when post_type is "note".'
            })

        return attrs
    
class ReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reaction
        fields = ['id', 'post', 'user', 'reaction_type', 'created_at']
        read_only_fields = ['id', 'user', 'created_at', 'post']

class NotificationSerializer(serializers.ModelSerializer):
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    sender_name = serializers.CharField(source='sender.name', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'sender', 'sender_email', 'sender_name', 'receiver',
            'notification_type', 'post', 'comment', 'is_read', 'created_at'
        ]
        read_only_fields = fields

class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'created_at']

class feedSerializer(serializers.ModelSerializer):
    like_count = serializers.SerializerMethodField()
    dislike_count = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'content', 'file', 'post_type', 'user_id', 
            'created_at', 'updated_at',
            'like_count', 'dislike_count', 'comments', 'comment_count'
        ]

    def get_like_count(self, obj):
        return obj.reactions.filter(reaction_type=Reaction.LIKE).count()

    def get_dislike_count(self, obj):
        return obj.reactions.filter(reaction_type=Reaction.DISLIKE).count()

    def get_comment_count(self, obj):
        return obj.comments.count()       

