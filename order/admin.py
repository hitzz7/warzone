from decimal import Decimal
from django.contrib import admin
from django.utils.html import format_html

from .models import City, Order, OrderItem,UserInfo


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # allow editing quantity and maybe product/variant via raw id fields
    fields = (
        "thumbnail",
        "product",
        "variant",
        "title",
        "sku",
        "size",
        "color",
        "price",
        "quantity",
        "line_total",
    )
    readonly_fields = ("thumbnail", "title", "sku", "size", "color", "price", "line_total")
    raw_id_fields = ("product", "variant")  # keeps admin fast when many products
    can_delete = True  # set False if you never want to remove order items from admin

    def thumbnail(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="width:60px; height:auto; object-fit:cover; border-radius:4px;" />', obj.image_url)
        return "-"
    thumbnail.short_description = "Image"

    def line_total(self, obj):
        try:
            return f"{(obj.price or Decimal('0.00')) * obj.quantity:.2f}"
        except Exception:
            return "-"
    line_total.short_description = "Line total"


@admin.action(description="Mark selected orders as paid")
def mark_orders_paid(modeladmin, request, queryset):
    updated = queryset.update(is_paid=True)
    modeladmin.message_user(request, f"{updated} order(s) marked as paid.")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "phone", "city", "total_price", "discount_amount","coupon", "is_paid", "created_at")
    list_filter = ("is_paid", "city", "created_at")
    search_fields = ("name", "email", "phone", "address")
    readonly_fields = ("total_price", "created_at", "delivery_price")
    inlines = [OrderItemInline]
    actions = [mark_orders_paid]

    fieldsets = (
        (None, {
            "fields": (
                ("name", "email"),
                ("phone", "city"),
                "address",
                "landmark",
            )
        }),
        ("Payment & totals", {
            "fields": ("delivery_price", "total_price","discount_amount","coupon", "is_paid")
        }),
        ("Meta", {
            "fields": ("created_at",),
        }),
    )

    def get_queryset(self, request):
        # override if you want to prefetch items for performance
        qs = super().get_queryset(request)
        return qs.select_related("city")


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "delivery_charge")
    search_fields = ("name",)

@admin.register(UserInfo)
class UserInfoAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at")   # only show email and date
    list_filter = ("created_at",)
    search_fields = ("email",)