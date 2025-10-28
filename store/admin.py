from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from .models import (
    Category, ProductType, Product, Size, Color,
    ProductVariant, ProductImage, ProductVariantImage
)
from .models import Coupon

# ------------------------
# Category (Tree Display)
# ------------------------
@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    mptt_level_indent = 20
    list_display = ("name", "parent", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


# ------------------------
# Product Images Inline
# ------------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


# ------------------------
# Product Variant Images Inline
# ------------------------
class ProductVariantImageInline(admin.TabularInline):
    model = ProductVariantImage
    extra = 1


# ------------------------
# Product Variant Inline
# ------------------------
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    show_change_link = True
    inlines = [ProductVariantImageInline] 
    

# ------------------------
# Product Admin
# ------------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "product_type", "is_active", "regular_price", "discount_price", "created_at")
    list_filter = ("product_type", "categories", "is_active", "created_at")
    search_fields = ("title", "description", "slug")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ProductImageInline, ProductVariantInline]


# ------------------------
# Product Variant Admin
# ------------------------
@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "size", "color", "stock", "sku")
    list_filter = ("size", "color", "product")
    search_fields = ("sku", "product__title")
    inlines = [ProductVariantImageInline]


# ------------------------
# Other Models
# ------------------------
@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'active', 'valid_from', 'valid_to', 'minimum_order_amount')
    list_filter = ('active', 'valid_from', 'valid_to')
    search_fields = ('code', 'description')
    ordering = ('-valid_from',)
    readonly_fields = ('display_validity',)

    def display_validity(self, obj):
        return f"{obj.valid_from} → {obj.valid_to}" if obj.valid_from or obj.valid_to else "No date set"
    display_validity.short_description = "Validity Period"