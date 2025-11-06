# from django.shortcuts import render
# from .models import Category,Project,ProjectImage,Product,ProductImage
# from django.shortcuts import render, get_object_or_404
# from django.shortcuts import render, redirect
# from .forms import ContactForm
# from django.core.mail import send_mail
# from django.conf import settings


# def product(request):
#     categories = Category.objects.all()
#     products = Product.objects.all()
#     return render(request, 'Warzone/product.html', {'categories': categories,'products': products},)



# def product_list(request, category_id):
#     category = get_object_or_404(Category, pk=category_id)
#     products = category.products.all()  # Uses the related_name 'projects'
#     return render(request, 'Warzone/category_detail.html', {'category': category, 'products': products})

# def product_detail(request, product_id):
#     product = get_object_or_404(Product, pk=product_id)
#     images = product.images.all()  # Uses the related_name 'images'
#     return render(request, 'Warzone/productdetail.html', {'product': product, 'images': images})


from django.shortcuts import render, get_object_or_404
from .models import Product, Category,Size,Color

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET    
from decimal import Decimal

from .models import ProductVariant, Product,ProductType
from django.db.models import Q

from django.utils import timezone
from .models import Coupon
from django.db.models import Sum



def base_context(request):
    # Get all top-level categories
    top_categories = Category.objects.filter(parent__isnull=True, is_active=True)
    men = get_object_or_404(Category, slug='men', is_active=True)
    men_children = men.get_children().filter(is_active=True)
    
    return {
        "top_categories": top_categories,
        'men_children': men_children,
    }
    
def home(request):
    
    products = Product.objects.all()
    
    return render(request,'Warzone/home.html',{'products':products});


def product_list(request, category_slug=None, parent_slug=None):
    category = None
    products = Product.objects.filter(is_active=True)
    subcategories = None
    sizes = Size.objects.all()
    colors = Color.objects.all()
    size = request.GET.get("size")
    color = request.GET.get("color")
    sort = request.GET.get('sort')
    product_type_param = request.GET.get("product_type")
    product_types = ProductType.objects.all() # get all types

    if category_slug and category_slug != "all":
        if parent_slug:
            parent = get_object_or_404(Category, slug=parent_slug, is_active=True)
            category = get_object_or_404(Category, slug=category_slug, parent=parent, is_active=True)
        else:
            category = get_object_or_404(Category, slug=category_slug, is_active=True)

        # Direct children (subcategories)
        subcategories = category.get_children()

        # All products within this category + descendants
        descendant_categories = category.get_descendants(include_self=True)
        products = products.filter(categories__in=descendant_categories).distinct()

    if size:
        products = products.filter(variants__size__name=size).distinct()

    if color:
        products = products.filter(variants__color__name=color).distinct()
        
    product_type_name = None
    if product_type_param:
        try:
            product_type_obj = ProductType.objects.get(name__iexact=product_type_param)
            products = products.filter(product_type=product_type_obj)
            product_type_name = product_type_obj.name  # For display in template
        except ProductType.DoesNotExist:
            pass 


    if sort == "price_low_high":
        products = products.order_by("discount_price")
    elif sort == "price_high_low":
        products = products.order_by("-discount_price")
    elif sort == "newest":
        products = products.order_by("-created_at")
    elif sort == "best_selling":
        products = products.annotate(total_sold=Sum("orderitem__quantity")).order_by("-total_sold", "-created_at")

    context = {
        "category": category,
        "subcategories": subcategories,
        "products": products,
        "sizes": sizes,
        "colors": colors,
        "product_types": product_types,
        "product_type_name": product_type_name,
    }
    return render(request, "Warzone/product.html", context)



def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    variants = product.variants.all()
    images = product.images.all()
    
    categories = product.categories.all()
    

    # ✅ Fetch related products from this category + its children
    category_ids = []
    for cat in categories:
        category_ids += cat.get_descendants(include_self=True).values_list('id', flat=True)

    # Fetch related products from these categories
    related_products = (
        Product.objects.filter(categories__in=category_ids)
        .exclude(id=product.id)
        .distinct()[:4]
    )
    colors = product.variants.values("color__id", "color__name").distinct()
    sizes = product.variants.values("size__id", "size__name").distinct()
    
    return render(request, "Warzone/productdetail.html", {
        "product": product,
        "variants": variants,
        "images": images,
        "colors": colors,
        "sizes": sizes,
        'related_products': related_products,
    })



def _get_cart(request):
    return request.session.get("cart", {})

def _save_cart(request, cart):
    request.session["cart"] = cart
    request.session.modified = True
    
def cart_item_count(request):
    cart = request.session.get('cart', {})
    item_count = sum(cart.values())
    return {'cart_item_count': item_count}


