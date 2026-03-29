from django.contrib import admin
from .models import CustomUser, Screen, Booking

admin.site.register(CustomUser)
admin.site.register(Screen)
admin.site.register(Booking)
