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

import time
import base64
import tools

from osv import fields
from osv import osv
from tools.translate import _

MAX_LEVEL = 15
AVAILABLE_STATES = [
    ('draft', 'Draft'),
    ('open', 'Open'),
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending', 'Pending'),
]

AVAILABLE_PRIORITIES = [
    ('1', 'Highest'),
    ('2', 'High'),
    ('3', 'Normal'),
    ('4', 'Low'),
    ('5', 'Lowest'),
]

class crm_case(object):
    """A simple python class to be used for common functions """

    def _find_lost_stage(self, cr, uid, type, section_id):
        return self._find_percent_stage(cr, uid, 0.0, type, section_id)

    def _find_won_stage(self, cr, uid, type, section_id):
        return self._find_percent_stage(cr, uid, 100.0, type, section_id)

    def _find_percent_stage(self, cr, uid, percent, type, section_id):
        """
            Return the first stage with a probability == percent
        """
        stage_pool = self.pool.get('crm.case.stage')
        if section_id :
            ids = stage_pool.search(cr, uid, [("probability", '=', percent), ("type", 'like', type), ("section_ids", 'in', [section_id])])
        else :
            ids = stage_pool.search(cr, uid, [("probability", '=', percent), ("type", 'like', type)])

        if ids:
            return ids[0]
        return False


    def _find_first_stage(self, cr, uid, type, section_id):
        """
            return the first stage that has a sequence number equal or higher than sequence
        """
        stage_pool = self.pool.get('crm.case.stage')
        if section_id :
            ids = stage_pool.search(cr, uid, [("sequence", '>', 0), ("type", 'like', type), ("section_ids", 'in', [section_id])])
        else :
            ids = stage_pool.search(cr, uid, [("sequence", '>', 0), ("type", 'like', type)])

        if ids:
            stages = stage_pool.browse(cr, uid, ids)
            stage_min = stages[0]
            for stage in stages:
                if stage_min.sequence > stage.sequence:
                    stage_min = stage
            return stage_min.id
        else :
            return False

    def onchange_stage_id(self, cr, uid, ids, stage_id, context={}):

        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of stage’s IDs
            @stage_id: change state id on run time """

        if not stage_id:
            return {'value':{}}

        stage = self.pool.get('crm.case.stage').browse(cr, uid, stage_id, context)

        if not stage.on_change:
            return {'value':{}}
        return {'value':{'probability': stage.probability}}

    def _get_default_partner_address(self, cr, uid, context=None):

        """Gives id of default address for current user
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        if context is None:
            context = {}
        if not context.get('portal', False):
            return False
        return self.pool.get('res.users').browse(cr, uid, uid, context).address_id.id

    def _get_default_partner(self, cr, uid, context=None):
        """Gives id of partner for current user
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        if context is None:
            context = {}
        if not context.get('portal', False):
            return False
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if not user.address_id:
            return False
        return user.address_id.partner_id.id

    def copy(self, cr, uid, id, default=None, context=None):
        """
        Overrides orm copy method.
        @param self: the object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param id: Id of mailgate thread
        @param default: Dictionary of default values for copy.
        @param context: A standard dictionary for contextual values
        """
        if context is None:
            context = {}
        if default is None:
            default = {}

        default.update({
                    'message_ids': [],
                })
        if hasattr(self, '_columns'):
            if self._columns.get('date_closed'):
                default.update({
                    'date_closed': False,
                })
            if self._columns.get('date_open'):
                default.update({
                    'date_open': False
                })
        return super(osv.osv, self).copy(cr, uid, id, default, context=context)

    def _get_default_email(self, cr, uid, context=None):
        """Gives default email address for current user
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        if not context.get('portal', False):
            return False
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if not user.address_id:
            return False
        return user.address_id.email

    def _get_default_user(self, cr, uid, context=None):
        """Gives current user id
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        if context and context.get('portal', False):
            return False
        return uid

    def _get_section(self, cr, uid, context=None):
        """Gives section id for current User
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.context_section_id.id or False

    def _find_next_stage(self, cr, uid, stage_list, index, current_seq, stage_pool, context=None):
        if index + 1 == len(stage_list):
            return False
        next_stage_id = stage_list[index + 1]
        next_stage = stage_pool.browse(cr, uid, next_stage_id, context=context)
        if not next_stage:
            return False
        next_seq = next_stage.sequence
        if not current_seq :
            current_seq = 0

        if (abs(next_seq - current_seq)) >= 1:
            return next_stage
        else :
            return self._find_next_stage(cr, uid, stage_list, index + 1, current_seq, stage_pool)

    def stage_change(self, cr, uid, ids, context=None, order='sequence'):
        if context is None:
            context = {}
        stage_pool = self.pool.get('crm.case.stage')
        stage_type = context and context.get('stage_type','')
        current_seq = False
        next_stage_id = False

        for case in self.browse(cr, uid, ids, context=context):
            next_stage = False
            value = {}
            if case.section_id.id :
                domain = [('type', '=', stage_type),('section_ids', '=', case.section_id.id)]
            else :
                domain = [('type', '=', stage_type)]


            stages = stage_pool.search(cr, uid, domain, order=order)
            current_seq = case.stage_id.sequence
            index = -1
            if case.stage_id and case.stage_id.id in stages:
                index = stages.index(case.stage_id.id)

            next_stage = self._find_next_stage(cr, uid, stages, index, current_seq, stage_pool, context=context)

            if next_stage:
                next_stage_id = next_stage.id
                value.update({'stage_id': next_stage.id})
                if next_stage.on_change:
                    value.update({'probability': next_stage.probability})
            self.write(cr, uid, [case.id], value, context=context)


        return next_stage_id #FIXME should return a list of all id


    def stage_next(self, cr, uid, ids, context=None):
        """This function computes next stage for case from its current stage
             using available stage for that case type
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values"""

        return self.stage_change(cr, uid, ids, context=context, order='sequence')

    def stage_previous(self, cr, uid, ids, context=None):
        """This function computes previous stage for case from its current stage
             using available stage for that case type
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values"""
        return self.stage_change(cr, uid, ids, context=context, order='sequence desc')

    def onchange_partner_id(self, cr, uid, ids, part, email=False):
        """This function returns value of partner address based on partner
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param part: Partner's id
        @email: Partner's email ID
        """
        if not part:
            return {'value': {'partner_address_id': False,
                            'email_from': False,
                            'phone': False
                            }}
        addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['contact'])
        data = {'partner_address_id': addr['contact']}
        data.update(self.onchange_partner_address_id(cr, uid, ids, addr['contact'])['value'])
        return {'value': data}

    def onchange_partner_address_id(self, cr, uid, ids, add, email=False):
        """This function returns value of partner email based on Partner Address
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param add: Id of Partner's address
        @email: Partner's email ID
        """
        if not add:
            return {'value': {'email_from': False}}
        address = self.pool.get('res.partner.address').browse(cr, uid, add)
        if address.email:
            return {'value': {'email_from': address.email, 'phone': address.phone}}
        else:
            return {'value': {'phone': address.phone}}

    def _history(self, cr, uid, cases, keyword, history=False, subject=None, email=False, details=None, email_from=False, message_id=False, attach=[], context=None):
        mailgate_pool = self.pool.get('mailgate.thread')
        return mailgate_pool.history(cr, uid, cases, keyword, history=history,\
                                       subject=subject, email=email, \
                                       details=details, email_from=email_from,\
                                       message_id=message_id, attach=attach, \
                                       context=context)

    def case_open(self, cr, uid, ids, *args):
        """Opens Case
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """

        cases = self.browse(cr, uid, ids)
        self._history(cr, uid, cases, _('Open'))
        for case in cases:
            data = {'state': 'open', 'active': True}
            if not case.user_id:
                data['user_id'] = uid
            self.write(cr, uid, case.id, data)


        self._action(cr, uid, cases, 'open')
        return True

    def case_close(self, cr, uid, ids, *args):
        """Closes Case
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self._history(cr, uid, cases, _('Close'))
        self.write(cr, uid, ids, {'state': 'done',
                                  'date_closed': time.strftime('%Y-%m-%d %H:%M:%S'),
                                  })
        #
        # We use the cache of cases to keep the old case state
        #
        self._action(cr, uid, cases, 'done')
        return True

    def case_escalate(self, cr, uid, ids, *args):
        """Escalates case to top level
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        cases = self.browse(cr, uid, ids)
        for case in cases:
            data = {'active': True}

            if case.section_id.parent_id:
                data['section_id'] = case.section_id.parent_id.id
                if case.section_id.parent_id.change_responsible:
                    if case.section_id.parent_id.user_id:
                        data['user_id'] = case.section_id.parent_id.user_id.id
            else:
                raise osv.except_osv(_('Error !'), _('You can not escalate, You are already at the top level regarding your sales-team category.'))
            self.write(cr, uid, [case.id], data)
        cases = self.browse(cr, uid, ids)
        self._history(cr, uid, cases, _('Escalate'))
        self._action(cr, uid, cases, 'escalate')
        return True

    def case_cancel(self, cr, uid, ids, *args):
        """Cancels Case
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self._history(cr, uid, cases, _('Cancel'))
        self.write(cr, uid, ids, {'state': 'cancel',
                                  'active': True})
        self._action(cr, uid, cases, 'cancel')
        for case in cases:
            message = _("The case '%s' has been cancelled.") % (case.name,)
            self.log(cr, uid, case.id, message)
        return True

    def case_pending(self, cr, uid, ids, *args):
        """Marks case as pending
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self._history(cr, uid, cases, _('Pending'))
        self.write(cr, uid, ids, {'state': 'pending', 'active': True})
        self._action(cr, uid, cases, 'pending')
        return True

    def case_reset(self, cr, uid, ids, *args):
        """Resets case as draft
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self._history(cr, uid, cases, _('Draft'))
        self.write(cr, uid, ids, {'state': 'draft', 'active': True})
        self._action(cr, uid, cases, 'draft')
        return True

    def remind_partner(self, cr, uid, ids, context=None, attach=False):

        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Remind Partner's IDs
        @param context: A standard dictionary for contextual values

        """

        return self.remind_user(cr, uid, ids, context, attach,
                destination=False)

    def remind_user(self, cr, uid, ids, context=None, attach=False, destination=True):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's IDs to remind
        @param context: A standard dictionary for contextual values
        """
        for case in self.browse(cr, uid, ids, context=context):
            if not destination and not case.email_from:
                raise osv.except_osv(_('Error!'), ("Partner Email is not specified in Case"))
            if not case.user_id.user_email:
               raise osv.except_osv(_('Error!'), ("User Email is not specified in Case"))
            
            if destination and case.section_id.user_id:
                case_email = case.section_id.user_id.user_email
            else:
                case_email = case.user_id.user_email

            src = case_email
            dest = case.user_id
            body = case.description or ""
            if case.message_ids:
                body = case.message_ids[0].description or ""
            if not destination:
                src, dest = dest, case.email_from
                if body and case.user_id.signature:
                    if body:
                        body += '\n\n%s' % (case.user_id.signature)
                    else:
                        body = '\n\n%s' % (case.user_id.signature)

            body = self.format_body(body)

            attach_to_send = None

            if attach:
                attach_ids = self.pool.get('ir.attachment').search(cr, uid, [('res_model', '=', self._name), ('res_id', '=', case.id)])
                attach_to_send = self.pool.get('ir.attachment').read(cr, uid, attach_ids, ['datas_fname', 'datas'])
                attach_to_send = map(lambda x: (x['datas_fname'], base64.decodestring(x['datas'])), attach_to_send)

                # Send an email
            subject = "Reminder: [%s] %s" % (str(case.id), case.name,)
            tools.email_send(
                src,
                [dest],
                subject,
                body,
                reply_to=case.section_id.reply_to or '',
                openobject_id=str(case.id),
                attach=attach_to_send
            )
            self._history(cr, uid, [case], _('Send'), history=True, subject=subject, email=dest, details=body, email_from=src)

        return True

    def _check(self, cr, uid, ids=False, context=None):
        """
        Function called by the scheduler to process cases for date actions
        Only works on not done and cancelled cases

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        cr.execute('select * from crm_case \
                where (date_action_last<%s or date_action_last is null) \
                and (date_action_next<=%s or date_action_next is null) \
                and state not in (\'cancel\',\'done\')',
                (time.strftime("%Y-%m-%d %H:%M:%S"),
                    time.strftime('%Y-%m-%d %H:%M:%S')))

        ids2 = map(lambda x: x[0], cr.fetchall() or [])
        cases = self.browse(cr, uid, ids2, context=context)
        return self._action(cr, uid, cases, False, context=context)

    def _action(self, cr, uid, cases, state_to, scrit=None, context=None):
        if context is None:
            context = {}
        context['state_to'] = state_to
        rule_obj = self.pool.get('base.action.rule')
        model_obj = self.pool.get('ir.model')
        model_ids = model_obj.search(cr, uid, [('model','=',self._name)])
        rule_ids = rule_obj.search(cr, uid, [('model_id','=',model_ids[0])])
        return rule_obj._action(cr, uid, rule_ids, cases, scrit=scrit, context=context)

    def format_body(self, body):
        return self.pool.get('base.action.rule').format_body(body)

    def format_mail(self, obj, body):
        return self.pool.get('base.action.rule').format_mail(obj, body)

    def message_followers(self, cr, uid, ids, context=None):
        """ Get a list of emails of the people following this thread
        """
        res = {}
        for case in self.browse(cr, uid, ids, context=context):
            l=[]
            if case.email_cc:
                l.append(case.email_cc)
            if case.user_id and case.user_id.user_email:
                l.append(case.user_id.user_email)
            res[case.id] = l
        return res


