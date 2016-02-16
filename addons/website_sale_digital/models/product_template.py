# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = ['product.template']

    attachment_count = fields.Integer(compute='_compute_attachment_count', string="File")

    @api.multi
    def _compute_attachment_count(self):
        IrAttachment = self.env['ir.attachment']
        for ptemplate in self:
            prod_tmpl_attach_count = IrAttachment.search_count([('res_model', '=', 'product.template'), ('res_id', 'in', ptemplate.ids)])
            prod_attach_count = IrAttachment.search_count([('res_model', '=', 'product.product'), ('res_id', 'in', ptemplate.product_variant_ids.ids)])
            ptemplate.attachment_count = prod_tmpl_attach_count + prod_attach_count

    @api.model
    def _get_product_template_type(self):
        res = super(ProductTemplate, self)._get_product_template_type()
        if 'digital' not in [item[0] for item in res]:
            res.append(('digital', _('Digital Content')))
        return res

    @api.multi
    def action_open_attachments(self):
        self.ensure_one()
        return {
            'name': _('Digital Attachments'),
            'domain': ['|',
                       '&', ('res_model', '=', 'product.product'), ('res_id', 'in', self.product_variant_ids.ids),
                       '&', ('res_model', '=', self._name), ('res_id', '=', self.id)],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,form',
            'view_type': 'form',
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id),
        }
