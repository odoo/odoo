# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from .. import base_calendar
from osv import fields, osv
from tools.translate import _
import tools


class base_calendar_invite_attendee(osv.osv_memory):
    """
    Invite attendee.
    """

    _name = "base_calendar.invite.attendee"
    _description = "Invite Attendees"

    _columns = {
        'type': fields.selection([('internal', 'Internal User'), \
              ('external', 'External Email'), \
              ('partner', 'Partner Contacts')], 'Type', required=True, help="Select whom you want to Invite"),
        'user_ids': fields.many2many('res.users', 'invite_user_rel',
                                  'invite_id', 'user_id', 'Users'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'email': fields.char('Email', size=124, help="Provide external email address who will receive this invitation."),
        'contact_ids': fields.many2many('res.partner', 'invite_contact_rel',
                                  'invite_id', 'contact_id', 'Contacts'),
        'send_mail': fields.boolean('Send mail?', help='Check this if you want to \
send an Email to Invited Person')
    }

    _defaults = {
        'type': 'internal',
        'send_mail': True
    }

    def do_invite(self, cr, uid, ids, context=None):
        """
        Invites attendee for meeting..
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of base calendar invite attendee’s IDs.
        @param context: A standard dictionary for contextual values
        @return: Dictionary of {}.
        """

        if context is None:
            context = {}

        model = False
        context_id = context and context.get('active_id', False) or False
        if not context or not context.get('model'):
            return {'type': 'ir.actions.act_window_close'}
        else:
            model = context.get('model')

        model_field = context.get('attendee_field', False)
        obj = self.pool.get(model)
        res_obj = obj.browse(cr, uid, context_id, context=context)
        att_obj = self.pool.get('calendar.attendee')
        user_obj = self.pool.get('res.users')
        current_user = user_obj.browse(cr, uid, uid, context=context)
        for datas in self.read(cr, uid, ids, context=context):
            type = datas.get('type')
            vals = []
            mail_to = []
            attendees = []
            ref = {}

            if not model == 'calendar.attendee':
                if context_id:
                    ref = {'ref': '%s,%s' % (model, base_calendar.base_calendar_id2real_id(context_id))}
                else:
                    return {'type': 'ir.actions.act_window_close'}
            if type == 'internal':
                
                if not datas.get('user_ids'):
                    raise osv.except_osv(_('Error!'), ("Please select any User."))
                for user_id in datas.get('user_ids'):
                    user = user_obj.browse(cr, uid, user_id)
                    res = {
                           'user_id': user_id,
                           'email': user.user_email
                           }
                    res.update(ref)
                    vals.append(res)
                    if user.user_email:
                        mail_to.append(user.user_email)

            elif  type == 'external' and datas.get('email'):
                res = {'email': datas['email']}
                res.update(ref)
                vals.append(res)
                mail_to.append(datas['email'])

            elif  type == 'partner':
                add_obj = self.pool.get('res.partner')
                for contact in  add_obj.browse(cr, uid, datas['contact_ids']):
                    res = {
                           'partner_id': contact.id,
                           'email': contact.email
                           }
                    res.update(ref)
                    vals.append(res)
                    if contact.email:
                        mail_to.append(contact.email)

            for att_val in vals:
                if model == 'calendar.attendee':
                    att = att_obj.browse(cr, uid, context_id)
                    att_val.update({
                        'parent_ids': [(4, att.id)],
                        'ref': att.ref and (att.ref._name + ',' +str(att.ref.id)) or False
                        })

                attendees.append(att_obj.create(cr, uid, att_val))
            if model_field:
                for attendee in attendees:
                    obj.write(cr, uid, res_obj.id, {model_field: [(4, attendee)]})

            if datas.get('send_mail'):
                if not mail_to:
                    name =  map(lambda x: x[1], filter(lambda x: type==x[0], \
                                       self._columns['type'].selection))
                    raise osv.except_osv(_('Error!'), _("%s must have an email  address to send mail.") %(name[0]))
                att_obj._send_mail(cr, uid, attendees, mail_to, \
                       email_from = current_user.user_email or tools.config.get('email_from', False))

        return {'type': 'ir.actions.act_window_close'}


    def onchange_partner_id(self, cr, uid, ids, partner_id, *args, **argv):
        """
        Make entry on contact_ids on change of partner_id field.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of base calendar invite attendee’s IDs.
        @param partner_id: id of Partner
        @return: dictionary of value.
        """

        if not partner_id:
            return {'value': {'contact_ids': []}}
        cr.execute('SELECT id FROM res_partner \
                         WHERE id=%s or parent_id =%s' , (partner_id,partner_id,))
        contacts = map(lambda x: x[0], cr.fetchall())
        return {'value': {'contact_ids': contacts}}

base_calendar_invite_attendee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
