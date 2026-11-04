# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def _edi_is_factoring_bank(self):
        """Hook for localization modules. Factoring columns are not stored here."""
        self.ensure_one()
        return False

    def _get_edi_payee_partner(self):
        """BG-10 payee. Empty unless a localization flags this bank account as factoring."""
        self.ensure_one()
        return self.env['res.partner']

    def _get_edi_payee_account_holder_name(self):
        """BT-85 holder name exported with the payee. Empty unless factoring."""
        self.ensure_one()
        return False

    def _get_edi_payee_role_code(self):
        self.ensure_one()
        return False

    def _edi_get_payment_note(self):
        self.ensure_one()
        return False
