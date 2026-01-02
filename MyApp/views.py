from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User,Turf,Facility,TurfBooking,Review
from datetime import datetime,date, timedelta
from decimal import Decimal
from django.db.models import Q,Avg,Count,Sum
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.utils.timezone import now
from reportlab.lib.pagesizes import letter
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import letter
from django.db.models.functions import TruncMonth
import json
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

User = get_user_model()

def landing(request):
    return render(request,'landing.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.is_blocked:  
                messages.error(request, "Your account has been blocked. Contact admin.")
                return redirect("login")

            login(request, user)
            messages.success(request, "Login Successful!")

            if user.role == 'admin':
                return redirect('admindash')
            elif user.role == 'owner':
                return redirect('ownerhome')
            else:
                return redirect("userhome")

        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html')

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

        # Create user using custom manager
        User.objects.create_user(
            email=email,
            password=password,
            fullname=fullname,
            phone=phone,
            role=user_type,
        )

        messages.success(request, "Account created successfully.")
        
        return redirect('login')

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
    messages.success(request, "You have been logged out successfully!")
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
    now = timezone.now().date()
    bookings=TurfBooking.objects.filter(user_id=user_id).select_related('turf')
    upcoming_bookings = bookings.filter(booking_date__gte=now).order_by("booking_date")
    past_bookings = bookings.filter(booking_date__lt=now).order_by("-booking_date")
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
        "past_bookings": past_bookings, 
        "upcoming_bookings":upcoming_bookings,
    }
    return render(request, 'userhome.html',context)

def admindash(request):
    turfapproved = Turf.objects.filter(is_approved = True)
    turfpending = Turf.objects.filter(is_approved = False)
    turfusers = User.objects.all()
    owners = (
        User.objects.filter(role="owner")  # Only owners
        .annotate(
            total_revenue=Sum("turfs__bookings__total_amount"),   # Sum of all bookings revenue
            turfs_owned=Count("turfs", distinct=True)             # Count of turfs owned
        )
        .filter(total_revenue__isnull=False)   # Exclude owners with no bookings
        .order_by("-total_revenue")[:10]       # Top 10 owners by revenue
    )
    topturf = (
        Turf.objects.annotate(total_bookings=Count("bookings"))
        .order_by("-total_bookings")
        .select_related("owner")
        .first()
    )

    turfearn = (
        Turf.objects.annotate(total_revenue=Sum("bookings__total_amount"))
        .order_by("-total_revenue")
        .select_related("owner")
        .first()
    )

    total_revenue = (
        TurfBooking.objects.filter(status__in=["confirmed", "completed"])
        .aggregate(total=Sum("total_amount"))["total"] or 0
    )


    context = {
        'turfpending' : turfpending,
        'turfapproved': turfapproved,
        'turfusers' : turfusers,
        "owners": owners,
        "topturf": topturf,
        "turfearn": turfearn,
        "total_revenue": total_revenue,
    }
    if request.user.role == 'admin':
        return render(request, 'admindash.html',context)
    
    
