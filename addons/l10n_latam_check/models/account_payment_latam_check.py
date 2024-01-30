import stdnum

from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date


class AccountPaymentLatamCheck(models.Model):
    _name = 'account.payment.latam.check'
    _description = 'latam check'
    _check_company_auto = True

    payment_id = fields.Many2one(
        comodel_name='account.payment',
    )
    l10n_latam_check_number = fields.Char(
    )
    # New third party check info
    l10n_latam_check_bank_id = fields.Many2one(
        comodel_name='res.bank',
        string='Check Bank',
        # compute='_compute_l10n_latam_check_bank_id', store=True, readonly=False,
    )
    l10n_latam_check_issuer_vat = fields.Char(
        string='Check Issuer VAT',
        # compute='_compute_l10n_latam_check_issuer_vat', store=True, readonly=False,
    )
    l10n_latam_check_payment_date = fields.Date(
        string='Check Cash-In Date',
        help="Date from when you can cash in the check, turn the check into cash",
        readonly=False,
    )
    currency_id = fields.Many2one(related="payment_id.currency_id")
    amount = fields.Monetary()
