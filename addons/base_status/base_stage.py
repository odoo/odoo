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

from osv import fields, osv
from tools.translate import _

class base_stage(object):
    """ Base utility mixin class for objects willing to manage their stages.
        Object that inherit from this class should inherit from mailgate.thread
        to have access to the mail gateway, as well as Chatter. Objects
        subclassing this class should define the following colums:
        - ``date_open`` (datetime field)
        - ``date_closed`` (datetime field)
        - ``user_id`` (many2one to res.users)
        - ``partner_id`` (many2one to res.partner)
        - ``stage_id`` (many2one to a stage definition model)
        - ``state`` (selection field, related to the stage_id.state)
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

    def _get_default_section_id(self, cr, uid, context=None):
        """ Gives default section """
        return False

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        return self.stage_find(cr, uid, [], None, [('state', '=', 'draft')], context=context)

    def stage_find(self, cr, uid, cases, section_id, domain=[], order='sequence', context=None):
        """ Find stage, with a given (optional) domain on the search,
            ordered by the order parameter. If several stages match the
            search criterions, the first one will be returned, according
            to the requested search order.
            This method is meant to be overriden by subclasses. That way
            specific behaviors can be achieved for every class inheriting
            from base_stage.

            :param cases: browse_record of cases
            :param section_id: section limitating the search, given for
                               a generic search (for example default search).
                               A section models concepts such as Sales team
                               (for CRM), ou departments (for HR).
            :param domain: a domain on the search of stages
            :param order: order of the search
        """
        return False

    def stage_set_with_state_name(self, cr, uid, cases, state_name, context=None):
        """ Set a new stage, with a state_name instead of a stage_id
            :param cases: browse_record of cases
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cr, uid, cases, context=context)
        for case in cases:
            stage_id = self.stage_find(cr, uid, [case], None, [('state', '=', state_name)], context=context)
            if stage_id:
                self.stage_set(cr, uid, [case.id], stage_id, context=context)
        return True

    def stage_set(self, cr, uid, ids, stage_id, context=None):
        """ Set the new stage. This methods is the right method to call
            when changing states. It also checks whether an onchange is
            defined, and execute it.
        """
        value = {}
        if hasattr(self, 'onchange_stage_id'):
            value = self.onchange_stage_id(cr, uid, ids, stage_id, context=context)['value']
        value['stage_id'] = stage_id
        self.stage_set_send_note(cr, uid, ids, stage_id, context=context)
        return self.write(cr, uid, ids, value, context=context)

    def stage_change(self, cr, uid, ids, op, order, context=None):
        """ Change the stage and take the next one, based on a condition
            writen for the 'sequence' field and an operator. This methods
            checks whether the case has a current stage, and takes its
            sequence. Otherwise, a default 0 sequence is chosen and this
            method will therefore choose the first available stage.
            For example if op is '>' and current stage has a sequence of
            10, this will call stage_find, with [('sequence', '>', '10')].
        """
        for case in self.browse(cr, uid, ids, context=context):
            seq = 0
            if case.stage_id:
                seq = case.stage_id.sequence or 0
            section_id = None
            next_stage_id = self.stage_find(cr, uid, [case], None, [('sequence', op, seq)],order, context=context)
            if next_stage_id:
                return self.stage_set(cr, uid, [case.id], next_stage_id, context=context)
        return False

    def stage_next(self, cr, uid, ids, context=None):
        """ This function computes next stage for case from its current stage
            using available stage for that case type
        """
        return self.stage_change(cr, uid, ids, '>','sequence', context)

    def stage_previous(self, cr, uid, ids, context=None):
        """ This function computes previous stage for case from its current
            stage using available stage for that case type
        """
        return self.stage_change(cr, uid, ids, '<', 'sequence desc', context)

    def copy(self, cr, uid, id, default=None, context=None):
        """ Overrides orm copy method to avoid copying messages,
            as well as date_closed and date_open columns if they
            exist."""
        if default is None:
            default = {}

        if hasattr(self, '_columns'):
            if self._columns.get('date_closed'):
                default.update({ 'date_closed': False, })
            if self._columns.get('date_open'):
                default.update({ 'date_open': False })
        return super(base_stage, self).copy(cr, uid, id, default, context=context)

    def case_escalate(self, cr, uid, ids, context=None):
        """ Escalates case to parent level """
        cases = self.browse(cr, uid, ids, context=context)
        cases[0].state # fill browse record cache, for _action having old and new values
        for case in cases:
            data = {'active': True}
            if case.section_id.parent_id:
                data['section_id'] = case.section_id.parent_id.id
                if case.section_id.parent_id.change_responsible:
                    if case.section_id.parent_id.user_id:
                        data['user_id'] = case.section_id.parent_id.user_id.id
            else:
                raise osv.except_osv(_('Error!'), _("You are already at the top level of your sales-team category.\nTherefore you cannot escalate furthermore."))
            self.write(cr, uid, [case.id], data, context=context)
            case.case_escalate_send_note(case.section_id.parent_id, context=context)
        cases = self.browse(cr, uid, ids, context=context)
        self._action(cr, uid, cases, 'escalate', context=context)
        return True

    def case_open(self, cr, uid, ids, context=None):
        """ Opens case """
        cases = self.browse(cr, uid, ids, context=context)
        for case in cases:
            data = {'active': True}
            if case.stage_id and case.stage_id.state == 'draft':
                data['date_open'] = fields.datetime.now()
            if not case.user_id:
                data['user_id'] = uid
            self.case_set(cr, uid, [case.id], 'open', data, context=context)
            self.case_open_send_note(cr, uid, [case.id], context=context)
        return True

    def case_close(self, cr, uid, ids, context=None):
        """ Closes case """
        self.case_set(cr, uid, ids, 'done', {'active': True, 'date_closed': fields.datetime.now()}, context=context)
        self.case_close_send_note(cr, uid, ids, context=context)
        return True

    def case_cancel(self, cr, uid, ids, context=None):
        """ Cancels case """
        self.case_set(cr, uid, ids, 'cancel', {'active': True}, context=context)
        self.case_cancel_send_note(cr, uid, ids, context=context)
        return True

    def case_pending(self, cr, uid, ids, context=None):
        """ Set case as pending """
        self.case_set(cr, uid, ids, 'pending', {'active': True}, context=context)
        self.case_pending_send_note(cr, uid, ids, context=context)
        return True

    def case_reset(self, cr, uid, ids, context=None):
        """ Resets case as draft """
        self.case_set(cr, uid, ids, 'draft', {'active': True}, context=context)
        self.case_reset_send_note(cr, uid, ids, context=context)
        return True

    def case_set(self, cr, uid, ids, new_state_name=None, values_to_update=None, new_stage_id=None, context=None):
        """ Generic method for setting case. This methods wraps the update
            of the record, as well as call to _action and browse_record
            case setting to fill the cache.

            :params new_state_name: the new state of the record; this method
                                    will call ``stage_set_with_state_name``
                                    that will find the stage matching the
                                    new state, using the ``stage_find`` method.
            :params new_stage_id: alternatively, you may directly give the
                                  new stage of the record
            :params state_name: the new value of the state, such as
                     'draft' or 'close'.
            :params update_values: values that will be added with the state
                     update when writing values to the record.
        """
        cases = self.browse(cr, uid, ids, context=context)
        cases[0].state # fill browse record cache, for _action having old and new values
        # 1. update the stage
        if new_state_name:
            self.stage_set_with_state_name(cr, uid, cases, new_state_name, context=context)
        elif not (new_stage_id is None):
            self.stage_set(cr, uid, ids, new_stage_id, context=context)
        # 2. update values
        if values_to_update:
            self.write(cr, uid, ids, values_to_update, context=context)
        # 3. call _action for base action rule
        if new_state_name:
            self._action(cr, uid, cases, new_state_name, context=context)
        elif not (new_stage_id is None):
            new_state_name = self.read(cr, uid, ids, ['state'], context=context)[0]['state']
        self._action(cr, uid, cases, new_state_name, context=context)
        return True

    def _action(self, cr, uid, cases, state_to, scrit=None, context=None):
        if context is None:
            context = {}
        context['state_to'] = state_to
        rule_obj = self.pool.get('base.action.rule')
        if not rule_obj:
            return True
        model_obj = self.pool.get('ir.model')
        model_ids = model_obj.search(cr, uid, [('model','=',self._name)], context=context)
        rule_ids = rule_obj.search(cr, uid, [('model_id','=',model_ids[0])], context=context)
        return rule_obj._action(cr, uid, rule_ids, cases, scrit=scrit, context=context)

    def remind_partner(self, cr, uid, ids, context=None, attach=False):
        return self.remind_user(cr, uid, ids, context, attach,
                destination=False)

    def remind_user(self, cr, uid, ids, context=None, attach=False, destination=True):
        mail_message = self.pool.get('mail.message')
        for case in self.browse(cr, uid, ids, context=context):
            if not destination and not case.email_from:
                return False
            if not case.user_id.email:
                return False
            if destination and case.section_id.user_id:
                case_email = case.section_id.user_id.email
            else:
                case_email = case.user_id.email

            src = case_email
            dest = case.user_id.email or ""
            body = case.description or ""
            for message in case.message_ids:
                if message.email_from and message.body:
                    body = message.body
                    break

            if not destination:
                src, dest = dest, case.email_from
                if body and case.user_id.signature:
                    if body:
                        body += '\n\n%s' % (case.user_id.signature)
                    else:
                        body = '\n\n%s' % (case.user_id.signature)

            body = self.format_body(body)

            attach_to_send = {}

            if attach:
                attach_ids = self.pool.get('ir.attachment').search(cr, uid, [('res_model', '=', self._name), ('res_id', '=', case.id)])
                attach_to_send = self.pool.get('ir.attachment').read(cr, uid, attach_ids, ['datas_fname', 'datas'])
                attach_to_send = dict(map(lambda x: (x['datas_fname'], base64.decodestring(x['datas'])), attach_to_send))

            # Send an email
            subject = "Reminder: [%s] %s" % (str(case.id), case.name, )
            mail_message.schedule_with_attach(cr, uid,
                src,
                [dest],
                subject,
                body,
                model=self._name,
                reply_to=case.section_id.reply_to,
                res_id=case.id,
                attachments=attach_to_send,
                context=context
            )
        return True

    def _check(self, cr, uid, ids=False, context=None):
        """ Function called by the scheduler to process cases for date actions.
            Must be overriden by inheriting classes.
        """
        return True

    def format_body(self, body):
        return self.pool.get('base.action.rule').format_body(body)

    def format_mail(self, obj, body):
        return self.pool.get('base.action.rule').format_mail(obj, body)

    def message_thread_followers(self, cr, uid, ids, context=None):
        res = {}
        for case in self.browse(cr, uid, ids, context=context):
            l=[]
            if case.email_cc:
                l.append(case.email_cc)
            if case.user_id and case.user_id.email:
                l.append(case.user_id.email)
            res[case.id] = l
        return res

    # ******************************
    # Notifications
    # ******************************

    def case_get_note_msg_prefix(self, cr, uid, id, context=None):
        """ Default prefix for notifications. For example: "%s has been
            <b>closed</b>.". As several models will inherit from base_stage,
            this method returns a void string. Class using base_stage
            will have to override this method to define the prefix they
            want to display.
        """
        return ''

    def stage_set_send_note(self, cr, uid, ids, stage_id, context=None):
        """ Send a notification when the stage changes. This method has
            to be overriden, because each document will have its particular
            behavior and/or stage model (such as project.task.type or
            crm.case.stage).
        """
        return True

    def case_open_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s has been <b>opened</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
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

    def case_escalate_send_note(self, cr, uid, ids, new_section=None, context=None):
        for id in ids:
            if new_section:
                msg = '%s has been <b>escalated</b> to <b>%s</b>.' % (self.case_get_note_msg_prefix(cr, uid, id, context=context), new_section.name)
            else:
                msg = '%s has been <b>escalated</b>.' % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_post(cr, uid, [id], 'System Notification', msg, context=context)
        return True
