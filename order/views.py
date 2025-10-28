# store/views.py
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.urls import reverse

from .models import Order, OrderItem, City,UserInfo
from store.models import ProductVariant,Coupon
from django.http import JsonResponse
from .forms import CheckoutForm
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

# from .paypal_client import PayPalClient
# import paypalcheckoutsdk.orders as paypalorders


def get_absolute_url(request, path):
    """Return absolute URL. If request provided, use build_absolute_uri, otherwise use SITE_URL."""
    if request:
        return request.build_absolute_uri(path)
    site = getattr(settings, "SITE_URL", None) or ""
    return site.rstrip("/") + path

def send_order_confirmation_email(order, request=None):
    """
    Sends a multipart (text + HTML) order confirmation email.
    - `order` is an Order instance with related OrderItem objects at order.items.all()
    - `request` is optional and used to build absolute URLs for links/images.
    """
    # Build helpful context
    order_lookup_path = reverse("order:order_lookup")  # change to your named url if different
    order_lookup_url = get_absolute_url(request, order_lookup_path)
    
    for it in order.items.all():
        image_url = ""
        if getattr(it, "image_url", None):  # make sure it has image_url field or property
            if request:
                image_url = request.build_absolute_uri(it.image_url)
            else:
                site_url = getattr(settings, "SITE_URL", "https://tsabinz.com")
                image_url = site_url.rstrip("/") + it.image_url
        it.image_url_absolute = image_url

    # If you want a direct order-specific link, use something like:
    # order_detail_path = reverse("store:order_detail_lookup", args=[order.id])
    # order_lookup_url = get_absolute_url(request, order_detail_path)
    subtotal = sum(item.price * item.quantity for item in order.items.all())

    context = {
        "order": order,
        "support_email": getattr(settings, "SUPPORT_EMAIL", getattr(settings, "DEFAULT_FROM_EMAIL", "tsabinzofficial@gmail.com")),
        "order_lookup_url": order_lookup_url,
        "subtotal": subtotal,
        # logo or site images must be absolute URLs
        "site_logo_url": get_absolute_url(request, settings.STATIC_URL + "tsabinlogo-.png") if getattr(settings, "STATIC_URL", None) else None,
    }

    subject = f"Order confirmation — Order #{order.id}"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
    to = [order.email, "tsabinzofficial@gmail.com"] if order.email else []

    # Render templates
    text_body = render_to_string("Warzone/order_confirmation.txt", context)
    html_body = render_to_string("Warzone/order_confirmation.html", context)

    # Create email message
    msg = EmailMultiAlternatives(subject, text_body, from_email, to)
    msg.attach_alternative(html_body, "text/html")

    # Optional: attach files or inline images (advanced) — omitted for now
    # Example to send:
    msg.send(fail_silently=False)
    
def _get_cart_items_from_session(request):
    """
    Returns list of dict items: [{'variant': ProductVariant, 'qty': int, 'product': Product, 'price': Decimal, 'line_total': Decimal}, ...]
    Assumes session['cart'] is { variant_id: qty, ... } (keys might be str or int).
    """
    cart = request.session.get('cart', {}) or {}
    # normalize ids
    ids = []
    for k in cart.keys():
        try:
            ids.append(int(k))
        except (TypeError, ValueError):
            continue
    variants = ProductVariant.objects.filter(id__in=ids).select_related('product', 'size', 'color')
    variant_map = {v.id: v for v in variants}
    items = []
    subtotal = Decimal('0.00')
    for vid_str, qty in cart.items():
        try:
            vid = int(vid_str)
        except (TypeError, ValueError):
            continue
        if vid not in variant_map:
            continue
        v = variant_map[vid]
        # price pulled from product (use discount if present)
        product = v.product
        price = product.discount_price if getattr(product, 'discount_price', None) not in (None, '') else product.regular_price
        qty_int = int(qty) if qty else 1
        line_total = (price or Decimal('0.00')) * qty_int
        subtotal += line_total
        items.append({
            'variant': v,
            'product': product,
            'qty': qty_int,
            'price': price,
            'line_total': line_total,
        })
    return items, subtotal

@transaction.atomic
def create_order_from_cart(request, form_cleaned_data):
    """
    Create Order + OrderItems from session cart.
    form_cleaned_data is cleaned_data from CheckoutForm.
    Returns created Order instance.
    """
    items, subtotal = _get_cart_items_from_session(request)
    if not items:
        raise ValueError("Cart is empty")

    # City and delivery
    city = form_cleaned_data.get('city')
    delivery_price = city.delivery_charge if city else Decimal('0.00')
    
    # Coupon
    coupon_code = request.POST.get('applied_coupon', '').strip()
    
    discount = Decimal('0.00')
    coupon = None
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code__iexact=coupon_code)
            if coupon.is_valid(subtotal):
                discount = (subtotal * coupon.discount_percent / Decimal('100')).quantize(Decimal('0.01'))
            else:
                coupon = None  # invalid due to date or inactive
        except Coupon.DoesNotExist:
            coupon = None
   
    # Create Order
    order = Order.objects.create(
        name=form_cleaned_data.get('name'),
        email=form_cleaned_data.get('email'),
        phone=form_cleaned_data.get('phone'),
        address=form_cleaned_data.get('address'),
        city=city,
        landmark=form_cleaned_data.get('landmark') or '',
        delivery_price=delivery_price,
        total_price=Decimal('0.00'),
        coupon=coupon,
        discount_amount=discount,# will update below
    )
    
    name = form_cleaned_data.get('name')
    email = form_cleaned_data.get('email')
    phone = form_cleaned_data.get('phone')
    address = form_cleaned_data.get('address')

    user_exists = UserInfo.objects.filter(name=name, email=email).exists()
    if not user_exists:
        UserInfo.objects.create(
            name=name,
            email=email,
            phone=phone,
            address=address,
        )
          
    # create items
    for it in items:
        v = it['variant']
        p = it['product']
        price = it['price'] or Decimal('0.00')
        qty = it['qty']
        OrderItem.objects.create(
            order=order,
            product=p,
            variant=v,
            title=p.title,
            price=price,
            sku=getattr(v, 'sku', '') or None,
            size=getattr(v.size, 'name', '') if getattr(v, 'size', None) else None,
            color=getattr(v.color, 'name', '') if getattr(v, 'color', None) else None,
            quantity=qty,
            image_url=p.images.first().image.url if p.images.exists() else '',
        )
        
        if v and hasattr(v, 'stock'):
            v.stock = max(v.stock - qty, 0)  # prevent negative stock
        v.save()

    # finalize totals
    total = subtotal + delivery_price - discount
    order.total_price = max(total, Decimal('0.00'))  # prevent negative
    order.save()


    # clear cart
    request.session.pop('cart', None)
    request.session.modified = True

    return order

