import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Blog.settings')  # ⚠ must be first

from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from myapp.middleware import JWTAuthMiddleware
from myapp.consumers import NotificationConsumer
from django.urls import re_path

ws_patterns = [
    re_path(r'ws/notifications/?$', NotificationConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter(ws_patterns)
    ),
})
