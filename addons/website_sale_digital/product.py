# -*- encoding: utf-8 -*-
from openerp import models, fields, api, _


class product_template(models.Model):
    _inherit = ['product.template']

    attachment_count = fields.Integer(compute='_compute_attachment_count', string="File")

    @api.multi
    def _compute_attachment_count(self):
        IrAttachment = self.env['ir.attachment']
        prod_tmpl_attach_count = IrAttachment.read_group([('res_model', '=', 'product.template'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        prod_attach_count = IrAttachment.read_group([('res_model', '=', 'product.product'), ('res_id', 'in', self.product_variant_ids.ids)], ['res_id'], ['res_id'])
        prod_tmpl_result = dict((data['res_id'], data['res_id_count']) for data in prod_tmpl_attach_count)
        prod_attach_result = dict((data['res_id'], data['res_id_count']) for data in prod_attach_count)
        for ptemplate in self:
            ptemplate.attachment_count = prod_tmpl_result.get(ptemplate.id, 0) + sum(prod_attach_result.get(p.id, 0) for p in ptemplate.product_variant_ids)

    @api.model
    def _get_product_template_type(self):
        res = super(product_template, self)._get_product_template_type()
        if 'digital' not in [item[0] for item in res]:
            res.append(('digital', 'Digital Content'))
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


class product_product(models.Model):
    _inherit = 'product.product'

    attachment_count = fields.Integer(compute='_compute_attachment_count', string="File")

    @api.multi
    def _compute_attachment_count(self):
        read_count = self.env['ir.attachment'].read_group([('res_model', '=', self._name), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        result = dict((data['res_id'], data['res_id_count']) for data in read_count)
        for product in self:
            product.attachment_count = result.get(product.id, 0)

    @api.multi
    def action_open_attachments(self):
        self.ensure_one()
        return {
            'name': _('Digital Attachments'),
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,form',
            'view_type': 'form',
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id),
        }
