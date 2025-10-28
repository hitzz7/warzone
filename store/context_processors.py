def cart_item_count(request):
    cart = request.session.get('cart', {})
    item_count = sum(cart.values())  # values are already integers
    return {'cart_item_count': item_count}
