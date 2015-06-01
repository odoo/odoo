# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv
from openerp.tools.translate import _

class crm_phonecall2meeting(osv.osv_memory):
    """ Phonecall to Meeting """

    _name = 'crm.phonecall2meeting'
    _description = 'Phonecall To Meeting'

    def action_cancel(self, cr, uid, ids, context=None):
        """
        Closes Phonecall to Meeting form
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Phonecall to Meeting IDs
        @param context: A standard dictionary for contextual values

        """
        return {'type':'ir.actions.act_window_close'}

    def action_make_meeting(self, cr, uid, ids, context=None):
        """ This opens Meeting's calendar view to schedule meeting on current Phonecall
            @return : Dictionary value for created Meeting view
        """
        res = {}
        phonecall_id = context and context.get('active_id', False) or False
        if phonecall_id:
            phonecall = self.pool.get('crm.phonecall').browse(cr, uid, phonecall_id, context)
            res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'calendar', 'action_calendar_event', context)
            res['context'] = {
                'default_phonecall_id': phonecall.id,
                'default_partner_id': phonecall.partner_id and phonecall.partner_id.id or False,
                'default_user_id': uid,
                'default_email_from': phonecall.email_from,
                'default_state': 'open',
                'default_name': phonecall.name,
            }
        return res
