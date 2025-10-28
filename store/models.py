
# Create your models here.
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal


class Category(MPTTModel):
    """
    Category Table implimented with MPTT.
    """

    name = models.CharField(
        verbose_name=_("Category Name"),
        help_text=_("Required and unique"),
        max_length=255,
        unique=True,
    )
    
    
    slug = models.SlugField(verbose_name=_("Category safe URL"), max_length=255, unique=True)
    parent = TreeForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    is_active = models.BooleanField(default=True)
    

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def get_absolute_url(self):
        if self.parent:
            return reverse('store:subcategory_products', args=[self.parent.slug, self.slug])
        return reverse('store:category_products', args=[self.slug])

    def __str__(self):
        return self.name
    
    
    
class ProductType(models.Model):
    """
    ProductType Table will provide a list of the different types
    of products that are for sale.
    """

    name = models.CharField(verbose_name=_("Product Name"), help_text=_("Required"), max_length=255, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Product Type")
        verbose_name_plural = _("Product Types")

    def __str__(self):
        return self.name
class Product(models.Model):
    """
    The Product table contining all product items.
    """

    product_type = models.ForeignKey(ProductType, on_delete=models.RESTRICT)
    categories = models.ManyToManyField("Category", related_name="products")
    title = models.CharField(
        verbose_name=_("title"),
        help_text=_("Required"),
        max_length=255,
    )
    description = models.TextField(verbose_name=_("description"), help_text=_("Not Required"), blank=True)
    slug = models.SlugField(max_length=255)
    regular_price = models.DecimalField(
        verbose_name=_("Regular price"),
        help_text=_("Maximum 99999.99"),
        error_messages={
            "name": {
                "max_length": _("The price must be between 0 and 99999.99."),
            },
        },
        max_digits=7,
        decimal_places=2,
    )
    discount_price = models.DecimalField(
        verbose_name=_("Discount price"),
        help_text=_("Maximum 99999.99"),
        error_messages={
            "name": {
                "max_length": _("The price must be between 0 and 99999.99."),
            },
        },
        max_digits=7,
        decimal_places=2,
    )
    is_active = models.BooleanField(
        verbose_name=_("Product visibility"),
        help_text=_("Change product visibility"),
        default=True,
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def get_absolute_url(self):
        return reverse("store:product_detail", args=[self.slug])

    def __str__(self):
        return self.title
    
class Size(models.Model):
    name = models.CharField(max_length=20, unique=True)  # e.g., S, M, L, XL

    def __str__(self):
        return self.name


class Color(models.Model):
    name = models.CharField(max_length=50, unique=True)  # e.g., Black, White, Red
      # optional color code

    def __str__(self):
        return self.name
    
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)

    class Meta:
        unique_together = ("product", "size", "color")

    def save(self, *args, **kwargs):
        # Auto-generate SKU if it is not set
        if not self.sku:
            # Use first 3 letters of product title and color, plus size
            title_part = ''.join(e for e in self.product.title if e.isalnum())[:3].upper()
            color_part = ''.join(e for e in self.color.name if e.isalnum())[:3].upper()
            self.sku = f"{title_part}-{color_part}-{self.size.name.upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.title} - {self.size.name} - {self.color.name}"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_feature = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.product.title}"
    
    
class ProductVariantImage(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/variants/')
    is_feature = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Image for {self.variant}"
    
    
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, 
        help_text="Discount percentage (e.g., 10 for 10%)"
    )
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    minimum_order_amount = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    def is_valid(self, order_total):
        now = timezone.now()
        if not self.active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        if order_total < self.minimum_order_amount:
            return False
        return True

    def get_discount_amount(self, order_total):
        """Return discount value based on percentage"""
        if self.is_valid(order_total):
            return (order_total * self.discount_percent / Decimal('100.00')).quantize(Decimal('0.01'))
        return Decimal('0.00')

    def __str__(self):
        return f"{self.code} ({self.discount_percent}%)"