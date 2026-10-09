# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Shonima (odoo@cybrosys.com)
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
################################################################################
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Inherited res.config.settings class to add  fields and functions to get
     and set values in purchase settings form"""
    _inherit = 'res.config.settings'

    is_auto_generate = fields.Boolean(string='Auto Generate',
                                      help="Based on this selection it shows "
                                           "the fields for auto generating "
                                           "lot/serial number",
                                      config_parameter="auto_generate_lot_number.is_auto_generate")
    serial_number_type = fields.Selection(
        [('global', 'Global'), ('product', 'Product Wise')],
        default='global', string='Serial/lot Number',
        help="Generate the lot/serial number product wise or globally",
        config_parameter="auto_generate_lot_number.serial_number_type")
    prefix = fields.Char(string='Prefix',
                         help="Prefix value of the record for sequence",
                         config_parameter="auto_generate_lot_number.prefix")
    digits = fields.Integer(string='Digits',
                            help="Used to set number of digits contain in a "
                                 "sequence",
                            config_parameter="auto_generate_lot_number.digits")

    @api.onchange('is_auto_generate')
    def _onchange_auto_generate(self):
        """Based on the change of is_auto_generate is updated the boolean field
        'check_auto_generate' in company"""
        self.env.company.check_auto_generate = False
        if self.is_auto_generate:
            self.env.company.check_auto_generate = True
