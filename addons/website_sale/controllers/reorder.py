# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.addons.sale.controllers import portal as sale_portal


class CustomerPortal(sale_portal.CustomerPortal):

    def _sale_reorder_get_line_context(self):
        return {}

    def _get_common_order_line_data(self, line, add_to_cart_allowed=True):
        combination = (
            line.product_id.product_template_attribute_value_ids
            | line.product_no_variant_attribute_value_ids
        )
        return {
            'product_template_id': line.product_id.product_tmpl_id.id,
            'product_id': line.product_id.id,
            'combination': combination.ids,
            'no_variant_attribute_value_ids': line.product_no_variant_attribute_value_ids.ids,
            'product_custom_attribute_values': [
                {
                    'custom_product_template_attribute_value_id': pcav.custom_product_template_attribute_value_id.id,
                    'custom_value': pcav.custom_value,
                }
                for pcav in line.product_custom_attribute_value_ids
            ],
            'qty': line.product_uom_qty,
            'combinationInfo': line.product_id.product_tmpl_id.with_context(
                **self._sale_reorder_get_line_context()
            )._get_combination_info(combination, line.product_id.id, line.product_uom_qty)
            if add_to_cart_allowed else {},
        }

    @route('/my/orders/reorder_modal_content', type='json', auth='public', website=True)
    def my_orders_reorder_modal_content(self, order_id, access_token):
        try:
            sale_order = self._document_check_access(
                'sale.order', order_id, access_token=access_token,
            ).with_user(request.env.user).sudo()
        except (AccessError, MissingError):
            return request.redirect('/my')

        currency = request.env['website'].get_current_website().currency_id
        result = {
            'currency': currency.id,
            'products': [],
        }
        for line in sale_order.order_line:
            if not line._show_in_cart():
                continue

            selected_combo_items = []
            if line.product_id.type == 'combo':
                for linked_line in line.linked_line_ids.filtered('combo_item_id'):
                    selected_combo_items.append({
                        **self._get_common_order_line_data(linked_line),
                        'combo_item_id': linked_line.combo_item_id.id,
                    })

            add_to_cart_allowed = line.with_user(request.env.user).sudo()._is_reorder_allowed()
            res = {
                **self._get_common_order_line_data(line, add_to_cart_allowed),
                'type': line.product_id.type,
                'name': line.name_short,
                'description_sale': line.product_id.description_sale or '' + line._get_sale_order_line_multiline_description_variants(),
                'add_to_cart_allowed': add_to_cart_allowed,
                'has_image': bool(line.product_id.image_128),
                'selected_combo_items': selected_combo_items,
            }

            result['products'].append(res)
        return result