def get_delivery_charge(request):
    city_id = request.GET.get("city_id")
    if city_id:
        try:
            city = City.objects.get(id=city_id)
            return JsonResponse({"delivery_charge": city.delivery_charge})
        except City.DoesNotExist:
            pass
    return JsonResponse({"delivery_charge": 0})

# def create_paypal_order(request, order_id):
#     """Create PayPal order and return approval URL"""
#     order_obj = Order.objects.get(id=order_id)  # your order
#     total_amount = f"{order_obj.total_price:.2f}"  # as string

#     client = PayPalClient()

#     request_order = paypalorders.OrdersCreateRequest()
#     request_order.prefer('return=representation')
#     request_order.request_body({
#         "intent": "CAPTURE",
#         "purchase_units": [
#             {
#                 "amount": {
#                     "currency_code": "USD",
#                     "value": total_amount
#                 },
#                 "invoice_id": str(order_obj.id),
#                 "description": "Purchase from Hitzz"
#             }
#         ],
#         "application_context": {
#             "return_url": request.build_absolute_uri(f"/paypal-success/{order_obj.id}/"),
#             "cancel_url": request.build_absolute_uri(f"/checkout/")
#         }
#     })

#     response = client.client.execute(request_order)
#     for link in response.result.links:
#         if link.rel == "approve":
#             approval_url = link.href
#             return JsonResponse({"approval_url": approval_url})

#     return JsonResponse({"error": "Unable to create PayPal order"}, status=400)

# def capture_paypal_order(request, order_id):
#     client = PayPalClient()
#     paypal_order_id = request.GET.get('token')  # PayPal sends token in return URL

#     request_capture = paypalorders.OrdersCaptureRequest(paypal_order_id)
#     request_capture.request_body({})

#     response = client.client.execute(request_capture)

#     if response.result.status == "COMPLETED":
#         # Mark order as paid
#         order = Order.objects.get(id=order_id)
#         order.status = "paid"
#         order.save()
#         return redirect('order:order_success', order_id=order.id)
#     else:
#         return redirect('checkout')


def checkout(request):
    # show checkout form and cart summary
    items, subtotal = _get_cart_items_from_session(request)
    if not items:
        messages.info(request, "Your cart is empty.")
        return redirect('store:product_list')  # change to your product listing url

    if request.method == 'POST':
        print("POST data:", request.POST)
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                # Create order from cart
                order = create_order_from_cart(request, form.cleaned_data)

                # Compute subtotal from order items (ensures DB is accurate)
                subtotal = sum(it.price * it.quantity for it in order.items.all())

            except ValueError as e:
                messages.error(request, str(e))
                return redirect('store:cart')  # or product list

            # ✅ Send confirmation email with HTML + text
            try:
                send_order_confirmation_email(order, request=request)
            except Exception as e:
                # In production: log error
                print(f"Error sending confirmation email: {e}")

            # Redirect to success page
            return redirect(reverse('order:order_success', args=[order.id]))
    else:
        form = CheckoutForm()

    context = {
        'form': form,
        'items': items,
        'subtotal': subtotal,
        'delivery_estimate': None,
    }
    return render(request, 'Warzone/checkout.html', context)



def order_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    subtotal = sum(it.price * it.quantity for it in order.items.all())
    
    return render(request, 'Warzone/success.html', {'order': order,'subtotal': subtotal})

def order_lookup(request):
    """
    Let customers enter Order ID and email to look up an order (no login required).
    """
    order = None
    msg = ''
    if request.method == 'POST':
        oid = request.POST.get('order_id')
        email = request.POST.get('email')
        if not oid or not email:
            msg = "Please provide both Order ID and email."
        else:
            try:
                order = Order.objects.get(pk=oid)
                if order.email.lower().strip() != email.lower().strip():
                    order = None
                    msg = "Order ID found but email does not match."
            except Order.DoesNotExist:
                msg = "No order found with that Order ID."
    return render(request, 'Warzone/order_lookup.html', {'order': order, 'message': msg})



def save_email(request):
    if request.method == "POST":
        email = request.POST.get("email")
        if email:
            if not UserInfo.objects.filter(email=email).exists():
                UserInfo.objects.create(email=email)
                return JsonResponse({"status": "success", "message": "Email saved!"})
            else:
                return JsonResponse({"status": "exists", "message": "Email already saved!"})
    return JsonResponse({"status": "error", "message": "Invalid request."}, status=400)