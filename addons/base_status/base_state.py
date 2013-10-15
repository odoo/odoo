# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class base_state(object):
    """ Base utility mixin class for objects willing to manage their state.
        Object subclassing this class should define the following colums:
        - ``date_open`` (datetime field)
        - ``date_closed`` (datetime field)
        - ``user_id`` (many2one to res.users)
        - ``partner_id`` (many2one to res.partner)
        - ``email_from`` (char field)
        - ``state`` (selection field)
    """

    def _get_default_partner(self, cr, uid, context=None):
        """ Gives id of partner for current user
            :param context: if portal not in context returns False
        """
        if context is None:
            context = {}
        if not context or not context.get('portal'):
            return False
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if hasattr(user, 'partner_address_id') and user.partner_address_id:
            return user.partner_address_id
        return user.company_id.partner_id.id

    def _get_default_email(self, cr, uid, context=None):
        """ Gives default email address for current user
            :param context: if portal not in context returns False
        """
        if context is None:
            context = {}
        if not context or not context.get('portal'):
            return False
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.email

    def _get_default_user(self, cr, uid, context=None):
        """ Gives current user id
            :param context: if portal not in context returns False
        """
        if context is None:
            context = {}
        if not context or not context.get('portal'):
            return False
        return uid

    def onchange_partner_address_id(self, cr, uid, ids, add, email=False):
        """ This function returns value of partner email based on Partner Address
            :param add: Id of Partner's address
            :param email: Partner's email ID
        """
        data = {'value': {'email_from': False, 'phone':False}}
        if add:
            address = self.pool.get('res.partner').browse(cr, uid, add)
            data['value'] = {'email_from': address and address.email or False ,
                             'phone':  address and address.phone or False}
        if 'phone' not in self._columns:
            del data['value']['phone']
        return data

    def onchange_partner_id(self, cr, uid, ids, part, email=False):
        """ This function returns value of partner address based on partner
            :param part: Partner's id
            :param email: Partner's email ID
        """
        data={}
        if  part:
            addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['contact'])
            data.update(self.onchange_partner_address_id(cr, uid, ids, addr['contact'])['value'])
        return {'value': data}

    def case_escalate(self, cr, uid, ids, context=None):
        """ Escalates case to parent level """
        cases = self.browse(cr, uid, ids, context=context)
        cases[0].state # fill browse record cache, for _action having old and new values
        data = {'active': True}
        for case in cases:
            parent_id = case.section_id.parent_id
            if parent_id:
                data['section_id'] = parent_id.id
                if parent_id.change_responsible and parent_id.user_id:
                    data['user_id'] = parent_id.user_id.id
            else:
                raise osv.except_osv(_('Error!'), _('You can not escalate, you are already at the top level regarding your sales-team category.'))
            self.write(cr, uid, [case.id], data, context=context)
            case.case_escalate_send_note(parent_id, context=context)
        return True

    def case_open(self, cr, uid, ids, context=None):
        """ Opens case """
        cases = self.browse(cr, uid, ids, context=context)
        for case in cases:
            values = {'active': True}
            if case.state == 'draft':
                values['date_open'] = fields.datetime.now()
            if not case.user_id:
                values['user_id'] = uid
            self.case_set(cr, uid, [case.id], 'open', values, context=context)
        return True

    def case_close(self, cr, uid, ids, context=None):
        """ Closes case """
        return self.case_set(cr, uid, ids, 'done', {'date_closed': fields.datetime.now()}, context=context)

    def case_cancel(self, cr, uid, ids, context=None):
        """ Cancels case """
        return self.case_set(cr, uid, ids, 'cancel', {'active': True}, context=context)

    def case_pending(self, cr, uid, ids, context=None):
        """ Sets case as pending """
        return self.case_set(cr, uid, ids, 'pending', {'active': True}, context=context)

    def case_reset(self, cr, uid, ids, context=None):
        """ Resets case as draft """
        return self.case_set(cr, uid, ids, 'draft', {'active': True}, context=context)

    def case_set(self, cr, uid, ids, state_name, update_values=None, context=None):
        """ Generic method for setting case. This methods wraps the update
            of the record, as well as call to _action and browse_record
            case setting to fill the cache.

            :params: state_name: the new value of the state, such as
                     'draft' or 'close'.
            :params: update_values: values that will be added with the state
                     update when writing values to the record.
        """
        cases = self.browse(cr, uid, ids, context=context)
        cases[0].state # fill browse record cache, for _action having old and new values
        if update_values is None:
            update_values = {}
        update_values['state'] = state_name
        return self.write(cr, uid, ids, update_values, context=context)
    
    # ******************************
    # Notifications
    # ******************************
    
    def case_get_note_msg_prefix(self, cr, uid, id, context=None):
        return ''

    def case_open_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s has been <b>opened</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_post(cr, uid, [id], body=msg, context=context)
        return True

    def case_escalate_send_note(self, cr, uid, ids, new_section=None, context=None):
        for id in ids:
            if new_section:
                msg = '%s has been <b>escalated</b> to <b>%s</b>.' % (self.case_get_note_msg_prefix(cr, uid, id, context=context), new_section.name)
            else:
                msg = '%s has been <b>escalated</b>.' % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_post(cr, uid, [id], body=msg, context=context)
        return True

    def case_close_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s has been <b>closed</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_post(cr, uid, [id], body=msg, context=context)
        return True

    def case_cancel_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s has been <b>canceled</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_post(cr, uid, [id], body=msg, context=context)
        return True

    def case_pending_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s is now <b>pending</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_post(cr, uid, [id], body=msg, context=context)
        return True

    def case_reset_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s has been <b>renewed</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_post(cr, uid, [id], body=msg, context=context)
        return True
