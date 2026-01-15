# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    branch_code = fields.Char(string='Company Branch Code', related='partner_id.branch_code')
    l10n_ph_rdo = fields.Char(related='partner_id.l10n_ph_rdo', readonly=False)
