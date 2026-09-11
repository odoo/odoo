# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import http
from odoo.http import request


class SellerDashboard(http.Controller):
    """This Class for creating dashboard"""

    @http.route(['/seller_dashboard'], type='json', auth="public",
                website=True)
    def seller_dashboard(self):
        """Load the dashboard information"""
        return {'pending': request.env['product.template'].search_count(
            [('state', '=', 'pending')]),
            'approved': request.env['product.template'].search_count(
                [('state', '=', 'approved')]),
            'rejected': request.env['product.template'].search_count(
                [('state', '=', 'rejected')]),
            'user_type': request.env['res.users'].has_group(
                'multi_vendor_marketplace.multi_vendor_marketplace_admin'),
            'seller_pending': request.env['res.partner'].search_count(
                [('state', '=', 'Pending for Approval')]),
            'seller_approved': request.env['res.partner'].search_count(
                [('state', '=', 'Approved')]),
            'seller_rejected': request.env['res.partner'].search_count(
                [('state', '=', 'Denied')]),
            'inventory_pending': request.env['inventory.request'].search_count(
                [('state', '=', 'Requested')]),
            'inventory_approved': request.env[
                'inventory.request'].search_count(
                [('state', '=', 'Approved')]),
            'inventory_rejected': request.env[
                'inventory.request'].search_count(
                [('state', '=', 'Rejected')]),
            'payment_pending': request.env['seller.payment'].search_count(
                [('state', '=', 'Requested')]),
            'payment_approved': request.env['seller.payment'].search_count(
                [('state', '=', 'Validated')]),
            'payment_rejected': request.env['seller.payment'].search_count(
                [('state', '=', 'Rejected')]),
            'order_pending': request.env['sale.order.line'].search_count(
                [('state', '=', 'pending')]),
            'order_approved': request.env['sale.order.line'].search_count(
                [('state', '=', 'approved')]),
            'order_shipped': request.env['sale.order.line'].search_count(
                [('state', '=', 'shipped')]),
            'order_cancel': request.env['sale.order.line'].search_count(
                [('state', '=', 'cancel')]),
            'sale_order_kanban_id': request.env['ir.ui.view'].search(
                [('name', '=', 'multi.vendor.sale.order.line.kanban')]).id,
            'product_kanban_id': request.env['ir.ui.view'].search(
                [('name', '=', 'multi.vendor.view.kanban')]).id,
            'sale_order_form_id': request.env['ir.ui.view'].search(
                [(
                    'name', '=',
                    'multi.vendor.sale.order.line.form.readonly')]).id
        }
