# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _restore_shopee_data_product(self, default_name, default_type, xmlid):
        """ Create a product and assign it the provided and previously valid xmlid.

        :param str default_name: The name of the product
        :param str default_type: The type of the product
        :param str xmlid: The xmlid of the product
        :return: The created product
        """
        product = self.env['product.product'].with_context(mail_create_nosubscribe=True).create({
            'name': default_name,
            'type': default_type,
            'list_price': 0.,
            'sale_ok': False,
            'purchase_ok': False,
        })
        product._configure_for_shopee()
        ir_model = self.env['ir.model.data'].search(
            [('module', '=', 'sale_shopee'), ('name', '=', xmlid)]
        )
        if not ir_model:
            self.env['ir.model.data'].create({
                'module': 'sale_shopee',
                'name': xmlid,
                'model': 'product.product',
                'res_id': product.id,
            })
        else:
            ir_model.res_id = product.id
        return product

    def _configure_for_shopee(self):
        """ Archive products and their templates and define their invoice policy. """
        # Archiving is achieved by the mean of write instead of toggle_active to allow this method
        # to be called from data without restoring the products when they were already archived.
        self.active = False
        for product_template in self.product_tmpl_id:
            product_template.write({
                'active': False,
                'invoice_policy': 'order' if product_template.type == 'service' else 'delivery',
            })
