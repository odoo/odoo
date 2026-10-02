# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2022-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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

from odoo import api, fields, models
from ast import literal_eval


class ResConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    def _get_contacts_fields_domain(self):
        return [
            ('model', '=', 'res.partner'), ('store', '=', True),
            ('ttype', 'in', ['binary', 'char'])]

    is_unique_contact = fields.Boolean(string="Unique Contacts Alert")
    unique_contact_ids = fields.Many2many(
        'ir.model.fields', string='Contact Fields',
        domain=_get_contacts_fields_domain,
        help='Warning to avoid duplication of customer/vendor'
             ' details in the system')

    def set_values(self):
        super(ResConfig, self).set_values()
        self.env['ir.config_parameter'].set_param(
            'duplicate_contact_details_alert.is_unique_contact',
            self.is_unique_contact)

        self.env['ir.config_parameter'].set_param(
            'duplicate_contact_details_alert.unique_contact_ids',
            self.unique_contact_ids.ids)

    @api.model
    def get_values(self):
        res = super(ResConfig, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        contact_field_ids = params.get_param(
            'duplicate_contact_details_alert.unique_contact_ids')
        if contact_field_ids:
            res.update(
                is_unique_contact=params.get_param(
                    'duplicate_contact_details_alert.is_unique_contact'),
                unique_contact_ids=[(6, 0, literal_eval(contact_field_ids))],
            )
            return res
        else:
            return res