@login_required
def ownerhome(request):
    pendingTurf = request.user.turfs.filter(is_approved=False)
    approvedTurf = request.user.turfs.filter(is_approved=True)

    bookings = TurfBooking.objects.filter(turf__owner=request.user).select_related("turf", "user").order_by('-booking_date')
    current_year = datetime.now().year
    total_revenue = bookings.aggregate(total=Sum('total_amount'))['total'] or 0
    avg_rating = Review.objects.filter(turf__owner=request.user).aggregate(avg=Avg('rating'))['avg'] or 0
    total_bookings = bookings.count()
    pending_count = request.user.turfs.filter(is_approved=False).count()

     # 1. Query the database to get earnings grouped by month for confirmed bookings
    earnings_data = TurfBooking.objects.filter(
        turf__owner=request.user,
        status='confirmed',  # Only count confirmed payments
        booking_date__year=current_year
    ).annotate(
        month=TruncMonth('booking_date')
    ).values(
        'month'
    ).annotate(
        total_earnings=Sum('total_amount')
    ).order_by('month')

    # 2. Prepare the data for the chart (ensuring all 12 months are present)
    earnings_per_month = {i: 0 for i in range(1, 13)} # Initialize all months to 0
    for entry in earnings_data:
        month_number = entry['month'].month
        earnings_per_month[month_number] = float(entry['total_earnings']) # Use float for JSON

    # 3. Create final lists for labels and data
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_earnings_data = [earnings_per_month[i] for i in range(1, 13)]


    context = {
        'pending': pendingTurf,
        'approved': approvedTurf,
        'bookings': bookings,
        'monthly_earnings_labels': json.dumps(month_labels),
        'monthly_earnings_data': json.dumps(monthly_earnings_data),
        "total_revenue": total_revenue,
        "total_bookings": total_bookings,
        "avg_rating": round(avg_rating, 1),
        "pending_count": pending_count,
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


def booking(request, id):
    turf = Turf.objects.get(id=id)
    user = request.user

    if request.method == "POST":
        turf_id = request.POST.get("turf")
        booking_date = request.POST.get("date")
        start_time = request.POST.get("start_time")
        duration = Decimal(request.POST.get("duration"))
        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt = start_dt + timedelta(hours=int(duration))

        end_time = end_dt.strftime("%H:%M")
        bookings = TurfBooking.objects.filter(turf=turf_id, booking_date=booking_date)
        start_time_t = datetime.strptime(start_time, "%H:%M")
        end_time_t = datetime.strptime(end_time, "%H:%M")

        today = date.today()
        booking_date_time = datetime.strptime(booking_date, "%Y-%m-%d").date()
        now = datetime.now()
        current_time = datetime.strptime(now.strftime("%H:%M"), "%H:%M")

        if booking_date_time < today:
            messages.error(request, "Cannot book in the past.")
            return render(request, "booking.html", {"turf": turf})
        
        if start_time_t.time() < turf.opening_time:
            messages.error(request, f"Turf opens at {turf.opening_time.strftime('%H:%M')}. Please select a valid time.")
            return render(request, "booking.html", {"turf": turf})

        if end_time_t.time() > turf.closing_time:
            messages.error(request, f"Turf closes at {turf.closing_time.strftime('%H:%M')}. Please select a valid time.")
            return render(request, "booking.html", {"turf": turf})
        
        if booking_date_time == today:
            if start_time_t < current_time:
                messages.error(request, "Start time is in the past.")
                return render(request, "booking.html", {"turf": turf})

        for book in bookings:
            if start_time_t.time() < turf.opening_time or end_time_t.time() > turf.closing_time:
                messages.error(request, "Booking outside turf operating hours.")
                return render(request, "booking.html", {"turf": turf})

            if start_time_t.time() < book.end_time and end_time_t.time() > book.start_time:
                messages.error(request, "Time slot overlaps with an existing booking.")
                return render(request, "booking.html", {"turf": turf})

        total_amount = turf.price_per_hour * duration

        # ✅ Create Razorpay Order
        razorpay_order = razorpay_client.order.create({
            "amount": int(total_amount * 100),  # amount in paisa
            "currency": "INR",
            "payment_capture": "1"
        })

        # Create booking with status pending
        booking = TurfBooking.objects.create(
            user=user,
            turf=turf,
            start_time=start_time_t,
            booking_date=booking_date_time,
            end_time=end_time_t,
            total_amount=total_amount,
            status="pending"
        )

        context = {
            "turf": turf,
            "booking": booking,
            "razorpay_order_id": razorpay_order["id"],
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "amount": int(total_amount),
            "currency": "INR",
            "booking_date": booking.booking_date,
            "start_time": booking.start_time,
            "end_time": booking.end_time,
            
        }
        return render(request, "payment.html", context)

    # GET Request
    average_rating = turf.reviews.aggregate(avg=Avg("rating"))["avg"]
    reviews_count = turf.reviews.aggregate(count=Count("id"))["count"]
    has_booked = TurfBooking.objects.filter(user=request.user, turf=turf).exists()

    context = {
        "turf": turf,
        "average_rating": round(average_rating) if average_rating else None,
        "reviews_count": reviews_count,
        "has_booked": has_booked
    }
    return render(request, "booking.html", context)


@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        payment_id = request.POST.get("razorpay_payment_id")
        order_id = request.POST.get("razorpay_order_id")
        signature = request.POST.get("razorpay_signature")
        booking_id = request.POST.get("booking_id")

        booking = TurfBooking.objects.get(id=booking_id)

        try:
            # Verify payment signature
            razorpay_client.utility.verify_payment_signature({
                "razorpay_payment_id": payment_id,
                "razorpay_order_id": order_id,
                "razorpay_signature": signature
            })

            booking.status = "confirmed"
            booking.save()
            messages.success(request, "Payment Successful! Booking confirmed.")
            return redirect("userhome")

        except:
            booking.status = "cancelled"
            booking.save()
            messages.error(request, "Payment verification failed.")
            return redirect("userhome")


def listbooking(request):
    user_id = request.user.id
    bookings = (
        TurfBooking.objects.filter(user_id=user_id)
        .select_related('turf')
        .order_by('-id')   # latest first
    )
    return render(request, 'listbooking.html', {'bookings': bookings})


def manageusers(request):
    allusers = User.objects.all()
    return render(request,'manageusers.html',{'allusers': allusers})


def block_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_blocked = True   
    user.save()
    messages.success(request, f"{user.fullname} has been blocked.")
    return redirect('manageusers')

def unblock_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_blocked = False  
    user.save()
    messages.success(request, f"{user.fullname} has been unblocked.")
    return redirect('manageusers')

def confirm_booking(request, booking_id):
    booking = get_object_or_404(TurfBooking, id=booking_id, turf__owner=request.user)

    if booking.status == "pending":
        booking.status = "confirmed"
        booking.save()
        messages.success(request, "Booking confirmed successfully.")
    else:
        messages.warning(request, "This booking is already confirmed or completed.")

    return redirect('ownerhome')

def download_invoice(request, booking_id):
    try:
        booking = TurfBooking.objects.get(id=booking_id, user=request.user)
    except TurfBooking.DoesNotExist:
        raise Http404("Booking not found")

    # HTTP response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice-{booking.id}.pdf"'

    # Document setup with smaller margins for a more modern look
    doc = SimpleDocTemplate(response, pagesize=letter,
                            rightMargin=30, leftMargin=30,
                            topMargin=40, bottomMargin=30)

    elements = []
    styles = getSampleStyleSheet()

    # Custom color palette
    primary_color = colors.HexColor("#22c55e")  # Green accent
    dark_color = colors.HexColor("#1a1a1a")     # Near black
    light_color = colors.HexColor("#f8fafc")    # Light background
    gray_color = colors.HexColor("#64748b")     # Medium gray
    light_gray = colors.HexColor("#e2e8f0")     # Light gray for borders

    # Custom styles
    title_style = ParagraphStyle(
        "title_style",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=dark_color,
        alignment=TA_CENTER,
        spaceAfter=10,
        fontName="Helvetica-Bold"
    )
    
    subtitle_style = ParagraphStyle(
        "subtitle_style",
        parent=styles["Normal"],
        fontSize=12,
        textColor=gray_color,
        alignment=TA_CENTER,
        spaceAfter=30,
        fontName="Helvetica"
    )
    
    section_header_style = ParagraphStyle(
        "section_header",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=dark_color,
        spaceAfter=12,
        fontName="Helvetica-Bold"
    )
    
    normal_style = ParagraphStyle(
        "normal_style",
        parent=styles["Normal"],
        fontSize=10,
        textColor=dark_color,
        fontName="Helvetica"
    )

    
    footer_style = ParagraphStyle(
        "footer_style",
        parent=styles["Normal"],
        fontSize=9,
        textColor=gray_color,
        alignment=TA_CENTER,
        fontName="Helvetica"
    )

    # --- Header Section ---
    # Add a decorative line at the top
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>TURFZONE</b>", title_style))
    elements.append(Paragraph("INVOICE", subtitle_style))
    
    # Invoice and date on same line
    invoice_data = [
        [Paragraph(f"<b>Invoice No:</b> TZ{booking.id}", normal_style),
         Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d %b, %Y')}", normal_style)]
    ]
    invoice_table = Table(invoice_data, colWidths=[270, 270])
    invoice_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(invoice_table)
    
    # Divider line
    elements.append(HRFlowable(width="100%", thickness=1, color=light_gray, spaceAfter=20))

    # --- Booking Details ---
    elements.append(Paragraph("BOOKING DETAILS", section_header_style))
    
    booking_info = [
        ["Customer:", booking.user.fullname],
        ["Turf:", booking.turf.turf_name],
        ["Location:", f"{booking.turf.city}, {booking.turf.state}"],
        ["Booking Date:", str(booking.booking_date)],
        ["Time Slot:", f"{booking.start_time} - {booking.end_time}"],
    ]
    
    table = Table(booking_info, hAlign="LEFT", colWidths=[100, 440])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), gray_color),
        ("TEXTCOLOR", (1, 0), (1, -1), dark_color),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, -1), light_color),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 25))

    # --- Pricing Details ---
    elements.append(Paragraph("PRICE SUMMARY", section_header_style))
    
    # Calculate hours with proper decimal handling
    try:
        
        start = datetime.combine(date.today(), booking.start_time)
        end = datetime.combine(date.today(), booking.end_time)

        # Handle case where end_time is next day (overnight booking)
        if end < start:
            end = end.replace(day=end.day + 1)

        time_diff = end - start   # this gives timedelta
        hours = time_diff.total_seconds() / 3600
        
        # Convert Decimal to float for calculation
        total_amount_float = float(booking.total_amount)
        rate_per_hour = total_amount_float / hours if hours > 0 else total_amount_float
        
        # Format for display
        hours_str = f"{hours:.1f}"
        rate_str = f"{rate_per_hour:.0f}"
    except (TypeError, AttributeError, ValueError):
        # Fallback if there's any issue with the calculation
        hours_str = "N/A"
        rate_str = "N/A"
    
    pricing_data = [
        ["Description", "Hours", "Rate (INR)", "Amount (INR)"],
        ["Turf Booking", hours_str, rate_str, f"{booking.total_amount} INR"]
    ]
    
    pricing_table = Table(pricing_data, colWidths=[220, 80, 80, 100])
    pricing_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, light_gray),
        ("BACKGROUND", (0, 1), (-1, -1), light_color),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("FONTNAME", (3, -1), (3, -1), "Helvetica-Bold"),
    ]))
    elements.append(pricing_table)
    elements.append(Spacer(1, 15))
    
    # Total row
    total_data = [
        ["", "", "Total:", f"{booking.total_amount} INR"]
    ]
    total_table = Table(total_data, colWidths=[220, 80, 80, 100])
    total_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("ALIGN", (3, 0), (3, 0), "RIGHT"),
        ("FONTNAME", (2, 0), (3, 0), "Helvetica-Bold"),
        ("LINEABOVE", (2, 0), (3, 0), 1, dark_color),
    ]))
    elements.append(total_table)
    elements.append(Spacer(1, 30))

    # --- Payment Method ---
    elements.append(Paragraph("PAYMENT METHOD", section_header_style))
    payment_info = [
        ["Method:", "Online Payment"],
        ["Status:", "Paid"],
        ["Date:", str(booking.booking_date)]
    ]
    
    payment_table = Table(payment_info, hAlign="LEFT", colWidths=[100, 440])
    payment_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), gray_color),
        ("TEXTCOLOR", (1, 0), (1, -1), dark_color),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, -1), light_color),
    ]))
    elements.append(payment_table)
    elements.append(Spacer(1, 40))

    # --- Footer ---
    elements.append(HRFlowable(width="100%", thickness=0.5, color=light_gray, spaceAfter=12))
    elements.append(Paragraph("Thank you for your business!", footer_style))
    elements.append(Paragraph("Questions? Email support@turfzone.com or visit www.turfzone.com", footer_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("TurfZone • 123 Sports Avenue • City, State 12345", footer_style))

    # Build PDF
    doc.build(elements)
    return response


def turf_detail(request, turf_id):
    turf = get_object_or_404(Turf, id=turf_id)

    # Calculate overall average rating
    reviews = turf.reviews.all()
    reviews_count = turf.reviews.aggregate(count=Count("id"))["count"]
    

    context = {
        "turf": turf,
        "reviews": reviews,
        "reviews_count": reviews_count,
    }
    return render(request, "booking.html", context)


def add_review(request, turf_id):
    turf = Turf.objects.get(id=turf_id)

    if request.method == "POST":
        rating = request.POST.get("rating")
        comment = request.POST.get("comment")

        created = Review.objects.update_or_create(
            turf=turf,
            user=request.user,
            defaults={
                "rating": rating,
                "comment": comment
            }
        )

        if created:
            messages.success(request, "Review submitted successfully!")
        else:
            messages.success(request, "Your review has been updated!")

        return redirect("turf_detail", turf_id=turf.id)
    


def view_invoice(request, booking_id):
    try:
        booking = TurfBooking.objects.get(id=booking_id, user=request.user)
    except TurfBooking.DoesNotExist:
        raise Http404("Booking not found")

    # HTTP response (inline instead of attachment)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="invoice-{booking.id}.pdf"'

    # reuse same invoice logic as download_invoice
    doc = SimpleDocTemplate(response, pagesize=letter,
                            rightMargin=30, leftMargin=30,
                            topMargin=40, bottomMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
    primary_color = colors.HexColor("#22c55e")  # Green accent
    dark_color = colors.HexColor("#1a1a1a")     # Near black
    light_color = colors.HexColor("#f8fafc")    # Light background
    gray_color = colors.HexColor("#64748b")     # Medium gray
    light_gray = colors.HexColor("#e2e8f0")     # Light gray for borders

    # Custom styles
    title_style = ParagraphStyle(
        "title_style",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=dark_color,
        alignment=TA_CENTER,
        spaceAfter=10,
        fontName="Helvetica-Bold"
    )
    
    subtitle_style = ParagraphStyle(
        "subtitle_style",
        parent=styles["Normal"],
        fontSize=12,
        textColor=gray_color,
        alignment=TA_CENTER,
        spaceAfter=30,
        fontName="Helvetica"
    )
    
    section_header_style = ParagraphStyle(
        "section_header",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=dark_color,
        spaceAfter=12,
        fontName="Helvetica-Bold"
    )
    
    normal_style = ParagraphStyle(
        "normal_style",
        parent=styles["Normal"],
        fontSize=10,
        textColor=dark_color,
        fontName="Helvetica"
    )

    
    footer_style = ParagraphStyle(
        "footer_style",
        parent=styles["Normal"],
        fontSize=9,
        textColor=gray_color,
        alignment=TA_CENTER,
        fontName="Helvetica"
    )

    # --- Header Section ---
    # Add a decorative line at the top
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>TURFZONE</b>", title_style))
    elements.append(Paragraph("INVOICE", subtitle_style))
    
    # Invoice and date on same line
    invoice_data = [
        [Paragraph(f"<b>Invoice No:</b> TZ{booking.id}", normal_style),
         Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d %b, %Y')}", normal_style)]
    ]
    invoice_table = Table(invoice_data, colWidths=[270, 270])
    invoice_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(invoice_table)
    
    # Divider line
    elements.append(HRFlowable(width="100%", thickness=1, color=light_gray, spaceAfter=20))

    # --- Booking Details ---
    elements.append(Paragraph("BOOKING DETAILS", section_header_style))
    
    booking_info = [
        ["Customer:", booking.user.fullname],
        ["Turf:", booking.turf.turf_name],
        ["Location:", f"{booking.turf.city}, {booking.turf.state}"],
        ["Booking Date:", str(booking.booking_date)],
        ["Time Slot:", f"{booking.start_time} - {booking.end_time}"],
    ]
    
    table = Table(booking_info, hAlign="LEFT", colWidths=[100, 440])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), gray_color),
        ("TEXTCOLOR", (1, 0), (1, -1), dark_color),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, -1), light_color),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 25))

    # --- Pricing Details ---
    elements.append(Paragraph("PRICE SUMMARY", section_header_style))
    
    # Calculate hours with proper decimal handling
    try:
        
        start = datetime.combine(date.today(), booking.start_time)
        end = datetime.combine(date.today(), booking.end_time)

        # Handle case where end_time is next day (overnight booking)
        if end < start:
            end = end.replace(day=end.day + 1)

        time_diff = end - start   # this gives timedelta
        hours = time_diff.total_seconds() / 3600
        
        # Convert Decimal to float for calculation
        total_amount_float = float(booking.total_amount)
        rate_per_hour = total_amount_float / hours if hours > 0 else total_amount_float
        
        # Format for display
        hours_str = f"{hours:.1f}"
        rate_str = f"{rate_per_hour:.0f}"
    except (TypeError, AttributeError, ValueError):
        # Fallback if there's any issue with the calculation
        hours_str = "N/A"
        rate_str = "N/A"
    
    pricing_data = [
        ["Description", "Hours", "Rate (INR)", "Amount (INR)"],
        ["Turf Booking", hours_str, rate_str, f"{booking.total_amount} INR"]
    ]
    
    pricing_table = Table(pricing_data, colWidths=[220, 80, 80, 100])
    pricing_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, light_gray),
        ("BACKGROUND", (0, 1), (-1, -1), light_color),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("FONTNAME", (3, -1), (3, -1), "Helvetica-Bold"),
    ]))
    elements.append(pricing_table)
    elements.append(Spacer(1, 15))
    
    # Total row
    total_data = [
        ["", "", "Total:", f"{booking.total_amount} INR"]
    ]
    total_table = Table(total_data, colWidths=[220, 80, 80, 100])
    total_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("ALIGN", (3, 0), (3, 0), "RIGHT"),
        ("FONTNAME", (2, 0), (3, 0), "Helvetica-Bold"),
        ("LINEABOVE", (2, 0), (3, 0), 1, dark_color),
    ]))
    elements.append(total_table)
    elements.append(Spacer(1, 30))

    # --- Payment Method ---
    elements.append(Paragraph("PAYMENT METHOD", section_header_style))
    payment_info = [
        ["Method:", "Online Payment"],
        ["Status:", "Paid"],
        ["Date:", str(booking.booking_date)]
    ]
    
    payment_table = Table(payment_info, hAlign="LEFT", colWidths=[100, 440])
    payment_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), gray_color),
        ("TEXTCOLOR", (1, 0), (1, -1), dark_color),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, -1), light_color),
    ]))
    elements.append(payment_table)
    elements.append(Spacer(1, 40))

    # --- Footer ---
    elements.append(HRFlowable(width="100%", thickness=0.5, color=light_gray, spaceAfter=12))
    elements.append(Paragraph("Thank you for your business!", footer_style))
    elements.append(Paragraph("Questions? Email support@turfzone.com or visit www.turfzone.com", footer_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("TurfZone • 123 Sports Avenue • City, State 12345", footer_style))

    doc.build(elements)
    return response


@login_required
def edit_turf(request, turf_id):

    if request.method == "POST":
        turf = get_object_or_404(Turf, id=turf_id, owner=request.user)

        turf.turf_name = request.POST.get("turf_name")
        turf.description = request.POST.get("description")
        turf.price_per_hour = request.POST.get("price_per_hour")
        turf.opening_time = request.POST.get("opening_time")
        turf.closing_time = request.POST.get("closing_time")

        if request.FILES.get("image1"):
            turf.image1 = request.FILES["image1"]

        turf.save()
    
    return redirect("ownerhome")


def managebookings(request):
    
    today = now().date()

    # 1. Bookings Today
    bookings_today = TurfBooking.objects.filter(booking_date=today).count()

    # 2. Bookings This Week (Mon–Sun)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    bookings_week = TurfBooking.objects.filter(
        booking_date__range=[start_of_week, end_of_week]
    ).count()

    # 3. Bookings This Month
    bookings_month = TurfBooking.objects.filter(
        booking_date__year=today.year,
        booking_date__month=today.month,
    ).count()

    # 4. Total Cancellations
    total_cancellations = TurfBooking.objects.filter(status="cancelled").count()

    # 5. All bookings list with related turf & user
    all_bookings = (
        TurfBooking.objects.select_related("user", "turf")
        .order_by("-created_at")
    )

    context = {
        "bookings_today": bookings_today,
        "bookings_week": bookings_week,
        "bookings_month": bookings_month,
        "total_cancellations": total_cancellations,
        "all_bookings": all_bookings,
    }

    return render(request, 'managebookings.html', context)

