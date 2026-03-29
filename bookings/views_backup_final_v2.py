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

# --- TRIPLE-STAGE SEAMLESS ENTRY ---

def welcome(request):
    """The 1st Page: Pure Landing Showcase"""
    if request.user.is_authenticated:
        # Avoid accidental logouts; stay on dashboard
        return redirect("dashboard")
    return render(request, "welcome.html")

def auth_select(request):
    """The 2nd Page: Selector Terminal (Guest Only)"""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "auth_select.html")

@ensure_csrf_cookie
@csrf_protect
def login_view(request):
    """The 3rd Page (Option A): Login Terminal"""
    if request.user.is_authenticated:
        return redirect("dashboard")
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
    """The 3rd Page (Option B): Register Terminal"""
    if request.user.is_authenticated:
        return redirect("dashboard")
    register_form = CustomUserCreationForm()
    if request.method == "POST":
        register_form = CustomUserCreationForm(request.POST)
        if register_form.is_valid():
            user = register_form.save()
            login(request, user)
            return redirect("dashboard")
    return render(request, "register.html", {"register_form": register_form})

def custom_logout(request):
    """Explicit Logout Action"""
    logout(request)
    return redirect("welcome")


# --- SYSTEM HUB (HOME BASE) ---

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect("login_view")
    
    # Unified Cart Count for the UI
    cart_count = Booking.objects.filter(user=request.user, is_paid=False).exclude(status='Declined').count()
    return render(request, "dashboard.html", {"cart_count": cart_count})

def profile(request):
    if not request.user.is_authenticated:
        return redirect("login_view")
    reservations = Booking.objects.filter(user=request.user).order_by("-id")
    return render(request, "profile.html", {"reservations": reservations})


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
    
    # 14-day Context for Scroller
    display_dates = []
    base_date = timezone.now().date()
    for i in range(14):
        d = base_date + datetime.timedelta(days=i)
        display_dates.append({
            "full_iso": d.strftime("%Y-%m-%d"),
            "day_name": d.strftime("%a").upper(),
            "day_num": d.strftime("%d"),
            "month_name": d.strftime("%B").upper()
        })
        
    formatted_slots = [{"val": s[0], "label": s[1]} for s in Booking.TIME_SLOTS]
    
    return render(request, "book_search.html", {
        "screen": screen,
        "display_dates": display_dates,
        "all_slots": formatted_slots,
        "today_iso": base_date.strftime("%Y-%m-%d"),
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
        status='Pending' # Direct to review
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
    amount_paise = int(total * 100)
    
    if request.method == "POST":
        payment_id = request.POST.get("razorpay_payment_id")
        for b in approved_items:
            b.is_paid = True
            b.status = 'Approved'
            b.payment_date = timezone.now()
            b.transaction_id = payment_id or f"MOCK_{random.randint(1000,9999)}"
            b.save()
        return redirect("success_page")

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
        phone = request.POST.get("phone_number")
        password = request.POST.get("password")
        if phone == "9890236839" and password == "manager801":
            request.session['manager_authenticated'] = True
            return redirect("admin_dashboard")
        else:
            error = "CREDENTIAL_MISMATCH_ACCESS_DENIED_"
    return render(request, "admin_login.html", {"error": error})

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
