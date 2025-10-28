# store/urls.py
from django.urls import path
from . import views
app_name = 'order'

urlpatterns = [
    # ... your existing routes ...
    path('checkout/', views.checkout, name='checkout'),
    path('order/success/<int:order_id>/', views.order_success, name='order_success'),
    path('order/lookup/', views.order_lookup, name='order_lookup'),
    path('get-delivery-charge/', views.get_delivery_charge, name='get_delivery_charge'),
    path("save-email/", views.save_email, name="save_email"),
]