def managepayments(request):

    total_revenue = (
        TurfBooking.objects.filter(status__in=["confirmed", "completed"])
        .aggregate(total=Sum("total_amount"))["total"] or 0
    )

    context = {
        "total_revenue":total_revenue
    }

    return render(request, 'managepayments.html',context)


def update_turf(request, turf_id):
    # Ensure the request is a POST request
    if request.method == 'POST':
        # Get the specific turf instance or return a 404 error if not found
        turf = get_object_or_404(Turf, pk=turf_id)

        # Update turf fields from the form data
        turf.turf_name = request.POST.get('turf_name')
        turf.price_per_hour = request.POST.get('price_per_hour')
        turf.opening_time = request.POST.get('opening_time')
        turf.closing_time = request.POST.get('closing_time')
        turf.description = request.POST.get('description')

        # Handle the image upload
        # request.FILES will contain the uploaded file data
        if 'image1' in request.FILES:
            turf.image1 = request.FILES['image1']
        
        # Save the updated turf object to the database
        turf.save()

        # Add a success message to be displayed on the next page
        messages.success(request, f"'{turf.turf_name}' has been updated successfully!")

        # Redirect back to the manage turfs page
        return redirect('manageturf') # Make sure 'manageturf' is the correct name of your url pattern

    # If not a POST request, just redirect back
    return redirect('manageturf')


