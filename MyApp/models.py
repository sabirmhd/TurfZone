from django.db import models
from django.conf import settings 
from decimal import Decimal
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.db.models import Avg

class UserManager(BaseUserManager):
    def create_user(self, email, password = None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using = self._db)
        return user

    def create_superuser(self, email, password = None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)
    
class User(AbstractBaseUser, PermissionsMixin):
    fullname = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, null=True, blank=True, default=None)
    phone=models.CharField(max_length=10, unique=True)
    is_staff = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone']

    def __str__(self):
        return self.email
    
# Choices for sports types and facilities
SPORT_CHOICES = [
    ('football', 'Football'),
    ('cricket', 'Cricket'),
    ('badminton', 'Badminton'),
    ('tennis', 'Tennis'),
    ('multi', 'Multi-sport'),
]

FACILITY_CHOICES = [
    ('parking', 'Parking'),
    ('lights', 'Flood Lights'),
    ('locker', 'Locker Room'),
    ('refreshments', 'Refreshments'),
    ('washroom', 'Washroom'),
    ('seating', 'Spectator Seating'),
]

class Turf(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='turfs')
    turf_name = models.CharField(max_length=100)
    sport_type = models.CharField(max_length=50, choices=SPORT_CHOICES)
    description = models.TextField()
    location = models.CharField(max_length=200)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    address = models.CharField(max_length=255)
    pincode = models.CharField(max_length=10)
    price_per_hour = models.DecimalField(
    max_digits=7,
    decimal_places=2,
    )
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    facilities = models.ManyToManyField('Facility', blank=True)
    image1 = models.ImageField(upload_to='turf_images/', blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.location:
            self.location = f"{self.city},{self.state},{self.address}"
        super().save(*args, **kwargs)
        
    @property
    def avg_rating(self):
        return self.reviews.aggregate(avg=Avg("rating"))["avg"]   

class Facility(models.Model):
    name = models.CharField(max_length=50, choices=FACILITY_CHOICES, unique=True)

    def __str__(self):
        return self.get_name_display()
    

class TurfBooking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.fullname} booked {self.turf.turf_name}"
    

class Review(models.Model):
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('turf', 'user')  # one review per user per turf

    def __str__(self):
        return f"Review by {self.user.fullname} on {self.turf.turf_name}"




