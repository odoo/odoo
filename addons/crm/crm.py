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
from datetime import datetime
from datetime import timedelta
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

    def _get_default_partner_address(self, cr, uid, context):
        """Gives id of default address for current user
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        if not context.get('portal', False):
            return False
        return self.pool.get('res.users').browse(cr, uid, uid, context).address_id.id

    def _get_default_partner(self, cr, uid, context):
        """Gives id of partner for current user
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        if not context.get('portal', False):
            return False
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
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
    
    def _get_default_email(self, cr, uid, context):
        """Gives default email address for current user
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        if not context.get('portal', False):
            return False
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        if not user.address_id:
            return False
        return user.address_id.email

    def _get_default_user(self, cr, uid, context):
        """Gives current user id
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        if context.get('portal', False):
            return False
        return uid

    def _get_section(self, cr, uid, context):
        """Gives section id for current User
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        """
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.context_section_id.id or False

    def stage_next(self, cr, uid, ids, context=None):
        """This function computes next stage for case from its current stage
             using available stage for that case type
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values"""
        if not context:
            context = {}
        s = self.get_stage_dict(cr, uid, ids, context=context)
        section = self._name
        stage = False
        for case in self.browse(cr, uid, ids, context):
            if section in s:
                st =  not context.get('force_domain', False) and case.stage_id.id  or False
                if st in s[section]:
                    data = {'stage_id': s[section][st]}
                    stage = s[section][st]
                    self.write(cr, uid, [case.id], data)
        return stage

    def get_stage_dict(self, cr, uid, ids, context=None):
        """This function gives dictionary for stage according to stage levels
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values"""
        if not context:
            context = {}
        stage_obj = self.pool.get('crm.case.stage')
        res = self.read(cr, uid, ids, ['section_id', 'stage_id'], context)[0]
        section_id = res['section_id'] and res['section_id'][0] or False
        stage_id = res['stage_id'] and res['stage_id'][0] or False

        # We select either the stages in the same section as the current stage
        # if it a stage that does not have a section, or the stages of the 
        # current section of the case
        if stage_id:
            stage_record = stage_obj.browse(cr, uid, stage_id)
            if not stage_record.section_id:
                section_id = False # only select stages without section

        domain = [('object_id.model', '=', self._name), ('section_id', '=', section_id)]
        if 'force_domain' in context and context['force_domain']:
            domain += context['force_domain']
        sid = stage_obj.search(cr, uid, domain, context=context)
        s = {}
        previous = {}
        section = self._name

        for stage in stage_obj.browse(cr, uid, sid, context=context):
            s.setdefault(section, {})
            s[section][previous.get(section, False)] = stage.id
            previous[section] = stage.id
        return s

    def stage_previous(self, cr, uid, ids, context=None):
        """This function computes previous stage for case from its current stage
             using available stage for that case type
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values"""
        if not context:
            context = {}

        s = self.get_stage_dict(cr, uid, ids, context=context)
        section = self._name
        stage_pool = self.pool.get('crm.case.stage')
        for case in self.browse(cr, uid, ids, context):
            if section in s:
                st = not context.get('force_domain', False) and case.stage_id.id or False
                s[section] = dict([(v, k) for (k, v) in s[section].iteritems()])
                if st in s[section]:
                    data = {'stage_id': s[section][st]}
                    if s[section][st]:
                        stage = stage_pool.browse(cr, uid, s[section][st], context=context)
                        if stage.on_change:
                            data.update({'probability': stage.probability})
                    self.write(cr, uid, [case.id], data)
        return True

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
        return {'value': {'email_from': address.email, 'phone': address.phone}}

    def _history(self, cr, uid, cases, keyword, history=False, subject=None, email=False, details=None, email_from=False, message_id=False, attach=[], context={}):
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
            message = "The " + self._description + " '" + case.name + "' has been Cancelled."
            #TODO: Need to differentiate lead and opportunity
#            if hasattr(case, 'type'):
#                #TO CHECK: hasattr gives warning for other crm objects that don't have field 'type'
#                message = "The " + (case.type or 'Case').title() + " '" + case.name + "' has been Cancelled."
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

    def remind_partner(self, cr, uid, ids, context={}, attach=False):

        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Remind Partner's IDs
        @param context: A standard dictionary for contextual values

        """
        return self.remind_user(cr, uid, ids, context, attach,
                destination=False)

    def remind_user(self, cr, uid, ids, context={}, attach=False,destination=True):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Remind user's IDs
        @param context: A standard dictionary for contextual values

        """
        for case in self.browse(cr, uid, ids):
            if not case.section_id.reply_to:
                raise osv.except_osv(_('Error!'), ("Reply To is not specified in the sales team"))
            if not case.email_from:
                raise osv.except_osv(_('Error!'), ("Partner Email is not specified in Case"))
            if case.section_id.reply_to and case.email_from:
                src = case.email_from
                dest = case.section_id.reply_to
                body = case.description or ""
                if case.message_ids:
                    body = case.message_ids[0].description or ""
                if not destination:
                    src, dest = dest, src
                    if body and case.user_id.signature:
                        if body:
                            body += '\n\n%s' % (case.user_id.signature)
                        else:
                            body = '\n\n%s' % (case.user_id.signature)

                body = self.format_body(body)

                attach_to_send = None

                if attach:
                    attach_ids = self.pool.get('ir.attachment').search(cr, uid, [('res_model', '=', self._name), ('res_id', '=', case.id)])
                    attach_to_send = self.pool.get('ir.attachment').read(cr, uid, attach_ids, ['datas_fname','datas'])
                    attach_to_send = map(lambda x: (x['datas_fname'], base64.decodestring(x['datas'])), attach_to_send)

                # Send an email
                subject = "Reminder: [%s] %s" % (str(case.id), case.name, )
                flag = tools.email_send(
                    src,
                    [dest],
                    subject, 
                    body,
                    reply_to=case.section_id.reply_to,
                    openobject_id=str(case.id),
                    attach=attach_to_send
                )
                self._history(cr, uid, [case], _('Send'), history=True, subject=subject, email=dest, details=body, email_from=src)
        return True

    def _check(self, cr, uid, ids=False, context={}):
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
        cases = self.browse(cr, uid, ids2, context)
        return self._action(cr, uid, cases, False, context=context)

    def _action(self, cr, uid, cases, state_to, scrit=None, context={}):
        if not context:
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

