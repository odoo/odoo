# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    company_country_id = fields.Many2one('res.country', related='company_id.account_fiscal_country_id', readonly=True)
    intrastat_region_id = fields.Many2one('account.intrastat.code', string='Intrastat region',
        domain="[('type', '=', 'region'), '|', ('country_id', '=', None), ('country_id', '=', company_country_id)]")
