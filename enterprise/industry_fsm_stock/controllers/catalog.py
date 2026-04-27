# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.addons.industry_fsm_sale.controllers.catalog import CatalogControllerFSM

class CatalogControllerFSMStock(CatalogControllerFSM):

    @route()
    def product_catalog_update_order_line_info(self, res_model, order_id, product_id, quantity=0, **kwargs):
        """ Update sale order line information on a given sale order for a given product.

        :param int order_id: The sale order, as a `sale.order` id.
        :param int product_id: The product, as a `product.product` id.
        :param int task_id: The task, as a `project.task` id. also available in the context but clearer in argument
        :param float quantity: The quantity selected in the product catalog.
        :param list context: the context comming from the view, used only to propagate the 'fsm_task_id' for the action_assign_serial on the product.
        :return: The unit price of the product, based on the pricelist of the sale order and
                 the quantity selected. Plus the new minimum quantity for the product
        :rtype: A dictionary containing the SN action and the SOL price_unit
        """
        task_id = kwargs.get('task_id')
        super_dict = super().product_catalog_update_order_line_info(res_model, order_id, product_id, quantity, **kwargs)
        if not task_id:
            return super_dict
        task = request.env['project.task'].browse(task_id)
        sol = request.env['sale.order.line'].search([
            ('order_id', '=', task.sale_order_id.id), ('product_id', '=', product_id),
        ], limit=1)
        super_dict["min_quantity"] = sol.product_id.fsm_quantity - sol.product_id.quantity_decreasable_sum
        return super_dict
