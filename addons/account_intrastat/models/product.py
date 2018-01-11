# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    intrastat_id = fields.Many2one('account.intrastat.code', string='Commodity Code')

    @api.multi
    def search_intrastat_code(self):
        self.ensure_one()
        return self.intrastat_id or self.categ_id.search_intrastat_code()


class ProductCategory(models.Model):
    _inherit = "product.category"

    intrastat_id = fields.Many2one('account.intrastat.code', string='Commodity Code')

    @api.multi
    def search_intrastat_code(self):
        self.ensure_one()
        return self.intrastat_id or (self.parent_id and self.parent_id.search_intrastat_code())
