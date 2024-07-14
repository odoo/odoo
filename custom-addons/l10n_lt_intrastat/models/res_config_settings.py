# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    intrastat_region_id = fields.Many2one(
        comodel_name='account.intrastat.code',
        string="Company Intrastat Region",
        related='company_id.intrastat_region_id',
        domain="[('type', '=', 'region'), '|', ('country_id', '=', None), ('country_id', '=', account_fiscal_country_id)]",
        readonly=False,
    )
