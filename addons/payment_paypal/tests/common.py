# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class PaypalCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.paypal = cls._prepare_provider(
            "paypal",
            update_values={
                "paypal_email_account": "dummy@test.mail.com",
                "paypal_client_id": "dummy_client_id",
                "paypal_client_secret": "dummy_secret",
            },
        )

        # Override default values
        cls.provider = cls.paypal
        cls.currency = cls.currency_euro
        cls.order_id = "123DUMMY456"

        cls.payment_data = {
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "resource": {
                "id": cls.order_id,
                "intent": "CAPTURE",
                "status": "COMPLETED",
                "payment_source": {"paypal": {"account_id": "59XDVNACRAZZJ"}},
                "purchase_units": [
                    {
                        "amount": {"currency_code": cls.currency.name, "value": str(cls.amount)},
                        "reference_id": cls.reference,
                    }
                ],
            },
        }

        cls.completed_order = {
            "status": "COMPLETED",
            "payment_source": {"paypal": {"account_id": "59XDVNACRAZZJ"}},
            "purchase_units": [
                {
                    "reference_id": cls.reference,
                    "payments": {
                        "captures": [
                            {
                                "amount": {
                                    "currency_code": cls.currency.name,
                                    "value": str(cls.amount),
                                },
                                "status": "COMPLETED",
                                "id": cls.order_id,
                            }
                        ]
                    },
                }
            ],
        }

        # The `payer-action` URL the customer is redirected to for alternative payment methods.
        cls.payer_action_url = (
            f"https://www.sandbox.paypal.com/payment/bancontact?token={cls.order_id}"
        )
        cls.apm_order_data = {
            "id": cls.order_id,
            "status": "PAYER_ACTION_REQUIRED",
            "links": [
                {
                    "href": f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{cls.order_id}",
                    "rel": "self",
                    "method": "GET",
                },
                {"href": cls.payer_action_url, "rel": "payer-action", "method": "GET"},
            ],
        }

        cls.capture_notification = {
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {
                "id": "8SS60826HT082593F",
                "status": "COMPLETED",
                "custom_id": cls.reference,
                "amount": {"currency_code": cls.currency.name, "value": str(cls.amount)},
                "supplementary_data": {"related_ids": {"order_id": cls.order_id}},
            },
        }

        cls.declined_notification = {
            "event_type": "CHECKOUT.ORDER.DECLINED",
            "resource": {
                "id": cls.order_id,
                "intent": "CAPTURE",
                "status": "PAYER_ACTION_REQUIRED",
                "payment_source": {"bancontact": {"name": "John Doe", "country_code": "BE"}},
                "purchase_units": [
                    {
                        "reference_id": cls.reference,
                        "amount": {"currency_code": cls.currency.name, "value": str(cls.amount)},
                        "most_recent_errors": [
                            {
                                "issue": "PAYMENT_SOURCE_CANNOT_BE_USED",
                                "description": "The provided payment source cannot be used.",
                            }
                        ],
                    }
                ],
            },
        }
