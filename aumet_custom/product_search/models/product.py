# -*- coding: utf-8 -*-

from odoo import api, fields, models

import json


class ProductTemplate(models.Model):
    _inherit = "product.template"

    active_ingredient_str = fields.Char(compute="_get_active_ingredient_string", string="Scientific name", store="True")
    supplier_data_json = fields.Char(
        "Supplier data dict", readonly=True,
        compute="_compute_supplier_data_json")

    # @api.multi
    def _compute_supplier_data_json(self):
        for t in self:
            res = []
            for s in t.seller_ids:
                res.append({
                    'supplier_name': s.name.display_name,
                })
            t.supplier_data_json = json.dumps(res)

    @api.depends('active_ingredient_ids')
    def _get_active_ingredient_string(self):
        for rec in self:
            name_search_string = rec.active_ingredient_ids.name
            rec.active_ingredient_str = name_search_string
        return name_search_string
