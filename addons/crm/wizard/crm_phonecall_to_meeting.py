# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _

class crm_phonecall2meeting(models.TransientModel):
    """ Phonecall to Meeting """

    _name = 'crm.phonecall2meeting'
    _description = 'Phonecall To Meeting'

    @api.multi
    def action_cancel(self):
        """
        Closes Phonecall to Meeting form
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Phonecall to Meeting IDs
        @param context: A standard dictionary for contextual values

        """
        return {'type':'ir.actions.act_window_close'}

    @api.multi
    def action_make_meeting(self):
        """ This opens Meeting's calendar view to schedule meeting on current Phonecall
            @return : Dictionary value for created Meeting view
        """
        res = {}
        phonecall_id = self._context and self._context.get('active_id', False) or False
        if phonecall_id:
            phonecall = self.env['crm.phonecall'].browse(phonecall_id)
            res = self.env['ir.actions.act_window'].for_xml_id('calendar', 'action_calendar_event')
            res['context'] = {
                'default_phonecall_id': phonecall.id,
                'default_partner_id': phonecall.partner_id and phonecall.partner_id.id or False,
                'default_user_id': self._uid,
                'default_email_from': phonecall.email_from,
                'default_state': 'open',
                'default_name': phonecall.name,
            }
        return res
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: