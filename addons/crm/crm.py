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
    ('pending', 'Pending'),
]

AVAILABLE_PRIORITIES = [
    ('1', 'Highest'),
    ('2', 'High'), 
    ('3', 'Normal'), 
    ('4', 'Low'), 
    ('5', 'Lowest'), 
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
        'member_ids':fields.many2many('res.users', 'sale_member_rel', 'section_id', 'member_id', 'Team Members'),
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
        Checks for recursion level for sales team
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Sales team ids
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
        'email_to': fields.char('Email To', size=84),
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
