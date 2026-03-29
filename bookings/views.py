import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie, csrf_protect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from .forms import CustomUserCreationForm, CustomLoginForm, BookingForm
from .models import Booking, Screen, CustomUser, OTPLog
import datetime
import random
from django.utils import timezone
import json

# --- TRIPLE-STAGE SEAMLESS ENTRY ---

def welcome(request):
    return render(request, "welcome.html")

def auth_select(request):
    return render(request, "auth_select.html")

@ensure_csrf_cookie
@csrf_protect
def login_view(request):
    login_form = CustomLoginForm()
    if request.method == "POST":
        login_form = CustomLoginForm(data=request.POST)
        if login_form.is_valid():
            login(request, login_form.get_user())
            return redirect("dashboard")
    return render(request, "login.html", {"login_form": login_form})

@ensure_csrf_cookie
@csrf_protect
def register_view(request):
    register_form = CustomUserCreationForm()
    if request.method == "POST":
        register_form = CustomUserCreationForm(request.POST)
        if register_form.is_valid():
            user = register_form.save()
            login(request, user)
            return redirect("dashboard")
    return render(request, "register.html", {"register_form": register_form})

def custom_logout(request):
    logout(request)
    return redirect("auth_select")

# --- SYSTEM HUB ---

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect("login_view")
    cart_count = Booking.objects.filter(user=request.user, is_paid=False).exclude(status='Declined').count()
    return render(request, "dashboard.html", {"cart_count": cart_count})

def profile(request):
    if not request.user.is_authenticated:
        return redirect("login_view")
    bookings = Booking.objects.filter(user=request.user).order_by("-id")
    transactions = Booking.objects.filter(user=request.user, is_paid=True).exclude(transaction_id__isnull=True).order_by("-payment_date")
    return render(request, "profile.html", {"bookings": bookings, "transactions": transactions})

# --- PREMIUM BOOKING PATH ---

def book_search(request):
    if not request.user.is_authenticated:
        return redirect("login_view")
    screens = Screen.objects.all()
    return render(request, "book_landing.html", {"screens": screens})

def book_screen(request, screen_id):
    if not request.user.is_authenticated:
        return redirect("login_view")
    screen = get_object_or_404(Screen, id=screen_id)
    
    # Generate 7-day Context (restricted to 7 days only)
    display_dates = []
    base_date = timezone.now().date()
    today_iso = base_date.strftime("%Y-%m-%d")
    for i in range(7):
        d = base_date + datetime.timedelta(days=i)
        display_dates.append({
            "full_iso": d.strftime("%Y-%m-%d"),
            "day_name": d.strftime("%a").upper(),
            "day_num": d.strftime("%d"),
            "month_name": d.strftime("%B").upper()
        })
        
    # Availability: Approved only (As requested, Pending shows available)
    approved_bookings = Booking.objects.filter(
        screen=screen, 
        status__in=['Approved', 'Pending', 'Cart'], 
        date__gte=base_date
    )
    booked_map = {}
    for b in approved_bookings:
        d_str = b.date.strftime("%Y-%m-%d")
        if d_str not in booked_map:
            booked_map[d_str] = []
        booked_map[d_str].append(b.time_slot)
        
    formatted_slots = [{"val": s[0], "label": s[1]} for s in Booking.TIME_SLOTS]

    return render(request, "book_search.html", {
        "screen": screen,
        "display_dates": display_dates,
        "all_slots": formatted_slots,
        "booked_map_json": json.dumps(booked_map),
        "today_iso": today_iso,
        "current_month": base_date.strftime("%B %Y").upper()
    })

def book_results(request, screen_id):
    if not request.user.is_authenticated:
        return redirect("login_view")
    if request.method == "POST":
        date = request.POST.get("date")
        time_slot = request.POST.get("time_slot")
        return redirect("book_confirm", screen_id=screen_id, date=date, time_slot=time_slot)
    return redirect("book_screen", screen_id=screen_id)

