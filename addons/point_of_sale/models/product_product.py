# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('product_tmpl_id', 'in', [p['id'] for p in data['product.template']])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'lst_price', 'display_name', 'product_tmpl_id', 'product_template_variant_value_ids', 'barcode', 'product_tag_ids']

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active_pos_session(self):
        product_ctx = dict(self.env.context or {}, active_test=False)
        if self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
            if self.with_context(product_ctx).search_count([('id', 'in', self.ids), ('product_tmpl_id.available_in_pos', '=', True)]):
                raise UserError(_(
                    "To delete a product, make sure all point of sale sessions are closed.\n\n"
                    "Deleting a product available in a session would be like attempting to snatch a hamburger from a customer’s hand mid-bite; chaos will ensue as ketchup and mayo go flying everywhere!",
                ))
