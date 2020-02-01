# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = ['product.template']

    attachment_count = fields.Integer(compute='_compute_attachment_count', string="File")

    def _compute_attachment_count(self):
        attachment_data = self.env['ir.attachment'].read_group([('res_model', '=', self._name), ('res_id', 'in', self.ids), ('product_downloadable', '=', True)], ['res_id'], ['res_id'])
        mapped_data = dict([(data['res_id'], data['res_id_count']) for data in attachment_data])
        for product_template in self:
            product_template.attachment_count = mapped_data.get(product_template.id, 0)

    def action_open_attachments(self):
        self.ensure_one()
        return {
            'name': _('Digital Attachments'),
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id), ('product_downloadable', '=', True)],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,form',
            'context': "{'default_res_model': '%s','default_res_id': %d, 'default_product_downloadable': True}" % (self._name, self.id),
            'help': """
                <p class="o_view_nocontent_smiling_face">Add attachments for this digital product</p>
                <p>The attached files are the ones that will be purchased and sent to the customer.</p>
                """,
        }


class Product(models.Model):
    _inherit = 'product.product'

    attachment_count = fields.Integer(compute='_compute_attachment_count', string="File")

    def _compute_attachment_count(self):
        for product in self:
            product.attachment_count = self.env['ir.attachment'].search_count([
                '|',
                '&', '&', ('res_model', '=', 'product.template'), ('res_id', '=', product.product_tmpl_id.id), ('product_downloadable', '=', True),
                '&', '&', ('res_model', '=', 'product.product'), ('res_id', '=', product.id), ('product_downloadable', '=', True)])

    def action_open_attachments(self):
        self.ensure_one()
        return {
            'name': _('Digital Attachments'),
            'domain': [('product_downloadable', '=', True), '|',
                       '&', ('res_model', '=', 'product.template'), ('res_id', '=', self.product_tmpl_id.id),
                       '&', ('res_model', '=', self._name), ('res_id', '=', self.id)],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,form',
            'context': "{'default_res_model': '%s','default_res_id': %d, 'default_product_downloadable': True}" % (self._name, self.id),
            'help': """
                <p class="o_view_nocontent_smiling_face">Add attachments for this digital product</p>
                <p>The attached files are the ones that will be purchased and sent to the customer.</p>
                """,
        }
