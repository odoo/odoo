from requests import Response
from unittest.mock import patch
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests.common import tagged

@tagged('post_install', '-at_install')
class TestAdyenPoS(TestPointOfSaleHttpCommon):
    def _setup_adyen_config(self):
        self.main_pos_config.write({
            "payment_method_ids": [
                (0, 0, {
                    "name": "Adyen",
                    "use_payment_terminal": True,
                    "adyen_api_key": "my_adyen_api_key",
                    "adyen_terminal_identifier": "my_adyen_terminal",
                    "adyen_test_mode": False,
                    "use_payment_terminal": "adyen",
                    "payment_method_type": "terminal",
                    'journal_id': self.bank_journal.id,
                }),
            ],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()

    def test_adyen_basic_order(self):
        self._setup_adyen_config()

        def post(url, **kwargs):
            # TODO: check that the data passed by pos to adyen is correct
            response = Response()
            response.status_code = 200
            response._content = "ok".encode()
            return response

        with patch('odoo.addons.pos_adyen.models.pos_payment_method.requests.post', post), \
             patch('odoo.addons.pos_adyen.controllers.main.consteq', lambda a,b: True):
            self.start_pos_tour('PosAdyenTour')

    def test_adyen_cancel_rejected_by_terminal(self):
        # The terminal refuses the Abort request: the payment line must not
        # be dropped/retried, since Adyen can still send a Success
        # notification for it afterwards.
        self._setup_adyen_config()

        def post(url, **kwargs):
            response = Response()
            response.status_code = 200
            header = kwargs['json']['SaleToPOIRequest']['MessageHeader']
            response._content = b'{}' if header['MessageCategory'] == 'Abort' else b'ok'
            return response

        with patch('odoo.addons.pos_adyen.models.pos_payment_method.requests.post', post), \
             patch('odoo.addons.pos_adyen.controllers.main.consteq', lambda a,b: True):
            self.start_pos_tour('PosAdyenCancelFailTour')

    def test_adyen_orphaned_notification_is_reported(self):
        # A Success notification that arrives once the payment line was
        # deleted must not be silently dropped.
        self._setup_adyen_config()

        def post(url, **kwargs):
            response = Response()
            response.status_code = 200
            response._content = "ok".encode()
            return response

        with patch('odoo.addons.pos_adyen.models.pos_payment_method.requests.post', post), \
             patch('odoo.addons.pos_adyen.controllers.main.consteq', lambda a,b: True):
            self.start_pos_tour('PosAdyenOrphanNotificationTour')
