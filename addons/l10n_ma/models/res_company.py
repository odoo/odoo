# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ma_ice = fields.Char(related='partner_id.l10n_ma_ice', readonly=False)
