# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ProductProduct(models.Model):
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
                <p class="o_view_nocontent_smiling_face">{}</p>
                <p>{}</p>
                """.format(_("Add attachments for this digital product"),
                       _("The attached files are the ones that will be purchased and sent to the customer.")),
        }
