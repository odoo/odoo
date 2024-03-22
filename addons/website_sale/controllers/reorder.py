# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.addons.sale.controllers import portal as sale_portal


class CustomerPortal(sale_portal.CustomerPortal):

    def _sale_reorder_get_line_context(self):
        return {}

    @route('/my/orders/reorder_modal_content', type='json', auth='public', website=True)
    def my_orders_reorder_modal_content(self, order_id, access_token):
        try:
            sale_order = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        currency = request.env['website'].get_current_website().currency_id
        result = {
            'currency': currency.id,
            'products': [],
        }
        for line in sale_order.order_line:
            if line.display_type:
                continue
            if line._is_delivery():
                continue
            combination = line.product_id.product_template_attribute_value_ids | line.product_no_variant_attribute_value_ids
            res = {
                'product_template_id': line.product_id.product_tmpl_id.id,
                'product_id': line.product_id.id,
                'combination': combination.ids,
                'no_variant_attribute_value_ids': line.product_no_variant_attribute_value_ids.ids,
                'product_custom_attribute_values': [
                    { # Same input format as provided by product configurator
                        'custom_product_template_attribute_value_id': pcav.custom_product_template_attribute_value_id.id,
                        'custom_value': pcav.custom_value,
                    } for pcav in line.product_custom_attribute_value_ids
                ],
                'type': line.product_id.type,
                'name': line.name_short,
                'description_sale': line.product_id.description_sale or '' + line._get_sale_order_line_multiline_description_variants(),
                'qty': line.product_uom_qty,
                'add_to_cart_allowed': line.with_user(request.env.user).sudo()._is_reorder_allowed(),
                'has_image': bool(line.product_id.image_128),
            }
            if res['add_to_cart_allowed']:
                res['combinationInfo'] = line.product_id.product_tmpl_id.with_context(
                    **self._sale_reorder_get_line_context()
                )._get_combination_info(combination, res['product_id'], res['qty'])
            else:
                res['combinationInfo'] = {}
            result['products'].append(res)
        return result
