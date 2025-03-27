# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Anfas Faisal K (<https://www.cybrosys.com>)
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
from odoo import models


class PosSession(models.Model):
    """
    This is an Odoo model for Point of Sale (POS) sessions.
    It inherits from the 'pos.session' model and extends its functionality.

     Methods: _loader_params_product_product(): Adds the 'alert_tag' field to
     the search parameters for the product loader.
    """
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        """ Adds the 'alert_tag' field to the search parameters for the
        product loader.

        Returns:
            dict: The updated search parameters for the product loader.
        """
        result = super()._loader_params_product_product()
        result['search_params']['fields'].append('alert_tag')
        return result
