# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_pe_group_id = fields.Many2one("account.group", related="account_id.group_id", store=True)