@login_required
def delete_turf(request, turf_id):
    # Ensure the request is POST for security
    if request.method == 'POST':
        # Get the turf, ensuring it belongs to the logged-in user
        turf = get_object_or_404(Turf, id=turf_id, owner=request.user)
        
        # Check for any upcoming bookings for this turf
        upcoming_bookings = TurfBooking.objects.filter(
            turf=turf,
            booking_date__gte=date.today()
        ).exists()

        if upcoming_bookings:
            # If upcoming bookings exist, send an error message
            messages.error(request, f"Cannot delete '{turf.turf_name}' because there are upcoming bookings.")
        else:
            # If no upcoming bookings, delete the turf and send a success message
            turf_name = turf.turf_name
            turf.delete()
            messages.success(request, f"Turf '{turf_name}' has been deleted successfully.")
            
    # Redirect back to the owner's home page regardless of the outcome
    return redirect('ownerhome')


def delete_turf_admin(request, turf_id):
    # Ensure this is a POST request for security
    if request.method == 'POST':
        turf_to_delete = get_object_or_404(Turf, id=turf_id)
        today = date.today()

        # Check for any bookings on or after today's date
        has_upcoming_bookings = TurfBooking.objects.filter(
            turf=turf_to_delete,
            booking_date__gte=today
        ).exists()

        if has_upcoming_bookings:
            # If there are upcoming bookings, show an error message
            messages.error(request, 'Cannot delete this turf. It has upcoming bookings that are yet to be played.')
        else:
            # If no upcoming bookings, delete the turf and show a success message
            turf_name = turf_to_delete.turf_name
            turf_to_delete.delete()
            messages.success(request, f'Successfully deleted the turf: {turf_name}.')
            
    return redirect('manageturf')
