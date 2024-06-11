# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.addons.sale.controllers import portal


class CustomerPortal(portal.CustomerPortal):

    @route(['/my/orders/<int:order_id>/update_line_dict'], type='json', auth="public", website=True)
    def portal_quote_option_update(self, order_id, line_id, access_token=None, remove=False, unlink=False, input_quantity=False, **kwargs):
        """ Update the quantity or Remove an optional SOline from a SO.

        :param int order_id: `sale.order` id
        :param int line_id: `sale.order.line` id
        :param str access_token: portal access_token of the specified order
        :param bool remove: if true, 1 unit will be removed from the line
        :param bool unlink: if true, the option will be removed from the SO
        :param float input_quantity: if specified, will be set as new line qty
        :param dict kwargs: unused parameters
        """
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Redundant with can be edited on portal for line, ask sales if can rbe removed
        if not order_sudo._can_be_edited_on_portal():
            return False

        order_line = request.env['sale.order.line'].sudo().browse(int(line_id)).exists()
        if not order_line or order_line.order_id != order_sudo:
            return False

        if not order_line._can_be_edited_on_portal():
            # Do not allow updating non-optional products from a quotation
            return False

        if input_quantity is not False:
            quantity = input_quantity
        else:
            number = -1 if remove else 1
            quantity = order_line.product_uom_qty + number

        if unlink or quantity <= 0:
            order_line.unlink()
        else:
            order_line.product_uom_qty = quantity

    @route(["/my/orders/<int:order_id>/add_option/<int:option_id>"], type='json', auth="public", website=True)
    def portal_quote_add_option(self, order_id, option_id, access_token=None, **kwargs):
        """ Add the specified option to the specified order.

        :param int order_id: `sale.order` id
        :param int option_id: `sale.order.option` id
        :param str access_token: portal access_token of the specified order
        :param dict kwargs: unused parameters
        """
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        option_sudo = request.env['sale.order.option'].sudo().browse(option_id)

        if order_sudo != option_sudo.order_id:
            return request.redirect(order_sudo.get_portal_url())

        option_sudo.add_option_to_order()
