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
    ('pending', 'Pending')
]

AVAILABLE_PRIORITIES = [
    ('5', 'Lowest'), 
    ('4', 'Low'), 
    ('3', 'Normal'), 
    ('2', 'High'), 
    ('1', 'Highest')
]

class crm_case_section(osv.osv):
    """Sales Team"""

    _name = "crm.case.section"
    _description = "Sales Teams"
    _order = "name"

    _columns = {
        'name': fields.char('Sales Team', size=64, required=True, translate=True), 
        'code': fields.char('Code', size=8), 
        'active': fields.boolean('Active', help="If the active field is set to \
                        true, it will allow you to hide the sales team without removing it."), 
        'allow_unlink': fields.boolean('Allow Delete', help="Allows to delete non draft cases"), 
        'user_id': fields.many2one('res.users', 'Responsible User'), 
        'reply_to': fields.char('Reply-To', size=64, help="The email address put \
                        in the 'Reply-To' of all emails sent by Open ERP about cases in this sales team"),
        'parent_id': fields.many2one('crm.case.section', 'Parent Team'),
        'child_ids': fields.one2many('crm.case.section', 'parent_id', 'Child Teams'),
        'resource_calendar_id': fields.many2one('resource.calendar', "Resource's Calendar"),
        'server_id':fields.many2one('email.smtpclient', 'Server ID'),
        'note': fields.text('Description'),
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
        Checks for recursion level for sections
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of section ids
        """
        level = 100

        while len(ids):
            cr.execute('select distinct parent_id from crm_case_section where id =ANY(%s)', (ids,))
            ids = filter(None, map(lambda x: x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1

        return True

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive sections.', ['parent_id'])
    ]

    def name_get(self, cr, uid, ids, context=None):
        """Overrides orm name_get method
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of section ids
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
        'name': fields.char('Case Resource Type', size=64, required=True, translate=True), 
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
        'sequence': fields.integer('Sequence', help="Gives the sequence order \
                        when displaying a list of case stages."), 
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

class crm_case(osv.osv):
    """ CRM Case """

    _name = "crm.case"
    _description = "Case"

    def _email_last(self, cursor, user, ids, name, arg, context=None):
        """Return last email from History
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case’s IDs
        @param context: A standard dictionary for contextual values
        """
        res = {}
        for case in self.browse(cursor, user, ids):
            if case.history_line:
                res[case.id] = case.history_line[0].description
            else:
                res[case.id] = False
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        """Overrides orm copy method
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case’s IDs
        @param context: A standard dictionary for contextual values
        """
        if not context:
            context = {}
        if not default:
            default = {}
        default.update({'state': 'draft', 'id': False})
        return super(crm_case, self).copy(cr, uid, id, default, context)

    def _get_log_ids(self, cr, uid, ids, field_names, arg, context=None):
        """Gets id for case log from history of particular case
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Case IDs
        @param context: A standard dictionary for contextual values
        @return:Dictionary of History Ids
        """
        if not context:
            context = {}

        result = {}
        history_obj = False
        model_obj = self.pool.get('ir.model')

        if 'history_line' in field_names:
            history_obj = self.pool.get('crm.case.history')
            name = 'history_line'

        if 'log_ids' in field_names:
            history_obj = self.pool.get('crm.case.log')
            name = 'log_ids'

        if not history_obj:
            return result

        for case in self.browse(cr, uid, ids, context):
            model_ids = model_obj.search(cr, uid, [('model', '=', case._name)])
            history_ids = history_obj.search(cr, uid, [('model_id', '=', model_ids[0]), \
                                         ('res_id', '=', case.id)])
            if history_ids:
                result[case.id] = {name: history_ids}
            else:
                result[case.id] = {name: []}

        return result

    _columns = {
        'id': fields.integer('ID', readonly=True), 
        'name': fields.char('Description', size=1024, required=True), 
        'active': fields.boolean('Active', help="If the active field is set to\
                     true, it will allow you to hide the case without removing it."), 
        'description': fields.text('Description'), 
        'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                        select=True, help='Sales team to which Case belongs to.\
                             Define Responsible user and Email account for mail gateway.'), 
        'email_from': fields.char('Email', size=128, help="These people will receive email."), 
        'email_cc': fields.text('Watchers Emails', size=252 , help="These people\
                             will receive a copy of the future" \
                            " communication between partner and users by email"), 
        'probability': fields.float('Probability'), 
        'email_last': fields.function(_email_last, method=True, 
            string='Latest E-Mail', type='text'), 
        'partner_id': fields.many2one('res.partner', 'Partner'), 
        'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', \
                                 domain="[('partner_id','=',partner_id)]"), 
        'create_date': fields.datetime('Creation Date' , readonly=True), 
        'write_date': fields.datetime('Update Date' , readonly=True), 
        'date_deadline': fields.date('Deadline'), 
        'user_id': fields.many2one('res.users', 'Responsible'), 
        'history_line': fields.function(_get_log_ids, method=True, type='one2many', \
                         multi="history_line", relation="crm.case.history", string="Communication"), 
        'log_ids': fields.function(_get_log_ids, method=True, type='one2many', \
                         multi="log_ids", relation="crm.case.log", string="Logs History"), 
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', \
                         domain="[('section_id','=',section_id),\
                        ('object_id.model', '=', 'crm.opportunity')]"), 
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True, 
                                  help='The state is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the state is set to \'Open\'.\
                                  \nWhen the case is over, the state is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the state is set to \'Pending\'.'), 
        'company_id': fields.many2one('res.company', 'Company'), 
    }
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

    _defaults = {
        'active': lambda *a: 1, 
        'user_id': _get_default_user, 
        'partner_id': _get_default_partner, 
        'partner_address_id': _get_default_partner_address, 
        'email_from': _get_default_email, 
        'state': lambda *a: 'draft', 
        'section_id': _get_section, 
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.case', context=c), 
    }

    _order = 'date_deadline desc, create_date desc,id desc'

    def unlink(self, cr, uid, ids, context=None):
        """Overrides orm unlink method
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values
        """
        if not context:
            context = {}

        for case in self.browse(cr, uid, ids, context):
            if (not case.section_id.allow_unlink) and (case.state <> 'draft'):
                raise osv.except_osv(_('Warning !'), 
                    _('You can not delete this case. You should better cancel it.'))
        return super(crm_case, self).unlink(cr, uid, ids, context)

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
        for case in self.browse(cr, uid, ids, context):
            section = (case.section_id.id or False)
            if section in s:
                st = case.stage_id.id  or False
                if st in s[section]:
                    self.write(cr, uid, [case.id], {'stage_id': s[section][st]})
        return True

    def get_stage_dict(self, cr, uid, ids, context=None):
        """This function gives dictionary for stage according to stage levels
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values"""
        if not context:
            context = {}

        sid = self.pool.get('crm.case.stage').search(cr, uid, \
                            [('object_id.model', '=', self._name)], context=context)
        s = {}
        previous = {}
        for stage in self.pool.get('crm.case.stage').browse(cr, uid, sid, context=context):
            section = stage.section_id.id or False
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
        for case in self.browse(cr, uid, ids, context):
            section = (case.section_id.id or False)

            if section in s:
                st = case.stage_id.id or False
                s[section] = dict([(v, k) for (k, v) in s[section].iteritems()])
                if st in s[section]:
                    self.write(cr, uid, [case.id], {'stage_id': s[section][st]})
        return True

    def __history(self, cr, uid, cases, keyword, history=False, email=False, details=None, email_from=False, message_id=False, context={}):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Case ids
        @param keyword: Case action keyword e.g.: If case is closed "Close" keyword is used
        @param history: Value True/False, If True it makes entry in case History otherwise in Case Log
        @param email: Email address if any
        @param details: Details of case history if any 
        @param context: A standard dictionary for contextual values"""
        if not context:
            context = {}
        model_obj = self.pool.get('ir.model')
        obj = self.pool.get('crm.case.log')
        for case in cases:
            model_ids = model_obj.search(cr, uid, [('model', '=', case._name)])
            data = {
                'name': keyword,
                'user_id': uid,
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'model_id' : model_ids and model_ids[0] or False,
                'res_id': case.id,
                'section_id': case.section_id.id,
                'message_id':message_id
            }

            if history:
                obj = self.pool.get('crm.case.history')
                data['description'] = details or case.description
                data['email_to'] = email or \
                        (case.section_id and case.section_id.reply_to) or \
                        (case.user_id and case.user_id.address_id and \
                            case.user_id.address_id.email) or tools.config.get('email_from', False)
                data['email_from'] = email_from or \
                        (case.section_id and case.section_id.reply_to) or \
                        (case.user_id and case.user_id.address_id and \
                            case.user_id.address_id.email) or tools.config.get('email_from', False)
            res = obj.create(cr, uid, data, context)
        return True
    
    _history = __history
    history = __history

    def create(self, cr, uid, *args, **argv):
        """Overrides orm create method
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param *args: Tuple Value for additional Params
        @param **argv: Dictionay of Keyword Params
        """
        res = super(crm_case, self).create(cr, uid, *args, **argv)
        cases = self.browse(cr, uid, [res])
        cases[0].state # to fill the browse record cache
        self._action(cr, uid, cases, 'draft')
        return res

    def add_reply(self, cursor, user, ids, context=None):
        """This function finds last email and gives its description value for reply mail
        @param self: The object pointer
        @param cursor: the current row, from the database cursor,
        @param user: the current user’s ID for security checks
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values
        """
        for case in self.browse(cursor, user, ids, context=context):
            if case.email_last:
                description = case.email_last
                self.write(cursor, user, case.id, {
                    'description': '> ' + description.replace('\n', '\n> '), 
                    }, context=context)
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
        return {'value': {'email_from': address.email}}

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
        self.__history(cr, uid, cases, _('Close'))
        self.write(cr, uid, ids, {'state': 'done', 'date_closed': time.strftime('%Y-%m-%d %H:%M:%S')})
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
            data = {'active': True, 'user_id': False}

            if case.section_id.parent_id:
                data['section_id'] = case.section_id.parent_id.id
                if case.section_id.parent_id.user_id:
                    data['user_id'] = case.section_id.parent_id.user_id.id
            else:
                raise osv.except_osv(_('Error !'), _('You can not escalate this case.\nYou are already at the top level.'))
            self.write(cr, uid, [case.id], data)
        cases = self.browse(cr, uid, ids)
        self.__history(cr, uid, cases, _('Escalate'))
        self._action(cr, uid, cases, 'escalate')
        return True

    def case_open(self, cr, uid, ids, *args):
        """Opens Case
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        cases = self.browse(cr, uid, ids)
        self.__history(cr, uid, cases, _('Open'))

        for case in cases:
            data = {'state': 'open', 'active': True}
            if not case.user_id:
                data['user_id'] = uid
            self.write(cr, uid, case.id, data)
        self._action(cr, uid, cases, 'open')
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
        self.__history(cr, uid, cases, _('Cancel'))
        self.write(cr, uid, ids, {'state': 'cancel', 'active': True})
        self._action(cr, uid, cases, 'cancel')
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
        self.__history(cr, uid, cases, _('Pending'))
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
        self.__history(cr, uid, cases, _('Draft'))
        self.write(cr, uid, ids, {'state': 'draft', 'active': True})
        self._action(cr, uid, cases, 'draft')
        return True

