from . import views
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
app_name = 'store'

urlpatterns = [
    path('',views.home, name="home"),
    path("products", views.product_list, name="product_list"),   
    path("category/<slug:parent_slug>/<slug:category_slug>/", views.product_list, name="subcategory_products"),
    path("category/<slug:category_slug>/", views.product_list, name="category_products"),  
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/json/", views.cart_json, name="cart_json"),           # GET -> return cart as JSON
    path("cart/add/", views.cart_add, name="cart_add"),             # POST -> add variant to cart
    path("cart/update/", views.cart_update, name="cart_update"),    # POST -> set quantity
    path("cart/remove/", views.cart_remove, name="cart_remove"),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('search-json/', views.search_json, name='search_json'),
   
]

