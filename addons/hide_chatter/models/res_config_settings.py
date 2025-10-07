# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Muhsina V (<https://www.cybrosys.com>)
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
#############################################################################
from ast import literal_eval
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """
    Extend the 'res.config.settings' model to manage configuration settings for
     enabling/disabling the chatter feature.
    """
    _inherit = 'res.config.settings'

    model_ids = fields.Many2many('ir.model', string="Models",
                                 help="Choose the models to hide their "
                                      "chatter")

    def set_values(self):
        """
        Override the 'set_values' method to save the selected models as
        configuration parameters.
        """
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'chatter_enable.model_ids', self.model_ids.ids)
        return res

    @api.model
    def get_values(self):
        """
        Override the 'get_values' method to retrieve the selected models from
        configuration parameters.
        """
        res = super(ResConfigSettings, self).get_values()
        selected_models = self.env['ir.config_parameter'].sudo().get_param(
            'chatter_enable.model_ids')
        res.update(model_ids=[(6, 0, literal_eval(
            selected_models))] if selected_models else False, )
        return res