def _cart_response_data(request):
    """
    Return structured cart data for JSON response:
    {
      items: [{ variant_id, product_slug, title, image, size, color, qty, price, total_price }],
      subtotal, total_items
    }
    """
    cart = _get_cart(request)
    items = []
    subtotal = Decimal("0.00")
    total_items = 0

    variant_ids = [int(k) for k in cart.keys()] if cart else []
    variants = ProductVariant.objects.filter(id__in=variant_ids).select_related('product', 'size', 'color')

    variant_map = {v.id: v for v in variants}
    for vid_str, qty in cart.items():
        try:
            vid = int(vid_str)
        except ValueError:
            continue
        variant = variant_map.get(vid)
        if not variant:
            continue
        product = variant.product
        # choose displayed price: discount if available else regular
        price = product.discount_price if product.discount_price is not None else product.regular_price
        line_total = (price or Decimal("0.00")) * int(qty)
        subtotal += line_total
        total_items += int(qty)

        # image url if exists (first image)
        image_url = None
        first_img = product.images.first()
        if first_img:
            image_url = first_img.image.url

        items.append({
            "variant_id": variant.id,
            "product_slug": product.slug,
            "title": product.title,
            "image": image_url,
            "size": variant.size.name if variant.size else None,
            "color": variant.color.name if variant.color else None,
            "qty": int(qty),
            "price": f"{price:.2f}",
            "line_total": f"{line_total:.2f}",
        })

    return {
        "items": items,
        "subtotal": f"{subtotal:.2f}",
        "total_items": total_items,
    }

# GET cart JSON (used to render drawer)
# @require_GET
def cart_json(request):
    data = _cart_response_data(request)
    return JsonResponse(data)


@require_POST
def cart_add(request):
    """
    POST: variant_id, quantity (optional)
    Adds qty to existing quantity (increment).
    """
    variant_id = request.POST.get("variant_id")
    qty = int(request.POST.get("quantity", 1))
    if not variant_id:
        return JsonResponse({"error": "variant_id required"}, status=400)

    variant = get_object_or_404(ProductVariant, pk=variant_id)

    cart = _get_cart(request)
    cart_str = {k: v for k, v in cart.items()}  # just ensure dict
    current = int(cart_str.get(str(variant.id), 0))
    cart_str[str(variant.id)] = current + qty
    _save_cart(request, cart_str)
    return JsonResponse(_cart_response_data(request))


@require_POST
def cart_update(request):
    """
    POST: variant_id, quantity -> sets the quantity (if zero removes)
    """
    variant_id = request.POST.get("variant_id")
    try:
        qty = int(request.POST.get("quantity", 0))
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid quantity"}, status=400)

    if not variant_id:
        return JsonResponse({"error": "variant_id required"}, status=400)

    # ensure variant exists
    get_object_or_404(ProductVariant, pk=variant_id)

    cart = _get_cart(request)
    if qty > 0:
        cart[str(variant_id)] = qty
    else:
        # remove if zero
        cart.pop(str(variant_id), None)
    _save_cart(request, cart)
    return JsonResponse(_cart_response_data(request))


@require_POST
def cart_remove(request):
    """
    POST: variant_id -> removes it from cart
    """
    variant_id = request.POST.get("variant_id")
    if not variant_id:
        return JsonResponse({"error": "variant_id required"}, status=400)

    cart = _get_cart(request)
    cart.pop(str(variant_id), None)
    _save_cart(request, cart)
    return JsonResponse(_cart_response_data(request))


def apply_coupon(request):
    code = request.GET.get("code", "").strip()
    subtotal = Decimal(request.GET.get("subtotal", "0"))

    try:
        coupon = Coupon.objects.get(code__iexact=code)
        
        # ✅ Pass subtotal (order_total) into is_valid()
        if not coupon.is_valid(subtotal):
            return JsonResponse({"valid": False, "message": "Coupon expired, inactive, or minimum not met."})

        discount = (subtotal * coupon.discount_percent / Decimal("100")).quantize(Decimal("0.01"))

        return JsonResponse({
            "valid": True,
            "discount": float(discount),
            "discount_percent": float(coupon.discount_percent),
        })

    except Coupon.DoesNotExist:
        return JsonResponse({"valid": False, "message": "Coupon not found."})
    
    
def search_json(request):
    query = request.GET.get("q", "").strip()
    items = []

    if query:
        products = Product.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        ).distinct()[:10]  # limit to 10 results

        for product in products:
            first_image = product.images.first()
            items.append({
                "title": product.title,
                "url": product.get_absolute_url(),  # make sure your Product model has this
                "image": first_image.image.url if first_image else "",
                "price": f"{product.discount_price if product.discount_price else product.regular_price:.2f}",
            })

    return JsonResponse({"items": items})