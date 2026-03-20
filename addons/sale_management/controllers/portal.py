# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.addons.sale.controllers import portal


class CustomerPortal(portal.CustomerPortal):

    @route(['/my/orders/<int:order_id>/update_line_dict'], type='jsonrpc', auth="public", website=True)
    def portal_quote_option_update(self, order_id, line_id, access_token=None, remove=False, input_quantity=False, **kwargs):
        """ Update the quantity of an optional SOline from a SO.

        :param int order_id: `sale.order` id
        :param int line_id: `sale.order.line` id
        :param str access_token: portal access_token of the specified order
        :param bool remove: if true, 1 unit will be removed from the line
        :param float input_quantity: if specified, will be set as new line qty
        :param dict kwargs: unused parameters
        """
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Redundant with can be edited on portal for line, ask sales if can rbe removed
        if not order_sudo._can_be_edited_on_portal():
            return

        order_line = request.env['sale.order.line'].sudo().browse(int(line_id)).exists()
        if (
            not order_line
            or order_line.order_id != order_sudo
            or not order_line._can_be_edited_on_portal()
        ):
            # Do not allow updating non-optional lines from a quotation
            return

        if input_quantity is not False:
            quantity = input_quantity
        else:
            number = -1 if remove else 1
            quantity = max((order_line.product_uom_qty + number), 0)

        if order_line.product_type == 'combo':
            # for combo products, we update the quantities of the combo items too
            combo_item_lines = order_line._get_linked_lines().filtered('combo_item_id')
            combo_item_lines.update({'product_uom_qty': quantity})

        order_line.product_uom_qty = quantity
