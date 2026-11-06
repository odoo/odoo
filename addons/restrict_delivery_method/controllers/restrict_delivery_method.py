# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Shafna K(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import _
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery


class RestrictWebsiteDeliveryMethod(WebsiteSaleDelivery):
    """This class is the inherited class and uses the function in that
    class and super that function"""
    def _get_shop_payment_values(self, order, **kwargs):
        """Using this function we call another function
        to restrict delivery method"""
        res = super()._get_shop_payment_values(order, **kwargs)
        if not order._get_restrict_delivery_method():
            res['errors'].append(
                (_('Sorry, we are unable to ship your order'),
                 _('No shipping method is available for the product(s) you '
                   'have chosen.'
                   'Please contact us for more information.')))
        delivery_carriers = order._get_restrict_delivery_method()
        res['deliveries'] = delivery_carriers.sudo()
        return res
