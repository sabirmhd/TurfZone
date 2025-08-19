"""
URL configuration for MyProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from MyApp import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing, name='landing'),
    path('login/',views.login_view, name='login'),
    path('register/',views.register, name='register'),
    path('userhome/',views.userhome, name='userhome'),
    path('ownerhome/',views.ownerhome, name='ownerhome'),
    path('userpro/',views.userpro, name='userpro'),
    path('updatepass/',views.change_password, name='proupdate'),
    path('logout/', views.logout_view, name='logout'),
    path('turfreg/', views.turfreg, name='turfreg'),
    path('admindash/',views.admindash, name='admindash'),
    path('turfreq/',views.turfreq, name='turfreq'),
    path('manageturf/',views.manageturf, name='manageturf'),
    path('approve-turf/<int:turf_id>',views.approve_turf, name='approve_turf'),
    path('reject-turf/<int:turf_id>',views.reject_turf, name='reject_turf'), 
    path('booking/<int:id>',views.booking, name='booking'), 
    path('listbooking/',views.listbooking, name='listbooking'), 
    path('manageusers/',views.manageusers, name='manageusers'),
    path('block/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock/<int:user_id>/', views.unblock_user, name='unblock_user'),
] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT )
