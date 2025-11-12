import jwt
from django.conf import settings
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from channels.middleware import BaseMiddleware

# Lazy import of User model
@database_sync_to_async
def get_user(user_id):
    from django.contrib.auth import get_user_model  # ⚠ move inside function
    User = get_user_model()
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope['user'] = AnonymousUser()

        # Extract token from query string
        token = None
        query_string = scope.get("query_string", b"").decode()
        for param in query_string.split("&"):
            k, _, v = param.partition("=")
            if k == "token":
                token = v
                break

        if token:
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get("user_id")
                user = await get_user(user_id)
                if user:
                    scope['user'] = user
            except jwt.ExpiredSignatureError:
                pass
            except jwt.InvalidTokenError:
                pass

        return await super().__call__(scope, receive, send)
