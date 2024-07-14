# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    documents_product_settings = fields.Boolean(related='company_id.documents_product_settings', readonly=False,
                                                string="Product")
    product_folder = fields.Many2one('documents.folder', related='company_id.product_folder', readonly=False,
                                     string="product default workspace")
    product_tags = fields.Many2many('documents.tag', 'product_tags_table',
                                    related='company_id.product_tags', readonly=False,
                                    string="Product Tags")

    @api.onchange('product_folder')
    def on_product_folder_change(self):
        if self.product_folder != self.product_tags.mapped('folder_id'):
            self.product_tags = False
