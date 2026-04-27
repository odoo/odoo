# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_br_is_icbs = fields.Boolean(string="Enable ICBS", help="Brazil: enable the fiscal reform.")
