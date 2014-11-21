# -*- coding: utf-8 -*-

from openerp import api, fields, models

class CrmPhoneCall2Meeting(models.TransientModel):
    """ Phonecall to Meeting """

    _name = 'crm.phonecall2meeting'
    _description = 'Phonecall To Meeting'

    def action_cancel(self):
        """
        Closes Phonecall to Meeting form
        @param self: The object pointer

        """
        return {'type':'ir.actions.act_window_close'}

    @api.multi
    def action_make_meeting(self):
        """ This opens Meeting's calendar view to schedule meeting on current Phonecall
            @return : Dictionary value for created Meeting view
        """
        self.ensure_one()
        res = {}
        phonecall_id = self.env.context.get('active_id')
        if phonecall_id:
            phonecall = self.env['crm.phonecall'].browse(phonecall_id)
            res = self.env['ir.actions.act_window'].for_xml_id('calendar', 'action_calendar_event')
            res['context'] = {
                'default_phonecall_id': phonecall.id,
                'default_partner_id': phonecall.partner_id.id,
                'default_user_id': self.env.uid,
                'default_email_from': phonecall.email_from,
                'default_state': 'open',
                'default_name': phonecall.name,
            }
        return res
