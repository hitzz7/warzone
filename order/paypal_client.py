# # store/paypal_client.py
# import paypalcheckoutsdk.core as paypalcore
# import paypalcheckoutsdk.orders as paypalorders

# from django.conf import settings

# class PayPalClient:
#     def __init__(self):
#         self.client_id = settings.PAYPAL_CLIENT_ID
#         self.client_secret = settings.PAYPAL_SECRET
#         self.environment = paypalcore.SandboxEnvironment(
#             client_id=self.client_id,
#             client_secret=self.client_secret
#         )
#         self.client = paypalcore.PayPalHttpClient(self.environment)
