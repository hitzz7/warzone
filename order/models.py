from django.db import models
from store.models import Coupon
# Create your models here.
   
class City(models.Model):
    name = models.CharField(max_length=100)
    delivery_charge = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return self.name    

class Order(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)
    landmark = models.TextField(default='', blank=True)
    delivery_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Order {self.id} - {self.name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey("store.Product", on_delete=models.SET_NULL, null=True, blank=True)
    variant = models.ForeignKey("store.ProductVariant", on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sku = models.CharField(max_length=100, blank=True, null=True)
    size = models.CharField(max_length=64, blank=True, null=True)
    color = models.CharField(max_length=64, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    image_url = models.URLField(blank=True)
    

    def __str__(self):
        return f"{self.title} (x{self.quantity})"
    
    
class UserInfo(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"