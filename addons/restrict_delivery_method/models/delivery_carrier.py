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
from odoo import api, fields, models, _


class DeliveryCarrier(models.Model):
    """This contains the fields added in shipping methods in odoo"""
    _inherit = "delivery.carrier"

    restrict_product_ids = fields.Many2many('product.template',
                                            string="Restrict Product",
                                            help="Choose the products"
                                                 " to restrict from this "
                                                 "delivery method")
    partner_warning = fields.Boolean(string="Warning",
                                     help="Enable if partner "
                                          "warning needed")

    def action_notification(self):
        """Function to show the sticky notification"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Warning',
                'message': _("Default delivery method given for a partner"
                             " cannot be restricted!"),
                'type': 'warning',
                'sticky': False,
            }
        }

    @api.onchange('restrict_product_ids')
    def _onchange_restrict_product_ids(self):
        """To show a warning when products are given for restriction"""
        if self.restrict_product_ids:
            self.partner_warning = True
        else:
            self.partner_warning = False
