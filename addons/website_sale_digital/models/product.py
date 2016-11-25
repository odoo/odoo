# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from collections import defaultdict


class ProductTemplate(models.Model):
    _inherit = ['product.template']

    attachment_count = fields.Integer(compute='_compute_attachment_count', string="File")

    @api.multi
    def _compute_attachment_count(self):
        attachment_data = self.env['ir.attachment'].read_group([('res_model', '=', self._name), ('res_id', 'in', self.ids), ('product_downloadable', '=', True)], ['res_id'], ['res_id'])
        mapped_data = dict([(data['res_id'], data['res_id_count']) for data in attachment_data])
        for product_template in self:
            product_template.attachment_count = mapped_data.get(product_template.id, 0)

    @api.multi
    def action_open_attachments(self):
        self.ensure_one()
        return {
            'name': _('Digital Attachments'),
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id), ('product_downloadable', '=', True)],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,form',
            'view_type': 'form',
            'context': {'default_res_model': self._name, 'default_res_id': self.id, 'default_product_downloadable': True, 'default_name': self.name},
            'help': """
                <p class="oe_view_nocontent_create">Click on create to add attachments for this digital product.</p>
                <p>The attached files are the ones that will be purchased and sent to the customer.</p>
                """,
        }


class Product(models.Model):
    _inherit = 'product.product'

    attachment_count = fields.Integer(compute='_compute_attachment_count', string="File")

    @api.multi
    def _compute_attachment_count(self):
        IrAttachment = self.env['ir.attachment']
        for product in self:
            prod_tmpl_attach_count = IrAttachment.search_count([('res_model', '=', 'product.template'), ('res_id', 'in', product.product_tmpl_id.ids), ('product_downloadable', '=', True)])
            prod_attach_count = IrAttachment.search_count([('res_model', '=', 'product.product'), ('res_id', 'in', product.ids), ('product_downloadable', '=', True)])
            product.attachment_count = prod_tmpl_attach_count + prod_attach_count

    @api.multi
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
            'view_type': 'form',
            'context': {'default_res_model': self._name, 'default_res_id': self.id, 'default_product_downloadable': True, 'default_name': self.product_tmpl_id.name},
            'help': """
                <p class="oe_view_nocontent_create">Click on create to add attachments for this digital product.</p>
                <p>The attached files are the ones that will be purchased and sent to the customer.</p>
                """,
        }

    @api.multi
    def get_digital_attachment(self):
        template_ids = self.mapped('product_tmpl_id').ids
        result = defaultdict(list)
        product_product_atts = self.env['ir.attachment'].search_read(
                domain=[('product_downloadable', '=', True), ('res_model', '=', 'product.product'), ('res_id', 'in', self.ids)],
                fields=["name", "res_model", "res_id", "type", "url"])
        for attachment in product_product_atts:
            result[attachment['res_id']].append(attachment)
        product_template_atts = self.env['ir.attachment'].search_read(
                domain=[('product_downloadable', '=', True), ('res_model', '=', 'product.template'), ('res_id', 'in', template_ids)],
                fields=["name", "res_model", "res_id", "type", "url"])
        for attachment in product_template_atts:
            related_products = self.filtered(lambda r: r.product_tmpl_id.id == attachment['res_id'])
            for p in related_products:
                result[p.id].append(attachment)
        return result