class crm_case_stage(osv.osv):
    """ Stage of case """

    _name = "crm.case.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _order = "sequence"



    def _get_type_value(self, cr, user, context):
        return [('lead','Lead'),('opportunity','Opportunity')]


    _columns = {
        'name': fields.char('Stage Name', size=64, required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of case stages."),
        'probability': fields.float('Probability (%)', required=True, help="This percentage depicts the default/average probability of the Case for this stage to be a success"),
        'on_change': fields.boolean('Change Probability Automatically', \
                         help="Change Probability on next and previous stages."),
        'requirements': fields.text('Requirements'),
        'type': fields.selection(_get_type_value, 'Type'),
    }


    def _find_stage_type(self, cr, uid, context=None):
        """Finds type of stage according to object.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        type = context and context.get('type', '') or ''
        return type

    _defaults = {
        'sequence': lambda *args: 1,
        'probability': lambda *args: 0.0,
        'type': _find_stage_type,
    }

crm_case_stage()


class crm_case_section(osv.osv):
    """Sales Team"""

    _name = "crm.case.section"
    _description = "Sales Teams"
    _order = "complete_name"

    def get_full_name(self, cr, uid, ids, field_name, arg, context=None):
        return  dict(self.name_get(cr, uid, ids, context=context))

    _columns = {
        'name': fields.char('Sales Team', size=64, required=True, translate=True),
        'complete_name': fields.function(get_full_name, method=True, type='char', size=256, readonly=True, store=True),
        'code': fields.char('Code', size=8),
        'active': fields.boolean('Active', help="If the active field is set to "\
                        "true, it will allow you to hide the sales team without removing it."),
        'allow_unlink': fields.boolean('Allow Delete', help="Allows to delete non draft cases"),
        'change_responsible': fields.boolean('Change Responsible', help="Thick this box if you want that on escalation, the responsible of this sale team automatically becomes responsible of the lead/opportunity escaladed"),
        'user_id': fields.many2one('res.users', 'Responsible User'),
        'member_ids':fields.many2many('res.users', 'sale_member_rel', 'section_id', 'member_id', 'Team Members'),
        'reply_to': fields.char('Reply-To', size=64, help="The email address put in the 'Reply-To' of all emails sent by OpenERP about cases in this sales team"),
        'parent_id': fields.many2one('crm.case.section', 'Parent Team'),
        'child_ids': fields.one2many('crm.case.section', 'parent_id', 'Child Teams'),
        'resource_calendar_id': fields.many2one('resource.calendar', "Working Time"),
        'note': fields.text('Description'),
        'working_hours': fields.float('Working Hours', digits=(16,2 )),
        'stage_ids': fields.many2many('crm.case.stage', 'section_stage_rel', 'section_id', 'stage_id', 'Stages'),
    }

    _defaults = {
        'active': lambda *a: 1,
        'allow_unlink': lambda *a: 1,
    }

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code of the sales team must be unique !')
    ]

    def _check_recursion(self, cr, uid, ids, context=None):

        """
        Checks for recursion level for sales team
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Sales team ids
        """
        level = 100

        while len(ids):
            cr.execute('select distinct parent_id from crm_case_section where id IN %s', (tuple(ids),))
            ids = filter(None, map(lambda x: x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1

        return True

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive Sales team.', ['parent_id'])
    ]

    def name_get(self, cr, uid, ids, context=None):
        """Overrides orm name_get method
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of sales team ids
        """
        if context is None:
            context = {}

        res = []
        if not ids:
            return res
        reads = self.read(cr, uid, ids, ['name', 'parent_id'], context)

        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1] + ' / ' + name
            res.append((record['id'], name))
        return res

crm_case_section()


class crm_case_categ(osv.osv):
    """ Category of Case """
    _name = "crm.case.categ"
    _description = "Category of Case"
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'object_id': fields.many2one('ir.model', 'Object Name'),
    }

    def _find_object_id(self, cr, uid, context=None):
        """Finds id for case object
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """

        object_id = context and context.get('object_id', False) or False
        ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', object_id)])
        return ids and ids[0]

    _defaults = {
        'object_id' : _find_object_id

    }
crm_case_categ()


class crm_case_stage(osv.osv):
    _inherit = "crm.case.stage"
    _columns = {
        'section_ids':fields.many2many('crm.case.section', 'section_stage_rel', 'stage_id', 'section_id', 'Sections'),
    }

crm_case_stage()


class crm_case_resource_type(osv.osv):
    """ Resource Type of case """
    _name = "crm.case.resource.type"
    _description = "Campaign"
    _rec_name = "name"
    _columns = {
        'name': fields.char('Campaign Name', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }
crm_case_resource_type()


def _links_get(self, cr, uid, context=None):
    """Gets links value for reference field
    @param self: The object pointer
    @param cr: the current row, from the database cursor,
    @param uid: the current user’s ID for security checks,
    @param context: A standard dictionary for contextual values
    """
    obj = self.pool.get('res.request.link')
    ids = obj.search(cr, uid, [])
    res = obj.read(cr, uid, ids, ['object', 'name'], context)
    return [(r['object'], r['name']) for r in res]

class users(osv.osv):
    _inherit = 'res.users'
    _description = "Users"
    _columns = {
        'context_section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }

    def create(self, cr, uid, vals, context=None):
        res = super(users, self).create(cr, uid, vals, context=context)
        section_obj=self.pool.get('crm.case.section')

        if vals.get('context_section_id', False):
            section_obj.write(cr, uid, [vals['context_section_id']], {'member_ids':[(4, res)]}, context)
        return res
users()


class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }
res_partner()