crm_case()


class crm_case_log(osv.osv):
    """ Case Communication History """
    _name = "crm.case.log"
    _description = "Case Communication History"

    _order = "id desc"
    _columns = {
        'name': fields.char('Status', size=64), 
        'date': fields.datetime('Date'), 
        'section_id': fields.many2one('crm.case.section', 'Section'), 
        'user_id': fields.many2one('res.users', 'User Responsible', readonly=True), 
        'model_id': fields.many2one('ir.model', "Model"), 
        'res_id': fields.integer('Resource ID'), 
    }

    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'), 
    }

crm_case_log()

class crm_case_history(osv.osv):
    """Case history"""

    _name = "crm.case.history"
    _description = "Case history"
    _order = "id desc"
    _inherits = {'crm.case.log': "log_id"}

    def _note_get(self, cursor, user, ids, name, arg, context=None):
        """ Gives case History Description
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case History’s IDs
        @param context: A standard dictionary for contextual values
        """
        res = {}
        for hist in self.browse(cursor, user, ids, context or {}):
            res[hist.id] = (hist.email or '/') + ' (' + str(hist.date) + ')\n'
            res[hist.id] += (hist.description or '')
        return res

    _columns = {
        'description': fields.text('Description'),
        'note': fields.function(_note_get, method=True, string="Description", type="text"),
        'email_to': fields.char('Email TO', size=84),
        'email_from' : fields.char('Email From', size=84),
        'log_id': fields.many2one('crm.case.log','Log',ondelete='cascade'),
        'message_id': fields.char('Message Id', size=1024, readonly=True, help="Message Id on Email Server.", select=True),
    }

crm_case_history()


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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
