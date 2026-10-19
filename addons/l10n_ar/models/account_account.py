# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    l10n_ar_arca_activity_id = fields.Many2one(
        'l10n_ar.arca.activity',
        string='Associated ARCA Activity',
        help="Argentina: This field is to associate a specific activity to use with this account. "
        "If not set, the company's default activity will be used."
        "The activity will be used to when generating ARCA VAT reports.",
    )
