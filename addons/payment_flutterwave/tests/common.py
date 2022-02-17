# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class FlutterwaveCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.flutterwave = cls._prepare_acquirer('flutterwave', update_values={
            'flutterwave_public_key': 'FLWPUBK_TEST-abcdef-X',
            'flutterwave_secret_key': 'FLWSECK_TEST-123456-X',
            'flutterwave_encryption_key': 'FLWSECK_TEST0123abc',
        })

        cls.acquirer = cls.flutterwave

        # cls.notification_data = {
        #
        # }
