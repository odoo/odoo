from odoo import models, fields


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.avatax.unique.code', 'account.move']

    avatax_tax_date = fields.Date(
        string="Avatax Date",
        help="Avatax will use this date to calculate the tax on this invoice. "
             "If not specified it will use the Invoice Date.",
    )

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        self.filtered(
            lambda move: move.is_avatax and move.move_type in ('out_invoice', 'out_refund') and not move._is_downpayment()
        )._commit_avatax_taxes()
        return res

    def _get_avatax_dates(self):
        external_tax_date = self._get_date_for_external_taxes()
        if self.reversed_entry_id:
            reversed_override_date = self.reversed_entry_id.avatax_tax_date or self.reversed_entry_id._get_date_for_external_taxes()
            return external_tax_date, reversed_override_date
        return external_tax_date, self.avatax_tax_date

    def _get_avatax_document_type(self):
        return {
            'out_invoice': 'SalesInvoice',
            'out_refund': 'ReturnInvoice',
            'in_invoice': 'PurchaseInvoice',
            'in_refund': 'ReturnInvoice',
            'entry': 'Any',
        }[self.move_type]

    def _get_avatax_description(self):
        return 'Journal Entry'

    def _perform_address_validation(self):
        # Payments inherit account.move and will end up with a fiscal position.
        # Even if an auto-applied Avatax fiscal position is set don't validate the address.
        moves = self.filtered(lambda m: m.move_type in ('out_invoice', 'out_refund'))
        return super(AccountMove, moves)._perform_address_validation() and not moves.origin_payment_id
