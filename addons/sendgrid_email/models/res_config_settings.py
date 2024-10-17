# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Noushid Khan.P (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################

from odoo import models, fields, api, _


class SendGridApiConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    send_grid_api_check = fields.Boolean(string="SendGrid API")
    send_grid_api_value = fields.Char(string='API key')

    def set_values(self):
        """ save values in the settings fields """

        super(SendGridApiConfig, self).set_values()
        company_id = self.env.company
        self.env['ir.config_parameter'].sudo().set_param("SendGrid API Key "+company_id.name+"",
                                                         self.send_grid_api_value)
