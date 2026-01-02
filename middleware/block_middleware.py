from django.shortcuts import redirect
from django.contrib.auth import logout
from django.urls import reverse
from django.contrib import messages 

class BlockUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, "is_blocked", False):
            logout(request)
            messages.error(request, "Your account has been blocked by the admin.")
            return redirect(reverse("login"))

        return self.get_response(request)