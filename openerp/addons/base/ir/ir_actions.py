# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A. <http://www.openerp.com>
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

import ast
import copy
import logging
import os
import re
import time
import tools
from xml import dom

import netsvc
from osv import fields,osv
from report.report_sxw import report_sxw, report_rml
from tools.config import config
from tools.safe_eval import safe_eval as eval
from tools.translate import _
from socket import gethostname

_logger = logging.getLogger(__name__)

class actions(osv.osv):
    _name = 'ir.actions.actions'
    _table = 'ir_actions'
    _order = 'name'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'type': fields.char('Action Type', required=True, size=32,readonly=True),
        'usage': fields.char('Action Usage', size=32),
    }
    _defaults = {
        'usage': lambda *a: False,
    }
actions()


class report_xml(osv.osv):

    def _report_content(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for report in self.browse(cursor, user, ids, context=context):
            data = report[name + '_data']
            if not data and report[name[:-8]]:
                fp = None
                try:
                    fp = tools.file_open(report[name[:-8]], mode='rb')
                    data = fp.read()
                except:
                    data = False
                finally:
                    if fp:
                        fp.close()
            res[report.id] = data
        return res

    def _report_content_inv(self, cursor, user, id, name, value, arg, context=None):
        self.write(cursor, user, id, {name+'_data': value}, context=context)

    def _report_sxw(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for report in self.browse(cursor, user, ids, context=context):
            if report.report_rml:
                res[report.id] = report.report_rml.replace('.rml', '.sxw')
            else:
                res[report.id] = False
        return res

    def register_all(self, cr):
        """Report registration handler that may be overridden by subclasses to
           add their own kinds of report services.
           Loads all reports with no manual loaders (auto==True) and
           registers the appropriate services to implement them.
        """
        opj = os.path.join
        cr.execute("SELECT * FROM ir_act_report_xml WHERE auto=%s ORDER BY id", (True,))
        result = cr.dictfetchall()
        svcs = netsvc.Service._services
        for r in result:
            if svcs.has_key('report.'+r['report_name']):
                continue
            if r['report_rml'] or r['report_rml_content_data']:
                report_sxw('report.'+r['report_name'], r['model'],
                        opj('addons',r['report_rml'] or '/'), header=r['header'])
            if r['report_xsl']:
                report_rml('report.'+r['report_name'], r['model'],
                        opj('addons',r['report_xml']),
                        r['report_xsl'] and opj('addons',r['report_xsl']))

    _name = 'ir.actions.report.xml'
    _table = 'ir_act_report_xml'
    _sequence = 'ir_actions_id_seq'
    _order = 'name'
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'model': fields.char('Object', size=64, required=True),
        'type': fields.char('Action Type', size=32, required=True),
        'report_name': fields.char('Service Name', size=64, required=True),
        'usage': fields.char('Action Usage', size=32),
        'report_type': fields.char('Report Type', size=32, required=True, help="Report Type, e.g. pdf, html, raw, sxw, odt, html2html, mako2html, ..."),
        'groups_id': fields.many2many('res.groups', 'res_groups_report_rel', 'uid', 'gid', 'Groups'),
        'multi': fields.boolean('On Multiple Doc.', help="If set to true, the action will not be displayed on the right toolbar of a form view."),
        'attachment': fields.char('Save as Attachment Prefix', size=128, help='This is the filename of the attachment used to store the printing result. Keep empty to not save the printed reports. You can use a python expression with the object and time variables.'),
        'attachment_use': fields.boolean('Reload from Attachment', help='If you check this, then the second time the user prints with same attachment name, it returns the previous report.'),
        'auto': fields.boolean('Custom Python Parser'),

        'header': fields.boolean('Add RML Header', help="Add or not the corporate RML header"),

        'report_xsl': fields.char('XSL Path', size=256),
        'report_xml': fields.char('XML Path', size=256, help=''),

        # Pending deprecation... to be replaced by report_file as this object will become the default report object (not so specific to RML anymore)
        'report_rml': fields.char('Main Report File Path', size=256, help="The path to the main report file (depending on Report Type) or NULL if the content is in another data field"),
        # temporary related field as report_rml is pending deprecation - this field will replace report_rml after v6.0
        'report_file': fields.related('report_rml', type="char", size=256, required=False, readonly=False, string='Report File', help="The path to the main report file (depending on Report Type) or NULL if the content is in another field", store=True),

        'report_sxw': fields.function(_report_sxw, type='char', string='SXW Path'),
        'report_sxw_content_data': fields.binary('SXW Content'),
        'report_rml_content_data': fields.binary('RML Content'),
        'report_sxw_content': fields.function(_report_content, fnct_inv=_report_content_inv, type='binary', string='SXW Content',),
        'report_rml_content': fields.function(_report_content, fnct_inv=_report_content_inv, type='binary', string='RML Content'),

    }
    _defaults = {
        'type': lambda *a: 'ir.actions.report.xml',
        'multi': lambda *a: False,
        'auto': lambda *a: True,
        'header': lambda *a: True,
        'report_sxw_content': lambda *a: False,
        'report_type': lambda *a: 'pdf',
        'attachment': lambda *a: False,
    }

report_xml()

class act_window(osv.osv):
    _name = 'ir.actions.act_window'
    _table = 'ir_act_window'
    _sequence = 'ir_actions_id_seq'
    _order = 'name'

    def _check_model(self, cr, uid, ids, context=None):
        for action in self.browse(cr, uid, ids, context):
            if not self.pool.get(action.res_model):
                return False
            if action.src_model and not self.pool.get(action.src_model):
                return False
        return True

    def _invalid_model_msg(self, cr, uid, ids, context=None):
        return _('Invalid model name in the action definition.')

    _constraints = [
        (_check_model, _invalid_model_msg, ['res_model','src_model'])
    ]

    def _views_get_fnc(self, cr, uid, ids, name, arg, context=None):
        """Returns an ordered list of the specific view modes that should be
           enabled when displaying the result of this action, along with the
           ID of the specific view to use for each mode, if any were required.

           This function hides the logic of determining the precedence between
           the view_modes string, the view_ids o2m, and the view_id m2o that can
           be set on the action.

           :rtype: dict in the form { action_id: list of pairs (tuples) }
           :return: { action_id: [(view_id, view_mode), ...], ... }, where view_mode
                    is one of the possible values for ir.ui.view.type and view_id
                    is the ID of a specific view to use for this mode, or False for
                    the default one.
        """
        res = {}
        for act in self.browse(cr, uid, ids):
            res[act.id] = [(view.view_id.id, view.view_mode) for view in act.view_ids]
            view_ids_modes = [view.view_mode for view in act.view_ids]
            modes = act.view_mode.split(',')
            missing_modes = [mode for mode in modes if mode not in view_ids_modes]
            if missing_modes:
                if act.view_id and act.view_id.type in missing_modes:
                    # reorder missing modes to put view_id first if present
                    missing_modes.remove(act.view_id.type)
                    res[act.id].append((act.view_id.id, act.view_id.type))
                res[act.id].extend([(False, mode) for mode in missing_modes])
        return res

    def _search_view(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for act in self.browse(cr, uid, ids, context=context):
            field_get = self.pool.get(act.res_model).fields_view_get(cr, uid,
                act.search_view_id and act.search_view_id.id or False,
                'search', context=context)
            res[act.id] = str(field_get)
        return res

    _columns = {
        'name': fields.char('Action Name', size=64, translate=True),
        'type': fields.char('Action Type', size=32, required=True),
        'view_id': fields.many2one('ir.ui.view', 'View Ref.', ondelete='cascade'),
        'domain': fields.char('Domain Value', size=250,
            help="Optional domain filtering of the destination data, as a Python expression"),
        'context': fields.char('Context Value', size=250, required=True,
            help="Context dictionary as Python expression, empty by default (Default: {})"),
        'res_id': fields.integer('Record ID', help="Database ID of record to open in form view, when ``view_mode`` is set to 'form' only"),
        'res_model': fields.char('Destination Model', size=64, required=True,
            help="Model name of the object to open in the view window"),
        'src_model': fields.char('Source Model', size=64,
            help="Optional model name of the objects on which this action should be visible"),
        'target': fields.selection([('current','Current Window'),('new','New Window'),('inline','Inline Edit'),('inlineview','Inline View')], 'Target Window'),
        'view_mode': fields.char('View Mode', size=250, required=True,
            help="Comma-separated list of allowed view modes, such as 'form', 'tree', 'calendar', etc. (Default: tree,form)"),
        'view_type': fields.selection((('tree','Tree'),('form','Form')), string='View Type', required=True,
            help="View type: Tree type to use for the tree view, set to 'tree' for a hierarchical tree view, or 'form' for a regular list view"),
        'usage': fields.char('Action Usage', size=32,
            help="Used to filter menu and home actions from the user form."),
        'view_ids': fields.one2many('ir.actions.act_window.view', 'act_window_id', 'Views'),
        'views': fields.function(_views_get_fnc, type='binary', string='Views',
               help="This function field computes the ordered list of views that should be enabled " \
                    "when displaying the result of an action, federating view mode, views and " \
                    "reference view. The result is returned as an ordered list of pairs (view_id,view_mode)."),
        'limit': fields.integer('Limit', help='Default limit for the list view'),
        'auto_refresh': fields.integer('Auto-Refresh',
            help='Add an auto-refresh on the view'),
        'groups_id': fields.many2many('res.groups', 'ir_act_window_group_rel',
            'act_id', 'gid', 'Groups'),
        'search_view_id': fields.many2one('ir.ui.view', 'Search View Ref.'),
        'filter': fields.boolean('Filter'),
        'auto_search':fields.boolean('Auto Search'),
        'search_view' : fields.function(_search_view, type='text', string='Search View'),
        'help': fields.text('Action description',
            help='Optional help text for the users with a description of the target view, such as its usage and purpose.',
            translate=True),
        'multi': fields.boolean('Action on Multiple Doc.', help="If set to true, the action will not be displayed on the right toolbar of a form view"),
    }

    _defaults = {
        'type': lambda *a: 'ir.actions.act_window',
        'view_type': lambda *a: 'form',
        'view_mode': lambda *a: 'tree,form',
        'context': lambda *a: '{}',
        'limit': lambda *a: 80,
        'target': lambda *a: 'current',
        'auto_refresh': lambda *a: 0,
        'auto_search':lambda *a: True,
        'multi': False,
    }

    def for_xml_id(self, cr, uid, module, xml_id, context=None):
        """ Returns the act_window object created for the provided xml_id

        :param module: the module the act_window originates in
        :param xml_id: the namespace-less id of the action (the @id
                       attribute from the XML file)
        :return: A read() view of the ir.actions.act_window
        """
        dataobj = self.pool.get('ir.model.data')
        data_id = dataobj._get_id (cr, 1, module, xml_id)
        res_id = dataobj.browse(cr, uid, data_id, context).res_id
        return self.read(cr, uid, res_id, [], context)

act_window()

VIEW_TYPES = [
    ('tree', 'Tree'),
    ('form', 'Form'),
    ('graph', 'Graph'),
    ('calendar', 'Calendar'),
    ('gantt', 'Gantt'),
    ('kanban', 'Kanban')]
class act_window_view(osv.osv):
    _name = 'ir.actions.act_window.view'
    _table = 'ir_act_window_view'
    _rec_name = 'view_id'
    _order = 'sequence'
    _columns = {
        'sequence': fields.integer('Sequence'),
        'view_id': fields.many2one('ir.ui.view', 'View'),
        'view_mode': fields.selection(VIEW_TYPES, string='View Type', required=True),
        'act_window_id': fields.many2one('ir.actions.act_window', 'Action', ondelete='cascade'),
        'multi': fields.boolean('On Multiple Doc.',
            help="If set to true, the action will not be displayed on the right toolbar of a form view."),
    }
    _defaults = {
        'multi': lambda *a: False,
    }
    def _auto_init(self, cr, context=None):
        super(act_window_view, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'act_window_view_unique_mode_per_action\'')
        if not cr.fetchone():
            cr.execute('CREATE UNIQUE INDEX act_window_view_unique_mode_per_action ON ir_act_window_view (act_window_id, view_mode)')
act_window_view()

class act_wizard(osv.osv):
    _name = 'ir.actions.wizard'
    _inherit = 'ir.actions.actions'
    _table = 'ir_act_wizard'
    _sequence = 'ir_actions_id_seq'
    _order = 'name'
    _columns = {
        'name': fields.char('Wizard Info', size=64, required=True, translate=True),
        'type': fields.char('Action Type', size=32, required=True),
        'wiz_name': fields.char('Wizard Name', size=64, required=True),
        'multi': fields.boolean('Action on Multiple Doc.', help="If set to true, the wizard will not be displayed on the right toolbar of a form view."),
        'groups_id': fields.many2many('res.groups', 'res_groups_wizard_rel', 'uid', 'gid', 'Groups'),
        'model': fields.char('Object', size=64),
    }
    _defaults = {
        'type': lambda *a: 'ir.actions.wizard',
        'multi': lambda *a: False,
    }
act_wizard()

class act_url(osv.osv):
    _name = 'ir.actions.url'
    _table = 'ir_act_url'
    _sequence = 'ir_actions_id_seq'
    _order = 'name'
    _columns = {
        'name': fields.char('Action Name', size=64, translate=True),
        'type': fields.char('Action Type', size=32, required=True),
        'url': fields.text('Action URL',required=True),
        'target': fields.selection((
            ('new', 'New Window'),
            ('self', 'This Window')),
            'Action Target', required=True
        )
    }
    _defaults = {
        'type': lambda *a: 'ir.actions.act_url',
        'target': lambda *a: 'new'
    }
act_url()

def model_get(self, cr, uid, context=None):
    wkf_pool = self.pool.get('workflow')
    ids = wkf_pool.search(cr, uid, [])
    osvs = wkf_pool.read(cr, uid, ids, ['osv'])

    res = []
    mpool = self.pool.get('ir.model')
    for osv in osvs:
        model = osv.get('osv')
        id = mpool.search(cr, uid, [('model','=',model)])
        name = mpool.read(cr, uid, id)[0]['name']
        res.append((model, name))

    return res

class ir_model_fields(osv.osv):
    _inherit = 'ir.model.fields'
    _rec_name = 'field_description'
    _columns = {
        'complete_name': fields.char('Complete Name', size=64, select=1),
    }
ir_model_fields()

class server_object_lines(osv.osv):
    _name = 'ir.server.object.lines'
    _sequence = 'ir_actions_id_seq'
    _columns = {
        'server_id': fields.many2one('ir.actions.server', 'Object Mapping'),
        'col1': fields.many2one('ir.model.fields', 'Destination', required=True),
        'value': fields.text('Value', required=True, help="Expression containing a value specification. \n"
                                                          "When Formula type is selected, this field may be a Python expression "
                                                          " that can use the same values as for the condition field on the server action.\n"
                                                          "If Value type is selected, the value will be used directly without evaluation."),
        'type': fields.selection([
            ('value','Value'),
            ('equation','Formula')
        ], 'Type', required=True, size=32, change_default=True),
    }
    _defaults = {
        'type': lambda *a: 'equation',
    }
server_object_lines()

##
# Actions that are run on the server side
#
class actions_server(osv.osv):

    def _select_signals(self, cr, uid, context=None):
        cr.execute("""SELECT distinct w.osv, t.signal FROM wkf w, wkf_activity a, wkf_transition t
                      WHERE w.id = a.wkf_id AND
                            (t.act_from = a.id OR t.act_to = a.id) AND
                            t.signal IS NOT NULL""")
        result = cr.fetchall() or []
        res = []
        for rs in result:
            if rs[0] is not None and rs[1] is not None:
                line = rs[1], "%s - (%s)" % (rs[1], rs[0])
                res.append(line)
        return res

    def _select_objects(self, cr, uid, context=None):
        model_pool = self.pool.get('ir.model')
        ids = model_pool.search(cr, uid, [('name','not ilike','.')])
        res = model_pool.read(cr, uid, ids, ['model', 'name'])
        return [(r['model'], r['name']) for r in res] +  [('','')]

    def change_object(self, cr, uid, ids, copy_object, state, context=None):
        if state == 'object_copy' and copy_object:
            if context is None:
                context = {}
            model_pool = self.pool.get('ir.model')
            model = copy_object.split(',')[0]
            mid = model_pool.search(cr, uid, [('model','=',model)])
            return {
                'value': {'srcmodel_id': mid[0]},
                'context': context
            }
        else:
            return {}

    _name = 'ir.actions.server'
    _table = 'ir_act_server'
    _sequence = 'ir_actions_id_seq'
    _order = 'sequence,name'
    _columns = {
        'name': fields.char('Action Name', required=True, size=64, translate=True),
        'condition' : fields.char('Condition', size=256, required=True,
                                  help="Condition that is tested before the action is executed, "
                                       "and prevent execution if it is not verified.\n"
                                       "Example: object.list_price > 5000\n"
                                       "It is a Python expression that can use the following values:\n"
                                       " - self: ORM model of the record on which the action is triggered\n"
                                       " - object or obj: browse_record of the record on which the action is triggered\n"
                                       " - pool: ORM model pool (i.e. self.pool)\n"
                                       " - time: Python time module\n"
                                       " - cr: database cursor\n"
                                       " - uid: current user id\n"
                                       " - context: current context"),
        'state': fields.selection([
            ('client_action','Client Action'),
            ('dummy','Dummy'),
            ('loop','Iteration'),
            ('code','Python Code'),
            ('trigger','Trigger'),
            ('email','Email'),
            ('sms','SMS'),
            ('object_create','Create Object'),
            ('object_copy','Copy Object'),
            ('object_write','Write Object'),
            ('other','Multi Actions'),
        ], 'Action Type', required=True, size=32, help="Type of the Action that is to be executed"),
        'code':fields.text('Python Code', help="Python code to be executed if condition is met.\n"
                                               "It is a Python block that can use the same values as for the condition field"),
        'sequence': fields.integer('Sequence', help="Important when you deal with multiple actions, the execution order will be decided based on this, low number is higher priority."),
        'model_id': fields.many2one('ir.model', 'Object', required=True, help="Select the object on which the action will work (read, write, create).", ondelete='cascade'),
        'action_id': fields.many2one('ir.actions.actions', 'Client Action', help="Select the Action Window, Report, Wizard to be executed."),
        'trigger_name': fields.selection(_select_signals, string='Trigger Signal', size=128, help="The workflow signal to trigger"),
        'wkf_model_id': fields.many2one('ir.model', 'Target Object', help="The object that should receive the workflow signal (must have an associated workflow)"),
        'trigger_obj_id': fields.many2one('ir.model.fields','Relation Field', help="The field on the current object that links to the target object record (must be a many2one, or an integer field with the record ID)"),
        'email': fields.char('Email Address', size=512, help="Expression that returns the email address to send to. Can be based on the same values as for the condition field.\n"
                                                             "Example: object.invoice_address_id.email, or 'me@example.com'"),
        'subject': fields.char('Subject', size=1024, translate=True, help="Email subject, may contain expressions enclosed in double brackets based on the same values as those "
                                                                          "available in the condition field, e.g. `Hello [[ object.partner_id.name ]]`"),
        'message': fields.text('Message', translate=True, help="Email contents, may contain expressions enclosed in double brackets based on the same values as those "
                                                                          "available in the condition field, e.g. `Dear [[ object.partner_id.name ]]`"),
        'mobile': fields.char('Mobile No', size=512, help="Provides fields that be used to fetch the mobile number, e.g. you select the invoice, then `object.invoice_address_id.mobile` is the field which gives the correct mobile number"),
        'sms': fields.char('SMS', size=160, translate=True),
        'child_ids': fields.many2many('ir.actions.server', 'rel_server_actions', 'server_id', 'action_id', 'Other Actions'),
        'usage': fields.char('Action Usage', size=32),
        'type': fields.char('Action Type', size=32, required=True),
        'srcmodel_id': fields.many2one('ir.model', 'Model', help="Object in which you want to create / write the object. If it is empty then refer to the Object field."),
        'fields_lines': fields.one2many('ir.server.object.lines', 'server_id', 'Field Mappings.'),
        'record_id':fields.many2one('ir.model.fields', 'Create Id', help="Provide the field name where the record id is stored after the create operations. If it is empty, you can not track the new record."),
        'write_id':fields.char('Write Id', size=256, help="Provide the field name that the record id refers to for the write operation. If it is empty it will refer to the active id of the object."),
        'loop_action':fields.many2one('ir.actions.server', 'Loop Action', help="Select the action that will be executed. Loop action will not be avaliable inside loop."),
        'expression':fields.char('Loop Expression', size=512, help="Enter the field/expression that will return the list. E.g. select the sale order in Object, and you can have loop on the sales order line. Expression = `object.order_line`."),
        'copy_object': fields.reference('Copy Of', selection=_select_objects, size=256),
    }
    _defaults = {
        'state': lambda *a: 'dummy',
        'condition': lambda *a: 'True',
        'type': lambda *a: 'ir.actions.server',
        'sequence': lambda *a: 5,
        'code': lambda *a: """# You can use the following variables:
#  - self: ORM model of the record on which the action is triggered
#  - object: browse_record of the record on which the action is triggered if there is one, otherwise None
#  - pool: ORM model pool (i.e. self.pool)
#  - time: Python time module
#  - cr: database cursor
#  - uid: current user id
#  - context: current context
# If you plan to return an action, assign: action = {...}
""",
    }

    def get_email(self, cr, uid, action, context):
        obj_pool = self.pool.get(action.model_id.model)
        id = context.get('active_id')
        obj = obj_pool.browse(cr, uid, id)

        fields = None

        if '/' in action.email.complete_name:
            fields = action.email.complete_name.split('/')
        elif '.' in action.email.complete_name:
            fields = action.email.complete_name.split('.')

        for field in fields:
            try:
                obj = getattr(obj, field)
            except Exception:
                _logger.exception('Failed to parse: %s', field)

        return obj

    def get_mobile(self, cr, uid, action, context):
        obj_pool = self.pool.get(action.model_id.model)
        id = context.get('active_id')
        obj = obj_pool.browse(cr, uid, id)

        fields = None

        if '/' in action.mobile.complete_name:
            fields = action.mobile.complete_name.split('/')
        elif '.' in action.mobile.complete_name:
            fields = action.mobile.complete_name.split('.')

        for field in fields:
            try:
                obj = getattr(obj, field)
            except Exception:
                _logger.exception('Failed to parse: %s', field)

        return obj

    def merge_message(self, cr, uid, keystr, action, context=None):
        if context is None:
            context = {}

        def merge(match):
            obj_pool = self.pool.get(action.model_id.model)
            id = context.get('active_id')
            obj = obj_pool.browse(cr, uid, id)
            exp = str(match.group()[2:-2]).strip()
            result = eval(exp,
                          {
                            'object': obj,
                            'context': dict(context), # copy context to prevent side-effects of eval
                            'time': time,
                          })
            if result in (None, False):
                return str("--------")
            return tools.ustr(result)

        com = re.compile('(\[\[.+?\]\])')
        message = com.sub(merge, keystr)

        return message

    # Context should contains:
    #   ids : original ids
    #   id  : current id of the object
    # OUT:
    #   False : Finnished correctly
    #   ACTION_ID : Action to launch

    # FIXME: refactor all the eval() calls in run()!
    def run(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        user = self.pool.get('res.users').browse(cr, uid, uid)
        for action in self.browse(cr, uid, ids, context):
            obj = None
            obj_pool = self.pool.get(action.model_id.model)
            if context.get('active_model') == action.model_id.model and context.get('active_id'):
                obj = obj_pool.browse(cr, uid, context['active_id'], context=context)
            cxt = {
                'self': obj_pool,
                'object': obj,
                'obj': obj,
                'pool': self.pool,
                'time': time,
                'cr': cr,
                'context': dict(context), # copy context to prevent side-effects of eval
                'uid': uid,
                'user': user
            }
            expr = eval(str(action.condition), cxt)
            if not expr:
                continue

            if action.state=='client_action':
                if not action.action_id:
                    raise osv.except_osv(_('Error'), _("Please specify an action to launch !"))
                return self.pool.get(action.action_id.type)\
                    .read(cr, uid, action.action_id.id, context=context)

            if action.state=='code':
                eval(action.code, cxt, mode="exec", nocopy=True) # nocopy allows to return 'action'
                if 'action' in cxt:
                    return cxt['action']

            if action.state == 'email':
                email_from = config['email_from']
                address = str(action.email)
                try:
                    address =  eval(str(action.email), cxt)
                except:
                    pass

                if not address:
                    _logger.info('No partner email address specified, not sending any email.')
                    continue

                if not email_from:
                    _logger.debug('--email-from command line option is not specified, using a fallback value instead.')
                    if user.email:
                        email_from = user.email
                    else:
                        email_from = "%s@%s" % (user.login, gethostname())

                subject = self.merge_message(cr, uid, action.subject, action, context)
                body = self.merge_message(cr, uid, action.message, action, context)

                ir_mail_server = self.pool.get('ir.mail_server')
                msg = ir_mail_server.build_email(email_from, [address], subject, body)
                res_email = ir_mail_server.send_email(cr, uid, msg)
                if res_email:
                    _logger.info('Email successfully sent to: %s', address)
                else:
                    _logger.warning('Failed to send email to: %s', address)

            if action.state == 'trigger':
                wf_service = netsvc.LocalService("workflow")
                model = action.wkf_model_id.model
                m2o_field_name = action.trigger_obj_id.name
                target_id = obj_pool.read(cr, uid, context.get('active_id'), [m2o_field_name])[m2o_field_name]
                target_id = target_id[0] if isinstance(target_id,tuple) else target_id
                wf_service.trg_validate(uid, model, int(target_id), action.trigger_name, cr)

            if action.state == 'sms':
                #TODO: set the user and password from the system
                # for the sms gateway user / password
                # USE smsclient module from extra-addons
                _logger.warning('SMS Facility has not been implemented yet. Use smsclient module!')

            if action.state == 'other':
                res = []
                for act in action.child_ids:
                    context['active_id'] = context['active_ids'][0]
                    result = self.run(cr, uid, [act.id], context)
                    if result:
                        res.append(result)
                return res

            if action.state == 'loop':
                expr = eval(str(action.expression), cxt)
                context['object'] = obj
                for i in expr:
                    context['active_id'] = i.id
                    result = self.run(cr, uid, [action.loop_action.id], context)

            if action.state == 'object_write':
                res = {}
                for exp in action.fields_lines:
                    euq = exp.value
                    if exp.type == 'equation':
                        expr = eval(euq, cxt)
                    else:
                        expr = exp.value
                    res[exp.col1.name] = expr

                if not action.write_id:
                    if not action.srcmodel_id:
                        obj_pool = self.pool.get(action.model_id.model)
                        obj_pool.write(cr, uid, [context.get('active_id')], res)
                    else:
                        write_id = context.get('active_id')
                        obj_pool = self.pool.get(action.srcmodel_id.model)
                        obj_pool.write(cr, uid, [write_id], res)

                elif action.write_id:
                    obj_pool = self.pool.get(action.srcmodel_id.model)
                    rec = self.pool.get(action.model_id.model).browse(cr, uid, context.get('active_id'))
                    id = eval(action.write_id, {'object': rec})
                    try:
                        id = int(id)
                    except:
                        raise osv.except_osv(_('Error'), _("Problem in configuration `Record Id` in Server Action!"))

                    if type(id) != type(1):
                        raise osv.except_osv(_('Error'), _("Problem in configuration `Record Id` in Server Action!"))
                    write_id = id
                    obj_pool.write(cr, uid, [write_id], res)

            if action.state == 'object_create':
                res = {}
                for exp in action.fields_lines:
                    euq = exp.value
                    if exp.type == 'equation':
                        expr = eval(euq, cxt)
                    else:
                        expr = exp.value
                    res[exp.col1.name] = expr

                obj_pool = None
                res_id = False
                obj_pool = self.pool.get(action.srcmodel_id.model)
                res_id = obj_pool.create(cr, uid, res)
                if action.record_id:
                    self.pool.get(action.model_id.model).write(cr, uid, [context.get('active_id')], {action.record_id.name:res_id})

            if action.state == 'object_copy':
                res = {}
                for exp in action.fields_lines:
                    euq = exp.value
                    if exp.type == 'equation':
                        expr = eval(euq, cxt)
                    else:
                        expr = exp.value
                    res[exp.col1.name] = expr

                model = action.copy_object.split(',')[0]
                cid = action.copy_object.split(',')[1]
                obj_pool = self.pool.get(model)
                res_id = obj_pool.copy(cr, uid, int(cid), res)

        return False

actions_server()

class act_window_close(osv.osv):
    _name = 'ir.actions.act_window_close'
    _inherit = 'ir.actions.actions'
    _table = 'ir_actions'
    _defaults = {
        'type': lambda *a: 'ir.actions.act_window_close',
    }
act_window_close()

# This model use to register action services.
TODO_STATES = [('open', 'To Do'),
               ('done', 'Done')]
TODO_TYPES = [('manual', 'Launch Manually'),('once', 'Launch Manually Once'),
              ('automatic', 'Launch Automatically')]
class ir_actions_todo(osv.osv):
    """
    Configuration Wizards
    """
    _name = 'ir.actions.todo'
    _description = "Configuration Wizards"
    _columns={
        'action_id': fields.many2one(
            'ir.actions.actions', 'Action', select=True, required=True),
        'sequence': fields.integer('Sequence'),
        'state': fields.selection(TODO_STATES, string='State', required=True),
        'name': fields.char('Name', size=64),
        'type': fields.selection(TODO_TYPES, 'Type', required=True,
            help="""Manual: Launched manually.
Automatic: Runs whenever the system is reconfigured.
Launch Manually Once: after hacing been launched manually, it sets automatically to Done."""),
        'groups_id': fields.many2many('res.groups', 'res_groups_action_rel', 'uid', 'gid', 'Groups'),
        'note': fields.text('Text', translate=True),
    }
    _defaults={
        'state': 'open',
        'sequence': 10,
        'type': 'manual',
    }
    _order="sequence,id"

    def action_launch(self, cr, uid, ids, context=None):
        """ Launch Action of Wizard"""
        wizard_id = ids and ids[0] or False
        wizard = self.browse(cr, uid, wizard_id, context=context)
        if wizard.type in ('automatic', 'once'):
            wizard.write({'state': 'done'})

        # Load action
        act_type = self.pool.get('ir.actions.actions').read(cr, uid, wizard.action_id.id, ['type'], context=context)

        res = self.pool.get(act_type['type']).read(cr, uid, wizard.action_id.id, [], context=context)
        if act_type<>'ir.actions.act_window':
            return res
        res.setdefault('context','{}')
        res['nodestroy'] = True

        # Open a specific record when res_id is provided in the context
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        ctx = eval(res['context'], {'user': user})
        if ctx.get('res_id'):
            res.update({'res_id': ctx.pop('res_id')})

        # disable log for automatic wizards
        if wizard.type == 'automatic':
            ctx.update({'disable_log': True})
        res.update({'context': ctx})

        return res

    def action_open(self, cr, uid, ids, context=None):
        """ Sets configuration wizard in TODO state"""
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)

    def progress(self, cr, uid, context=None):
        """ Returns a dict with 3 keys {todo, done, total}.

        These keys all map to integers and provide the number of todos
        marked as open, the total number of todos and the number of
        todos not open (which is basically a shortcut to total-todo)

        :rtype: dict
        """
        user_groups = set(map(
            lambda x: x.id,
            self.pool['res.users'].browse(cr, uid, [uid], context=context)[0].groups_id))
        def groups_match(todo):
            """ Checks if the todo's groups match those of the current user
            """
            return not todo.groups_id \
                   or bool(user_groups.intersection((
                        group.id for group in todo.groups_id)))

        done = filter(
            groups_match,
            self.browse(cr, uid,
                self.search(cr, uid, [('state', '!=', 'open')], context=context),
                        context=context))

        total = filter(
            groups_match,
            self.browse(cr, uid,
                self.search(cr, uid, [], context=context),
                        context=context))

        return {
            'done': len(done),
            'total': len(total),
            'todo': len(total) - len(done)
        }

ir_actions_todo()

class act_client(osv.osv):
    _name = 'ir.actions.client'
    _inherit = 'ir.actions.actions'
    _table = 'ir_act_client'
    _sequence = 'ir_actions_id_seq'
    _order = 'name'

    def _get_params(self, cr, uid, ids, field_name, arg, context):
        result = {}
        for record in self.browse(cr, uid, ids, context=context):
            result[record.id] = record.params_store and eval(record.params_store, {'uid': uid}) or False
        return result

    def _set_params(self, cr, uid, id, field_name, field_value, arg, context):
        if isinstance(field_value, dict):
            self.write(cr, uid, id, {'params_store': repr(field_value)}, context=context)
        else:
            self.write(cr, uid, id, {'params_store': field_value}, context=context)

    _columns = {
        'name': fields.char('Action Name', required=True, size=64, translate=True),
        'tag': fields.char('Client action tag', size=64, required=True,
                           help="An arbitrary string, interpreted by the client"
                                " according to its own needs and wishes. There "
                                "is no central tag repository across clients."),
        'res_model': fields.char('Destination Model', size=64, 
            help="Optional model, mostly used for needactions."),
        'params': fields.function(_get_params, fnct_inv=_set_params,
                                  type='binary', 
                                  string="Supplementary arguments",
                                  help="Arguments sent to the client along with"
                                       "the view tag"),
        'params_store': fields.binary("Params storage", readonly=True)
    }
    _defaults = {
        'type': 'ir.actions.client',

    }
act_client()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
