# -*- coding: utf-8 -*-

{
    'name': 'Stripe Payment Acquirer',
    'summary': 'Payment Acquirer: Stripe Implementation',
    'version': '1.0',
    'description': """
Stripe Payment Acquirer checkout webhook
========================================
    
Allow configuring a webhook in Stripe to send s2s notifications to Odoo
when a Checkout payment is completed. Note that SetupIntent and
PaymentIntent events are not listened to, since they are handled 'live'
with the customer actively present; the main use case for Stripe
webhooks is a Checkout session that gets interrupted before the customer
is redirected to Odoo (e.g. network loss, browser crash, closing the
tab, etc.).

The webhook should be configured to send its events to
<base_url>/payment/stripe/webhook and should only subscribe to
checkout.session.completed events to avoid spamming the Odoo server with
useless notifications.""",
    'depends': ['payment_stripe'],
    'data': [
        'views/payment_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'license': 'LGPL-3',
}
