# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
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
from odoo import fields, models, _


class ResPartner(models.Model):
    """Inheriting res partner for including Twilio fields and functions"""
    _inherit = 'res.partner'

    twilio_contact_id = fields.Many2one('twilio.sms.group',
                                        string='Twilio ID',
                                        help='Twilio Connection ID')

    def action_partner_twilio_sms(self):
        """Action for opening the SMS wizard view"""
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Message Content'),
            'res_model': 'sms.builder',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id},
            'views': [[False, 'form']]
        }
        return action
