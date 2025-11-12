from django.contrib import admin

# Register your models here.


from .models import *

admin.site.register(User)
# admin.site.register(Profile)
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Reaction)
admin.site.register(Subscription)   
