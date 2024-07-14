# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    barcode_nomenclature_id = fields.Many2one('barcode.nomenclature', related='company_id.nomenclature_id', readonly=False)
    stock_barcode_demo_active = fields.Boolean("Demo Data Active", compute='_compute_stock_barcode_demo_active')
    show_barcode_nomenclature = fields.Boolean(compute='_compute_show_barcode_nomenclature')

    @api.depends('company_id')
    def _compute_show_barcode_nomenclature(self):
        self.show_barcode_nomenclature = self.module_stock_barcode and self.env['barcode.nomenclature'].search_count([]) > 1

    @api.depends('company_id')
    def _compute_stock_barcode_demo_active(self):
        for rec in self:
            rec.stock_barcode_demo_active = bool(self.env['ir.module.module'].search([('name', '=', 'stock_barcode'), ('demo', '=', True)]))
