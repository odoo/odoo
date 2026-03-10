# Copyright (C) 2022-Today - Engenere (<https://engenere.one>).
# @author Antônio S. Pereira Neto <neto@engenere.one>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import SavepointCase


class PartnerBankTest(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_bank_model = cls.env["res.partner.bank"]
        cls.partner_id = cls.env.ref("l10n_br_base.res_partner_amd")
        cls.bank_id = cls.env.ref("l10n_br_base.res_bank_001")

    def test_ok_transactional_acc_type(self):
        ok_bank_vals = {
            "partner_id": self.partner_id.id,
            "transactional_acc_type": "checking",
            "bank_id": self.bank_id.id,
            "bra_number": "1020",
            "acc_number": "102030",
            "acc_number_dig": "9",
        }
        ok_acc_bank = self.partner_bank_model.with_context(
            tracking_disable=True
        ).create(ok_bank_vals)
        self.assertTrue(ok_acc_bank.exists())

    def test_wrong_transactional_acc_type(self):
        wrong_bank_vals = {
            "partner_id": self.partner_id.id,
            "transactional_acc_type": "checking",
            "bra_number": "1020",
            "acc_number_dig": "9",
        }
        with self.assertRaises(UserError):
            self.partner_bank_model.with_context(tracking_disable=True).create(
                wrong_bank_vals
            )
