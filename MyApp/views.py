from django.shortcuts import render,redirect
from django.contrib.auth import authenticate, login, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Turf,Facility,TurfBooking
from datetime import datetime,date, timedelta
from decimal import Decimal
from django.db.models import Q

User = get_user_model()

def landing(request):
    return render(request,'landing.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            if user.role == 'admin':
                return redirect('admindash')
            elif user.role == 'owner':
                return redirect('ownerhome')
            else:
                return redirect('userhome')
        
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html')

# from .models import UserProfile  # Uncomment if you're using a profile model

def register(request):
    if request.method == 'POST':
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        user_type = request.POST.get('user_type')  # 'player' or 'owner'

        # Validation
        if not fullname or not email or not phone or not password or not confirm_password:
            messages.error(request, "All fields are required.")
            return render(request, 'register.html')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return render(request, 'register.html')

        if User.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number already registered.")
            return render(request, 'register.html')

        # Determine role: False = player, True = owner

        # Create user using custom manager
        User.objects.create_user(
            email=email,
            password=password,
            fullname=fullname,
            phone=phone,
            role=user_type,
        )

        messages.success(request, "Account created successfully.")

        # Redirect based on user_type
        if user_type == 'owner':
            return redirect('turfreg')  # for owner
        else:
            return redirect('userhome')   # for player

    return render(request, 'register.html')

def userpro(request):
    return render(request, 'userpro.html')


@login_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        user = request.user

        # Check current password
        if not user.check_password(old_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('change_password')

        # Check new password confirmation
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('change_password')

        # Update password
        user.set_password(new_password)
        user.save()

        # Keep user logged in after password change
        update_session_auth_hash(request, user)

        messages.success(request, "Password updated successfully.")
        return redirect('userhome')  # Or wherever you want to redirect

    return render(request, 'change_password.html')

def logout_view(request):
    logout(request)
    return redirect('landing')


def turfreg(request):
    if request.method == 'POST':
        turf_name = request.POST.get('turf_name')
        sport_type = request.POST.get('sport_type')
        description = request.POST.get('description')
        address = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        pincode = request.POST.get('pincode')
        price_per_hour = request.POST.get('price_per_hour')
        opening_time = request.POST.get('opening_time')
        closing_time = request.POST.get('closing_time')
        facilities = request.POST.getlist('facilities')
        image1 = request.FILES.get('image1')

        # Save turf object
        turf = Turf.objects.create(
            owner=request.user,
            turf_name=turf_name,
            sport_type=sport_type,
            description=description,
            address=address,
            city=city,
            state=state,
            pincode=pincode,
            price_per_hour=price_per_hour,
            opening_time=opening_time,
            closing_time=closing_time,
            image1=image1,
        )
        # Add selected facilities
        turf.facilities.set(facilities)
        messages.success(request, 'Turf registered successfully!')
        return redirect('ownerhome')  # Change to your desired page

    facilities = Facility.objects.all()
    return render(request, 'turfreg.html', {'facilities': facilities})

@login_required
def userhome(request):
    turfs= Turf.objects.filter(is_approved=True)
    user_id=request.user.id
    bookings=TurfBooking.objects.filter(user_id=user_id).select_related('turf')
    location = request.GET.get('location', '').strip()
    date = request.GET.get('date', '').strip()

    # Filter by location (case-insensitive match)
    if location:
        turfs = turfs.filter(
            Q(city__icontains=location) | Q(state__icontains=location) | Q(address__icontains=location)
        )

    # Filter by date (if your Turf has an availability model, adapt here)
    if date:
        try:
            filter_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            turfs = turfs.filter(available_dates__contains=filter_date)  # Example: ManyToMany or availability field
        except ValueError:
            pass
        
    context = {
        'turfs': turfs,
        'bookings': bookings,
        'selected_location': location,
    }
    return render(request, 'userhome.html',context)

def admindash(request):
    turfapproved = Turf.objects.filter(is_approved = True)
    turfpending = Turf.objects.filter(is_approved = False)
    turfusers = User.objects.all()
    context = {
        'turfpending' : turfpending,
        'turfapproved': turfapproved,
        'turfusers' : turfusers
    }
    if request.user.role == 'admin':
        return render(request, 'admindash.html',context)
    
    
@login_required
def ownerhome(request):
    
    pendingTurf = request.user.turfs.filter(is_approved = False)
    approvedTurf = request.user.turfs.filter(is_approved = True)
    context = {
        'pending': pendingTurf,
        'approved': approvedTurf,
    }
    return render(request, 'ownerhome.html', context)

def turfreq(request):
    pending_turfs = Turf.objects.filter(is_approved=False)
    return render(request, 'turfreq.html', {'pending_turfs': pending_turfs})


def manageturf(request):
    turfs = Turf.objects.filter(is_approved = True)
    context = {
        'turfs': turfs
    }
    return render(request, 'manageturf.html', context)

def approve_turf(request, turf_id):
    turf = Turf.objects.get(id=turf_id)
    turf.is_approved = True
    turf.save()
    messages.success(request, f"Turf '{turf.turf_name}' approved successfully.")
    return redirect('turfreq')

def reject_turf(request, turf_id):
    turf = Turf.objects.get(id=turf_id)
    turf.delete()
    messages.warning(request, f"Turf '{turf.turf_name}' rejected and removed.")
    return redirect('turfreq')


def booking(request,id):

    turf=Turf.objects.get(id=id)
    user_id = request.user
    if request.method == "POST":
        turf_id = request.POST.get("turf")
        booking_date = request.POST.get("date")
        start_time = request.POST.get("start_time")
        duration = Decimal(request.POST.get("duration"))
        start_dt = datetime.strptime(start_time, "%H:%M")

        # Add duration
        end_dt = start_dt + timedelta(hours=int(duration))

        # Extract end_time in same format
        end_time = end_dt.strftime("%H:%M")
        bookings = TurfBooking.objects.filter(turf=turf_id, booking_date=booking_date)
        start_time_t = datetime.strptime(start_time, "%H:%M")
        end_time_t = datetime.strptime(end_time, "%H:%M")
        
        now = datetime.now()
        current_time = datetime.strptime(now.strftime("%H:%M"), "%H:%M")
        
        today = date.today()
        booking_date_time = datetime.strptime(booking_date, "%Y-%m-%d").date()
        if booking_date_time < today:
            messages.error(request, "Cannot book in the past.")
            return render(request,"booking.html")
        
        if booking_date_time == today:
            if start_time_t < current_time:
                messages.error(request, "Start time is in the past.")
                return render(request,"booking.html")
                
        for book in bookings:
            if start_time_t.time()<turf.opening_time or end_time_t.time()>turf.closing_time:
                messages.error(request, "Booking is outside turf operating hours.")
                return render(request,"turf_booking.html",{"turf": turf})
            
            if start_time_t.time() < book.end_time and end_time_t.time() > book.start_time:
                 messages.error(request, "Time slot overlaps with an existing booking.")
                 return render(request,"booking.html",{"turf": turf})
        TurfBooking.objects.create(user=user_id,turf=turf,start_time=start_time,booking_date=booking_date,end_time=end_time,total_amount=turf.price_per_hour * duration)
        messages.success(request, "Booking successful!")
        return redirect('userhome')
                
    return render(request,"booking.html",{'turf':turf})


def listbooking(request):
    user_id=request.user.id
    bookings=TurfBooking.objects.filter(user_id=user_id).select_related('turf')
    return render(request,'listbooking.html',{'bookings':bookings})

def manageusers(request):
    allusers = User.objects.all()
    return render(request,'manageusers.html',{'allusers': allusers})

