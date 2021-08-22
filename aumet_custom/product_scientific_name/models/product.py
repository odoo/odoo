# -*- coding: utf-8 -*-

from odoo import api, fields, models

import json


class ProductTemplate(models.Model):
    _inherit = "product.template"

    scientific_name_id = fields.Many2one("product.scientific.name", "Scientific Name")
    scientific_name_str = fields.Char(compute="_get_scientific_name_string", string="Scientific name", store="True")
    # technical field used in POS frontend
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

    @api.depends('scientific_name_id')
    def _get_scientific_name_string(self):
        for rec in self:
            name_search_string = rec.scientific_name_id.name
            rec.scientific_name_str = name_search_string
        return name_search_string
