# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    offer_count = fields.Integer(
        compute='_compute_offer_count', groups='sales_team.group_sale_manager'
    )

    def _compute_offer_count(self):
        offers_data = self.env['amazon.offer']._read_group(
            [('product_id', 'in', self.ids)], ['product_id'], ['__count']
        )
        products_data = {product.id: count for product, count in offers_data}
        for product in self:
            product.offer_count = products_data.get(product.id, 0)

    def action_view_offers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Offers'),
            'res_model': 'amazon.offer',
            'view_mode': 'list,form',
            'context': {'create': False},
            'domain': [('product_id', '=', self.id)],
        }

    @api.model
    def _restore_data_product(self, default_name, default_type, xmlid):
        """ Create a product and assign it the provided and previously valid xmlid. """
        product = self.env['product.product'].with_context(mail_create_nosubscribe=True).create({
            'name': default_name,
            'type': default_type,
            'list_price': 0.,
            'sale_ok': False,
            'purchase_ok': False,
        })
        product._configure_for_amazon()
        self.env['ir.model.data'].search(
            [('module', '=', 'sale_amazon'), ('name', '=', xmlid)]
        ).write({'res_id': product.id})
        return product

    def _configure_for_amazon(self):
        """ Archive products and their templates and define their invoice policy. """
        # Archiving is achieved by the mean of write instead of toggle_active to allow this method
        # to be called from data without restoring the products when they were already archived.
        self.write({'active': False})
        for product_template in self.product_tmpl_id:
            product_template.write({
                'active': False,
                'invoice_policy': 'order' if product_template.type == 'service' else 'delivery',
            })
