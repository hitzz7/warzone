from django.contrib.sitemaps import Sitemap
from .models import Category, Product, ProductImage
from django.urls import reverse

class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Category.objects.filter(is_active=True)

    def location(self, obj):
        return obj.get_absolute_url()

class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 1.0

    def items(self):
        return Product.objects.filter(is_active=True)

    def location(self, obj):
        return obj.get_absolute_url()

    def images(self, obj):
        """
        Include all product images in sitemap
        """
        images = []
        for img in obj.images.all():
            images.append({
                'loc': img.image.url,
                'title': obj.title,
            })
        return images
