from odoo import Command
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.pos_bancontact_pay.tests.test_frontend import (
    TestFrontend,
    error_checker_bancontact_failed_rpc_request,
)


@tagged("post_install", "-at_install")
class TestKioskFrontend(TestFrontend):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.bancontact_kiosk = cls.env['pos.config'].create({
            'name': 'Bancontact Kiosk',
            'currency_id': cls.eur_currency.id,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'payment_method_ids': [Command.clear(), Command.link(cls.payment_method_display.id)],
            'self_ordering_available_language_ids': [Command.link(lang.id) for lang in cls.env['res.lang'].search([])],
        })

    def start_kiosk_tour(self, tour_name, **kwargs):
        self.bancontact_kiosk.with_user(self.pos_admin).open_ui()
        self.bancontact_kiosk.current_session_id.set_opening_control(0, "")
        self_route = self.bancontact_kiosk._get_self_order_route()
        self.start_tour(self_route, tour_name, **kwargs)

    def test_kiosk_bancontact_pay_success(self):
        with self.mock_bancontact_call(prefix="kiosk_bancontact_success_"):
            self.start_kiosk_tour("kiosk_bancontact_pay_success")

    def test_kiosk_bancontact_pay_failed(self):
        with self.mock_bancontact_call(prefix="kiosk_bancontact_failed_"):
            self.start_kiosk_tour("kiosk_bancontact_pay_failed")

    @mute_logger("odoo.http")
    def test_kiosk_bancontact_pay_failed_create_payment(self):
        with self.mock_bancontact_call(post_status_code=401):
            self.start_kiosk_tour("kiosk_bancontact_pay_failed_create_payment", error_checker=error_checker_bancontact_failed_rpc_request)
