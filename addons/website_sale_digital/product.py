# -*- encoding: utf-8 -*-
from openerp import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = ['product.template']

    attachment_count = fields.Integer(compute='_compute_attachment_count', string="File")

    @api.multi
    def _compute_attachment_count(self):
        IrAttachment = self.env['ir.attachment']
        for ptemplate in self:
            ptemplate.attachment_count = IrAttachment.search_count([('res_model', '=', ptemplate._name), ('res_id', 'in', ptemplate.ids), ('product_downloadable', '=', True)])

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
            'context': "{'default_res_model': '%s','default_res_id': %d, 'default_product_downloadable': True}" % (self._name, self.id),
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
                       '&', ('res_model', '=', 'product.template'), '&', ('res_id', '=', self.product_tmpl_id.id),
                       '&', ('res_model', '=', self._name), '&', ('res_id', '=', self.id)],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,form',
            'view_type': 'form',
            'context': "{'default_res_model': '%s','default_res_id': %d, 'default_product_downloadable': True}" % (self._name, self.id),
        }
