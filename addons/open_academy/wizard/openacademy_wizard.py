# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Dhanya Babu (<https://www.cybrosys.com>)
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
###############################################################################
from odoo import fields, models


class OpenacademyWizard(models.TransientModel):
    """This model represents a wizard that allows users to quickly register
    attendees to selected sessions.The wizard is triggered from a session 's
    form view, and it allows the user to select one or more sessions and add
    attendees to them in a single step."""
    _name = 'openacademy.wizard'
    _description = "Wizard: Quick Registration of Attendees to Sessions"

    def _default_sessions(self):
        """this method is used to get the sessions
        that are currently selected in the view"""
        return self.env['openacademy.session'].browse(
            self._context.get('active_ids'))

    session_ids = fields.Many2many('openacademy.session',
                                   string="Session", required=True,
                                   default=_default_sessions, help='Session')
    attendee_ids = fields.Many2many('res.partner', string="Attendees",
                                    help='Attendees')

    def subscribe(self):
        """This function subscribes attendees to the selected sessions"""
        for session in self.session_ids:
            session.attendee_ids |= self.attendee_ids
        return {}
