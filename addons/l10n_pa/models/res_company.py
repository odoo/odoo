# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pa_dv = fields.Char(related='partner_id.l10n_pa_dv', readonly=False)
