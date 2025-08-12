from django.contrib import admin
from .models import User,Facility,Turf

# Register your models here.
admin.site.register(User)
admin.site.register(Facility)
admin.site.register(Turf)