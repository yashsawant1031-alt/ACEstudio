from django.urls import path
from . import views

urlpatterns = [
    path("", views.welcome, name="welcome"),
    path("login/", views.login_view, name="login_view"),
    path("register/", views.register_view, name="register_view"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("book/", views.book_search, name="book_search"),
    path("book/screen/<int:screen_id>/", views.book_screen, name="book_screen"),
    path("book/confirm/<int:screen_id>/<str:date>/<str:time_slot>/", views.book_confirm, name="book_confirm"),
    path("profile/", views.profile, name="profile"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path('success/', views.success_page, name='success_page'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manage-booking/<int:booking_id>/<str:action>/', views.manage_booking, name='manage_booking'),
    path('admin-portal/login/', views.admin_login_portal, name='admin_login'),
    
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:screen_id>/<str:date>/<str:time_slot>/', views.book_confirm, name='add_to_cart'),
    path('cart/remove/<int:booking_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('password-reset/verify/', views.forgot_password_verify, name='forgot_password_verify'),
]
