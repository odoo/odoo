# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    # ----------------
    # Business methods
    # ----------------

    @api.model
    def _get_payment_method_information(self):
        # EXTENDS account
        res = super()._get_payment_method_information()
        for payment_method in ('l10n_nz_eft_in', 'l10n_nz_eft_out'):
            res[payment_method] = {
                'mode': 'multi',
                'domain': [('type', '=', 'bank')],
                'currency_ids': self.env.ref("base.NZD").ids,
            }
        return res


class AccountPaymentMethodLine(models.Model):
    _inherit = 'account.payment.method.line'

    # ------------------
    # Fields declaration
    # ------------------

    # Adding it here in order to leave as much freedom as possible to the user.
    # Possible to add multiple methods depending on what is wanted.
    l10n_nz_payment_listing_indicator = fields.Selection(
        selection=[
            ('C', 'C'),
            ('I', 'I'),
            ('O', 'O'),
        ],
        string='Payment Listing Indicator',
        help="Bulk Listing = combine all transactions contained in the file and show as one transaction on the payer’s bank statement.\n"
             "C = Individual listing, details copied from other party.\n"
             "I = Individual listing, payer’s and other party’s details entered individually.\n"
             "O = Individual listing, payer’s details all the same."
    )
