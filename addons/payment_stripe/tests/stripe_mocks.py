checkout_session_signature = 't=1591264652,v1=1f0d3e035d8de956396b1d91727267fbbf483253e7702e46357b4d2bfa078ba4,v0=20d76342f4704d49f8f89db03acff7cf04afa48ca70a22d608b4649b332c1f51'
checkout_session_body = b'{\n  "id": "evt_1GqFpHAlCFm536g8NYSLoccF",\n  "object": "event",\n  "api_version": "2019-05-16",\n  "created": 1591264651,\n  "data": {\n    "object": {\n      "id": "cs_test_SI8yz61JCZ4gxd7Z5oGfQSn9ZbubC6SZF3bJTxvy2PVqSd3dzbDV1kyd",\n      "object": "checkout.session",\n      "billing_address_collection": null,\n      "cancel_url": "https://httpbin.org/post",\n      "client_reference_id": null,\n      "customer": "cus_HP3xLqXMIwBfTg",\n      "customer_email": null,\n      "display_items": [\n        {\n          "amount": 1500,\n          "currency": "usd",\n          "custom": {\n            "description": "comfortable cotton t-shirt",\n            "images": null,\n            "name": "t-shirt"\n          },\n          "quantity": 2,\n          "type": "custom"\n        }\n      ],\n      "livemode": false,\n      "locale": null,\n      "metadata": {\n      },\n      "mode": "payment",\n      "payment_intent": "pi_1GqFpCAlCFm536g8HsBSvSEt",\n      "payment_method_types": [\n        "card"\n      ],\n      "setup_intent": null,\n      "shipping": null,\n      "shipping_address_collection": null,\n      "submit_type": null,\n      "subscription": null,\n      "success_url": "https://httpbin.org/post"\n    }\n  },\n  "livemode": false,\n  "pending_webhooks": 2,\n  "request": {\n    "id": null,\n    "idempotency_key": null\n  },\n  "type": "checkout.session.completed"\n}'

checkout_session_object = {'billing_address_collection': None,
                           'cancel_url': 'https://httpbin.org/post',
                           'client_reference_id': "tx_ref_test_handle_checkout_webhook",
                           'customer': 'cus_HOgyjnjdgY6pmY',
                           'customer_email': None,
                           'display_items': [{'amount': 1500,
                                              'currency': 'usd',
                                              'custom': {'description': 'comfortable '
                                                                        'cotton '
                                                                        't-shirt',
                                                         'images': None,
                                                         'name': 't-shirt'},
                                              'quantity': 2,
                                              'type': 'custom'}],
                           'id': 'cs_test_sbTG0yGwTszAqFUP8Ulecr1bUwEyQEo29M8taYvdP7UA6Qr37qX6uA6w',
                           'livemode': False,
                           'locale': None,
                           'metadata': {},
                           'mode': 'payment',
                           'object': 'checkout.session',
                           'payment_intent': 'pi_1GptaRAlCFm536g8AfCF6Zi0',
                           'payment_method_types': ['card'],
                           'setup_intent': None,
                           'shipping': None,
                           'shipping_address_collection': None,
                           'submit_type': None,
                           'subscription': None,
                           'success_url': 'https://httpbin.org/post'}
