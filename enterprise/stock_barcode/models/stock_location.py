# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class Location(models.Model):
    _inherit = 'stock.location'
    _barcode_field = 'barcode'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        domain = self.env.company.nomenclature_id._preprocess_gs1_search_args(domain, ['location', 'location_dest'])
        return super()._search(domain, offset=offset, limit=limit, order=order)

    @api.model
    def _get_fields_stock_barcode(self):
        return ['barcode', 'display_name', 'name', 'parent_path', 'usage']

    def get_counted_quant_data_records(self):
        self.ensure_one()
        return self.quant_ids.get_stock_barcode_data_records()