class crm_case_section(osv.osv):
    """Sales Team"""

    _name = "crm.case.section"
    _description = "Sales Teams"
    _order = "name"

    _columns = {
        'name': fields.char('Sales Team', size=64, required=True, translate=True),
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
        'resource_calendar_id': fields.many2one('resource.calendar', "Resource's Calendar"),
        'note': fields.text('Description'),
        'working_hours': fields.float('Working Hours', digits=(16,2 )),
    }

    _defaults = {
        'active': lambda *a: 1,
        'allow_unlink': lambda *a: 1,
    }

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code of the sales team must be unique !')
    ]

    def _check_recursion(self, cr, uid, ids):

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
        if not context:
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
    _description = "Category of case"

    _columns = {
        'name': fields.char('Case Category Name', size=64, required=True, translate=True),
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


class crm_case_resource_type(osv.osv):
    """ Resource Type of case """

    _name = "crm.case.resource.type"
    _description = "Resource Type of case"
    _rec_name = "name"

    _columns = {
        'name': fields.char('Resource Type', size=64, required=True, translate=True),
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

crm_case_resource_type()


class crm_case_stage(osv.osv):
    """ Stage of case """

    _name = "crm.case.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _order = "sequence"

    _columns = {
        'name': fields.char('Stage Name', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of case stages."),
        'object_id': fields.many2one('ir.model', 'Object Name'),
        'probability': fields.float('Probability (%)', required=True),
        'on_change': fields.boolean('Change Probability Automatically', \
                         help="Change Probability on next and previous stages."),
        'requirements': fields.text('Requirements')
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
        'sequence': lambda *args: 1,
        'probability': lambda *args: 0.0,
        'object_id' : _find_object_id
    }

crm_case_stage()

def _links_get(self, cr, uid, context=None):
    """Gets links value for reference field
    @param self: The object pointer
    @param cr: the current row, from the database cursor,
    @param uid: the current user’s ID for security checks,
    @param context: A standard dictionary for contextual values
    """
    if not context:
        context = {}
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
users()


class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }
res_partner()


class crm_case_section_custom(osv.osv):
    _name = "crm.case.section.custom"
    _description = 'Custom CRM Case Section' 

    _columns = {
        'name': fields.char('Case Section',size=64, required=True, translate=True),
        'code': fields.char('Section Code',size=8),
        'active': fields.boolean('Active'),
        'allow_unlink': fields.boolean('Allow Delete', help="Allows to delete non draft cases"),
        'sequence': fields.integer('Sequence'),
        'user_id': fields.many2one('res.users', 'Responsible User'),
        'reply_to': fields.char('Reply-To', size=64, help="The email address put in the 'Reply-To' of all emails sent by OpenERP about cases in this section"),
        'parent_id': fields.many2one('crm.case.section.custom', 'Parent Section'), 
        'note': fields.text('Notes'),
    }

    _defaults = {
        'active': 1,
        'allow_unlink': 1,
    }

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code of the section must be unique !')
    ]

    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('SELECT DISTINCT parent_id FROM crm_case_section_custom '\
                       'WHERE id IN %s',
                       (tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True
    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive sections.', ['parent_id'])
    ]

crm_case_section_custom()


class crm_case_custom(osv.osv, crm_case):
    _name = 'crm.case.custom'
    _inherit = 'mailgate.thread'
    _description = "Custom CRM Case"

    _columns = {
            'id': fields.integer('ID', readonly=True),
            'name': fields.char('Name',size=64,required=True),
            'priority': fields.selection(AVAILABLE_PRIORITIES, 'Priority'),
            'active': fields.boolean('Active'),
            'description': fields.text('Description'),
            'section_id': fields.many2one('crm.case.section.custom', 'Section', required=True, select=True),
            'probability': fields.float('Probability (%)'),
            'email_from': fields.char('Partner Email', size=128),
            'email_cc': fields.char('CC', size=252),
            'partner_id': fields.many2one('res.partner', 'Partner'),
            'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', domain="[('partner_id','=',partner_id)]"),
            'date': fields.datetime('Date'),
            'create_date': fields.datetime('Created' ,readonly=True),
            'date_deadline': fields.datetime('Deadline'),
            'date_closed': fields.datetime('Closed', readonly=True),
            'user_id': fields.many2one('res.users', 'Responsible'),
            'state': fields.selection(AVAILABLE_STATES, 'Status', size=16, readonly=True),
            'ref' : fields.reference('Reference', selection=_links_get, size=128),
            'date_action_last': fields.datetime('Last Action', readonly=1),
            'date_action_next': fields.datetime('Next Action', readonly=1),
        }

    _defaults = {
        'active': 1,
        'state': 'draft',
        'priority': AVAILABLE_PRIORITIES[2][0],
        'date': time.strftime('%Y-%m-%d %H:%M:%S'),
    }

crm_case_custom()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
