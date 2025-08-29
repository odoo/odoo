# Copyright (C) 2021 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class FSMWizard(TransactionCase):
    """
    Test used to check that the base functionalities of Field Service Stock.
    """

    def setUp(self):
        super().setUp()
        self.Wizard = self.env["fsm.wizard"]
        self.test_partner = self.env.ref("fieldservice.test_partner")

    def test_prepare_location(self):
        self.Wizard._prepare_fsm_location(self.test_partner)
