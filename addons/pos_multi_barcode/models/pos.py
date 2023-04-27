# -*- coding: utf-8 -*-


from odoo import fields, models,tools,api
import json


class pos_multi_barcode(models.Model):
    _name = 'pos.multi.barcode'

    name = fields.Char('Barcode')
    product_id = fields.Many2one("product.product",string="Product")


class product_product(models.Model):
    _inherit = 'product.product'

    pos_multi_barcode = fields.One2many('pos.multi.barcode','product_id',string='الباركود المتعدد الأساسي')
    pos_multi_barcode_list = fields.Text(string='Barcodes',compute="_compute_multi_barcode")


    @api.depends("pos_multi_barcode")
    def _compute_multi_barcode(self):
        for record in self:
            if record.pos_multi_barcode:
                multi_uom_list = []
                for multi_uom in record.pos_multi_barcode:
                    multi_uom_list.append(multi_uom.name)
                record.pos_multi_barcode_list = json.dumps(multi_uom_list)
            else:
                record.pos_multi_barcode_list = json.dumps([])

class PosSession(models.Model):
    _inherit = 'pos.session'


    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result['search_params']['fields'].extend(['pos_multi_barcode_list'])
        return result

    