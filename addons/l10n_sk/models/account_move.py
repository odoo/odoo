# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('country_code', 'invoice_date')
    def _compute_taxable_supply_date(self):
        super()._compute_taxable_supply_date()
        for move in self.filtered(lambda m: m.country_code == 'SK' and not m.taxable_supply_date):
            move.taxable_supply_date = move.invoice_date

    @api.depends('country_code')
    def _compute_show_taxable_supply_date(self):
        super()._compute_show_taxable_supply_date()
        for move in self.filtered(lambda m: m.country_code == 'SK'):
            move.show_taxable_supply_date = True

    def _generate_qr_code(self, silent_errors=False):
        """ Forward the due date to the QR-code generation.

        The PAY by square data model carries the payment due date, which the
        generic QR-code generation signature does not provide.
        """
        # EXTENDS account
        self.ensure_one()
        return super(
            AccountMove,
            self.with_context(invoice_date_due=self.invoice_date_due),
        )._generate_qr_code(silent_errors)
