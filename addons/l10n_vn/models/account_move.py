# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons import account


class AccountMove(account.AccountMove):

    l10n_vn_e_invoice_number = fields.Char(
        string='eInvoice Number',
        help='Electronic Invoicing number.',
        copy=False,
    )
