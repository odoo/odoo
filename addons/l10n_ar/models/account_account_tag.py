# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountAccountTag(models.Model):

    _inherit = 'account.account.tag'

    l10n_ar_jurisdiction_code = fields.Char(
        size=3,
        string="Jurisdiction Code",
    )
