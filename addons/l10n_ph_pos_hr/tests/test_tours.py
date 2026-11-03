# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.l10n_ph_pos_hr.tests.common import L10nPhPosTestBase


@tagged("post_install_l10n", "post_install", "-at_install")
class TestLineVoidTours(L10nPhPosTestBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref("base.ph")

    def _start_tour(self, tour_name):
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour(tour_name, login="pos_admin")

    def test_line_void_flow(self):
        self._start_tour("L10nPhPosLineVoidFlow")

    def test_quantity_decrease_flow(self):
        self._start_tour("L10nPhPosQuantityDecreaseFlow")

    def test_invalid_passcode_flow(self):
        self._start_tour("L10nPhPosInvalidPasscodeFlow")

    def test_bypass_line_void_flow(self):
        self.emp3.l10n_ph_pos_allow_self_line_void = True
        self._start_tour("L10nPhPosBypassLineVoidFlow")

    def test_cancel_line_void_flow(self):
        self._start_tour("L10nPhPosCancelLineVoidFlow")

    def test_multi_digit_decrease_flow(self):
        self._start_tour("L10nPhPosMultiDigitDecreaseFlow")