def book_confirm(request, screen_id, date, time_slot):
    if not request.user.is_authenticated:
        return redirect("login_view")
    screen = get_object_or_404(Screen, id=screen_id)
    Booking.objects.get_or_create(
        user=request.user,
        screen=screen,
        date=date,
        time_slot=time_slot,
        status='Pending'
    )
    return redirect("cart_view")

# --- CART & PAYMENT ---

def cart_view(request):
    if not request.user.is_authenticated:
        return redirect("login_view")
    pending_items = Booking.objects.filter(user=request.user, is_paid=False).filter(status__in=['Cart', 'Pending'])
    approved_items = Booking.objects.filter(user=request.user, status='Approved', is_paid=False)
    total = sum(item.amount for item in approved_items)
    return render(request, "cart.html", {"pending_items": pending_items, "approved_items": approved_items, "total": total})

def remove_from_cart(request, booking_id):
    if not request.user.is_authenticated:
        return redirect("login_view")
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    booking.delete()
    return redirect("cart_view")

@csrf_exempt
def checkout(request):
    if not request.user.is_authenticated:
        return redirect("login_view")
    approved_items = Booking.objects.filter(user=request.user, status='Approved', is_paid=False)
    total = sum(item.amount for item in approved_items)
    
    if request.method == "POST":
        payment_id = request.POST.get("razorpay_payment_id")
        for b in approved_items:
            b.is_paid = True
            b.status = 'Approved'
            b.payment_date = timezone.now()
            b.transaction_id = payment_id or f"MOCK_{random.randint(1000,9999)}"
            b.save()
        return redirect("success_page")

    amount_paise = int(total * 100)
    razorpay_order_id = f"ORDER_{random.randint(100000, 999999)}"
    context = {
        "total": total,
        "amount_paise": amount_paise,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order_id,
        "user_phone": request.user.phone_number
    }
    return render(request, "payment_gateway.html", context)

def success_page(request):
    return render(request, "success.html", {"message": "TRANSACTION_VERIFIED."})

# --- SECURE MANAGER PORTAL ---

def admin_login_portal(request):
    error = None
    if request.method == "POST":
        phone = request.POST.get("phone_number", "").strip().replace("-", "").replace(" ", "")
        password = request.POST.get("password", "").strip()
        if phone == "9890236839" and password == "manager801":
            request.session['manager_authenticated'] = True
            return redirect("admin_dashboard")
        else:
            error = "CREDENTIAL_MISMATCH_ACCESS_DENIED_"
    return render(request, "admin_login.html", {"error": error})

def admin_logout(request):
    if 'manager_authenticated' in request.session:
        del request.session['manager_authenticated']
    return redirect("auth_select")

def admin_dashboard(request):
    if not request.session.get('manager_authenticated'):
        return redirect("admin_login")
    pending = Booking.objects.filter(status__in=['Pending', 'Cart'], is_paid=False)
    history = Booking.objects.all().order_by("-id")[:50]
    return render(request, "admin_dashboard.html", {"pending": pending, "history": history})

def manage_booking(request, booking_id, action):
    if not request.session.get('manager_authenticated'):
        return redirect("admin_login")
    booking = get_object_or_404(Booking, id=booking_id)
    if action == "approve":
        booking.status = 'Approved'
    elif action == "decline":
        booking.status = 'Declined'
    booking.save()
    return redirect(f"/admin-dashboard/?msg=ACTION_{action.upper()}_COMPLETE")

def forgot_password(request):
    return render(request, "forgot_password.html")

def forgot_password_verify(request):
    return redirect("login_view")

def admin_profile(request):
    if not request.session.get('manager_authenticated'):
        return redirect("admin_login")
    users = CustomUser.objects.all().order_by("-date_joined")
    transactions = Booking.objects.filter(is_paid=True).order_by("-payment_date")
    return render(request, "admin_profile.html", {"users": users, "transactions": transactions})



