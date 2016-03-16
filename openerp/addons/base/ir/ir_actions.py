# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial
import logging
import operator
import os
import time
import datetime
import dateutil
import pytz

import openerp
from openerp import SUPERUSER_ID
from openerp import tools
from openerp import workflow
import openerp.api
from openerp.osv import fields, osv
from openerp.osv.orm import browse_record
import openerp.report.interface
from openerp.report.report_sxw import report_sxw, report_rml
from openerp.tools import ormcache
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
import openerp.workflow
from openerp.exceptions import MissingError, UserError

_logger = logging.getLogger(__name__)


class actions(osv.osv):
    _name = 'ir.actions.actions'
    _table = 'ir_actions'
    _order = 'name'
    _columns = {
        'name': fields.char('Name', required=True),
        'type': fields.char('Action Type', required=True),
        'usage': fields.char('Action Usage'),
        'xml_id': fields.function(osv.osv.get_external_id, type='char', string="External ID"),
        'help': fields.html('Action description',
            help='Optional help text for the users with a description of the target view, such as its usage and purpose.',
            translate=True),
    }
    _defaults = {
        'usage': lambda *a: False,
    }

    def create(self, cr, uid, vals, context=None):
        res = super(actions, self).create(cr, uid, vals, context=context)
        # ir_values.get_actions() depends on action records
        self.pool['ir.values'].clear_caches()
        return res

    def write(self, cr, uid, ids, vals, context=None):
        res = super(actions, self).write(cr, uid, ids, vals, context=context)
        # ir_values.get_actions() depends on action records
        self.pool['ir.values'].clear_caches()
        return res

    def unlink(self, cr, uid, ids, context=None):
        """unlink ir.action.todo which are related to actions which will be deleted.
           NOTE: ondelete cascade will not work on ir.actions.actions so we will need to do it manually."""
        todo_obj = self.pool.get('ir.actions.todo')
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]
        todo_ids = todo_obj.search(cr, uid, [('action_id', 'in', ids)], context=context)
        todo_obj.unlink(cr, uid, todo_ids, context=context)
        res = super(actions, self).unlink(cr, uid, ids, context=context)
        # ir_values.get_actions() depends on action records
        self.pool['ir.values'].clear_caches()
        return res

    def _get_eval_context(self, cr, uid, action=None, context=None):
        """ evaluation context to pass to safe_eval """
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return {
            'uid': uid,
            'user': user,
            'time': time,
            'datetime': datetime,
            'dateutil': dateutil,
            # NOTE: only `timezone` function. Do not provide the whole `pytz` module as users
            #       will have access to `pytz.os` and `pytz.sys` to do nasty things...
            'timezone': pytz.timezone,
        }

class ir_actions_report_xml(osv.osv):

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

    def _lookup_report(self, cr, name):
        """
        Look up a report definition.
        """
        opj = os.path.join

        # First lookup in the deprecated place, because if the report definition
        # has not been updated, it is more likely the correct definition is there.
        # Only reports with custom parser sepcified in Python are still there.
        if 'report.' + name in openerp.report.interface.report_int._reports:
            new_report = openerp.report.interface.report_int._reports['report.' + name]
        else:
            cr.execute("SELECT * FROM ir_act_report_xml WHERE report_name=%s", (name,))
            r = cr.dictfetchone()
            if r:
                if r['report_type'] in ['qweb-pdf', 'qweb-html']:
                    return r['report_name']
                elif r['report_rml'] or r['report_rml_content_data']:
                    if r['parser']:
                        kwargs = { 'parser': operator.attrgetter(r['parser'])(openerp.addons) }
                    else:
                        kwargs = {}
                    new_report = report_sxw('report.'+r['report_name'], r['model'],
                            opj('addons',r['report_rml'] or '/'), header=r['header'], register=False, **kwargs)
                elif r['report_xsl'] and r['report_xml']:
                    new_report = report_rml('report.'+r['report_name'], r['model'],
                            opj('addons',r['report_xml']),
                            r['report_xsl'] and opj('addons',r['report_xsl']), register=False)
                else:
                    raise Exception, "Unhandled report type: %s" % r
            else:
                raise Exception, "Required report does not exist: %s" % name

        return new_report

    def create_action(self, cr, uid, ids, context=None):
        """ Create a contextual action for each of the report."""
        for ir_actions_report_xml in self.browse(cr, uid, ids, context=context):
            ir_values_id = self.pool['ir.values'].create(cr, SUPERUSER_ID, {
                'name': ir_actions_report_xml.name,
                'model': ir_actions_report_xml.model,
                'key2': 'client_print_multi',
                'value': "ir.actions.report.xml,%s" % ir_actions_report_xml.id,
            }, context)
            ir_actions_report_xml.write({
                'ir_values_id': ir_values_id,
            })
        return True

    def unlink_action(self, cr, uid, ids, context=None):
        """ Remove the contextual actions created for the reports."""
        self.check_access_rights(cr , uid, 'write', raise_exception=True)
        for ir_actions_report_xml in self.browse(cr, uid, ids, context=context):
            if ir_actions_report_xml.ir_values_id:
                try:
                    self.pool['ir.values'].unlink(
                        cr, SUPERUSER_ID, ir_actions_report_xml.ir_values_id.id, context
                    )
                except Exception:
                    raise UserError(_('Deletion of the action record failed.'))
        return True

    def render_report(self, cr, uid, res_ids, name, data, context=None):
        """
        Look up a report definition and render the report for the provided IDs.
        """
        new_report = self._lookup_report(cr, name)

        if isinstance(new_report, (str, unicode)):  # Qweb report
            # The only case where a QWeb report is rendered with this method occurs when running
            # yml tests originally written for RML reports.
            if openerp.tools.config['test_enable'] and not tools.config['test_report_directory']:
                # Only generate the pdf when a destination folder has been provided.
                return self.pool['report'].get_html(cr, uid, res_ids, new_report, data=data, context=context), 'html'
            else:
                return self.pool['report'].get_pdf(cr, uid, res_ids, new_report, data=data, context=context), 'pdf'
        else:
            return new_report.create(cr, uid, res_ids, data, context)

    _name = 'ir.actions.report.xml'
    _inherit = 'ir.actions.actions'
    _table = 'ir_act_report_xml'
    _sequence = 'ir_actions_id_seq'
    _order = 'name'
    _columns = {
        'type': fields.char('Action Type', required=True),
        'name': fields.char('Name', required=True, translate=True),

        'model': fields.char('Model', required=True),
        'report_type': fields.selection([('qweb-pdf', 'PDF'),
                    ('qweb-html', 'HTML'),
                    ('controller', 'Controller'),
                    ('pdf', 'RML pdf (deprecated)'),
                    ('sxw', 'RML sxw (deprecated)'),
                    ('webkit', 'Webkit (deprecated)'),
                    ], 'Report Type', required=True, help="HTML will open the report directly in your browser, PDF will use wkhtmltopdf to render the HTML into a PDF file and let you download it, Controller allows you to define the url of a custom controller outputting any kind of report."),
        'report_name': fields.char('Template Name', required=True, help="For QWeb reports, name of the template used in the rendering. The method 'render_html' of the model 'report.template_name' will be called (if any) to give the html. For RML reports, this is the LocalService name."),
        'groups_id': fields.many2many('res.groups', 'res_groups_report_rel', 'uid', 'gid', 'Groups'),
        'ir_values_id': fields.many2one('ir.values', 'More Menu entry', readonly=True,
                                        help='More menu entry.', copy=False),

        # options
        'multi': fields.boolean('On Multiple Doc.', help="If set to true, the action will not be displayed on the right toolbar of a form view."),
        'attachment_use': fields.boolean('Reload from Attachment', help='If you check this, then the second time the user prints with same attachment name, it returns the previous report.'),
        'attachment': fields.char('Save as Attachment Prefix', help='This is the filename of the attachment used to store the printing result. Keep empty to not save the printed reports. You can use a python expression with the object and time variables.'),


        # Deprecated rml stuff
        'usage': fields.char('Action Usage'),
        'header': fields.boolean('Add RML Header', help="Add or not the corporate RML header"),
        'parser': fields.char('Parser Class'),
        'auto': fields.boolean('Custom Python Parser'),

        'report_xsl': fields.char('XSL Path'),
        'report_xml': fields.char('XML Path'),

        'report_rml': fields.char('Main Report File Path/controller', help="The path to the main report file/controller (depending on Report Type) or empty if the content is in another data field"),
        'report_file': fields.related('report_rml', type="char", required=False, readonly=False, string='Report File', help="The path to the main report file (depending on Report Type) or empty if the content is in another field", store=True),

        'report_sxw': fields.function(_report_sxw, type='char', string='SXW Path'),
        'report_sxw_content_data': fields.binary('SXW Content'),
        'report_rml_content_data': fields.binary('RML Content'),
        'report_sxw_content': fields.function(_report_content, fnct_inv=_report_content_inv, type='binary', string='SXW Content',),
        'report_rml_content': fields.function(_report_content, fnct_inv=_report_content_inv, type='binary', string='RML Content'),
    }
    _defaults = {
        'type': 'ir.actions.report.xml',
        'multi': False,
        'auto': True,
        'header': True,
        'report_sxw_content': False,
        'report_type': 'pdf',
        'attachment': False,
    }


class ir_actions_act_window(osv.osv):
    _name = 'ir.actions.act_window'
    _table = 'ir_act_window'
    _inherit = 'ir.actions.actions'
    _sequence = 'ir_actions_id_seq'
    _order = 'name'

    def _check_model(self, cr, uid, ids, context=None):
        for action in self.browse(cr, uid, ids, context):
            if action.res_model not in self.pool:
                return False
            if action.src_model and action.src_model not in self.pool:
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
            field_get = self.pool[act.res_model].fields_view_get(cr, uid,
                act.search_view_id and act.search_view_id.id or False,
                'search', context=context)
            res[act.id] = str(field_get)
        return res

    _columns = {
        'name': fields.char('Action Name', required=True, translate=True),
        'type': fields.char('Action Type', required=True),
        'view_id': fields.many2one('ir.ui.view', 'View Ref.', ondelete='set null'),
        'domain': fields.char('Domain Value',
            help="Optional domain filtering of the destination data, as a Python expression"),
        'context': fields.char('Context Value', required=True,
            help="Context dictionary as Python expression, empty by default (Default: {})"),
        'res_id': fields.integer('Record ID', help="Database ID of record to open in form view, when ``view_mode`` is set to 'form' only"),
        'res_model': fields.char('Destination Model', required=True,
            help="Model name of the object to open in the view window"),
        'src_model': fields.char('Source Model',
            help="Optional model name of the objects on which this action should be visible"),
        'target': fields.selection([('current','Current Window'),('new','New Window'),('inline','Inline Edit'),('inlineview','Inline View')], 'Target Window'),
        'view_mode': fields.char('View Mode', required=True,
            help="Comma-separated list of allowed view modes, such as 'form', 'tree', 'calendar', etc. (Default: tree,form)"),
        'view_type': fields.selection((('tree','Tree'),('form','Form')), string='View Type', required=True,
            help="View type: Tree type to use for the tree view, set to 'tree' for a hierarchical tree view, or 'form' for a regular list view"),
        'usage': fields.char('Action Usage',
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
        'multi': fields.boolean('Restrict to lists', help="If checked and the action is bound to a model, it will only appear in the More menu on list views"),
    }

    _defaults = {
        'type': 'ir.actions.act_window',
        'view_type': 'form',
        'view_mode': 'tree,form',
        'context': '{}',
        'limit': 80,
        'target': 'current',
        'auto_refresh': 0,
        'auto_search':True,
        'multi': False,
    }
    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        """ call the method get_empty_list_help of the model and set the window action help message
        """
        ids_int = isinstance(ids, (int, long))
        if ids_int:
            ids = [ids]
        results = super(ir_actions_act_window, self).read(cr, uid, ids, fields=fields, context=context, load=load)

        if not fields or 'help' in fields:
            for res in results:
                model = res.get('res_model')
                if model and self.pool.get(model):
                    ctx = dict(context or {})
                    res['help'] = self.pool[model].get_empty_list_help(cr, uid, res.get('help', ""), context=ctx)
        if ids_int:
            return results[0]
        return results

    def for_xml_id(self, cr, uid, module, xml_id, context=None):
        """ Returns the act_window object created for the provided xml_id

        :param module: the module the act_window originates in
        :param xml_id: the namespace-less id of the action (the @id
                       attribute from the XML file)
        :return: A read() view of the ir.actions.act_window
        """
        dataobj = self.pool.get('ir.model.data')
        data_id = dataobj._get_id (cr, SUPERUSER_ID, module, xml_id)
        res_id = dataobj.browse(cr, uid, data_id, context).res_id
        return self.read(cr, uid, [res_id], [], context)[0]

    @openerp.api.model
    def create(self, vals):
        self.clear_caches()
        return super(ir_actions_act_window, self).create(vals)

    @openerp.api.multi
    def unlink(self):
        self.clear_caches()
        return super(ir_actions_act_window, self).unlink()

    @openerp.api.multi
    def exists(self):
        ids = self._existing()
        existing = self.filtered(lambda rec: rec.id in ids)
        if len(existing) < len(self):
            # mark missing records in cache with a failed value
            exc = MissingError(_("Record does not exist or has been deleted."))
            (self - existing)._cache.update(openerp.fields.FailedValue(exc))
        return existing

    @openerp.api.model
    @ormcache()
    def _existing(self):
        self._cr.execute("SELECT id FROM %s" % self._table)
        return set(row[0] for row in self._cr.fetchall())

VIEW_TYPES = [
    ('tree', 'Tree'),
    ('form', 'Form'),
    ('graph', 'Graph'),
    ('pivot', 'Pivot'),
    ('calendar', 'Calendar'),
    ('gantt', 'Gantt'),
    ('kanban', 'Kanban')]
class ir_actions_act_window_view(osv.osv):
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
        'multi': False,
    }
    def _auto_init(self, cr, context=None):
        super(ir_actions_act_window_view, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'act_window_view_unique_mode_per_action\'')
        if not cr.fetchone():
            cr.execute('CREATE UNIQUE INDEX act_window_view_unique_mode_per_action ON ir_act_window_view (act_window_id, view_mode)')


class ir_actions_act_window_close(osv.osv):
    _name = 'ir.actions.act_window_close'
    _inherit = 'ir.actions.actions'
    _table = 'ir_actions'
    _defaults = {
        'type': 'ir.actions.act_window_close',
    }


class ir_actions_act_url(osv.osv):
    _name = 'ir.actions.act_url'
    _table = 'ir_act_url'
    _inherit = 'ir.actions.actions'
    _sequence = 'ir_actions_id_seq'
    _order = 'name'
    _columns = {
        'name': fields.char('Action Name', required=True, translate=True),
        'type': fields.char('Action Type', required=True),
        'url': fields.text('Action URL',required=True),
        'target': fields.selection((
            ('new', 'New Window'),
            ('self', 'This Window')),
            'Action Target', required=True
        )
    }
    _defaults = {
        'type': 'ir.actions.act_url',
        'target': 'new'
    }


class ir_actions_server(osv.osv):
    """ Server actions model. Server action work on a base model and offer various
    type of actions that can be executed automatically, for example using base
    action rules, of manually, by adding the action in the 'More' contextual
    menu.

    Since OpenERP 8.0 a button 'Create Menu Action' button is available on the
    action form view. It creates an entry in the More menu of the base model.
    This allows to create server actions and run them in mass mode easily through
    the interface.

    The available actions are :

    - 'Execute Python Code': a block of python code that will be executed
    - 'Trigger a Workflow Signal': send a signal to a workflow
    - 'Run a Client Action': choose a client action to launch
    - 'Create or Copy a new Record': create a new record with new values, or
      copy an existing record in your database
    - 'Write on a Record': update the values of a record
    - 'Execute several actions': define an action that triggers several other
      server actions
    """
    _name = 'ir.actions.server'
    _table = 'ir_act_server'
    _inherit = 'ir.actions.actions'
    _sequence = 'ir_actions_id_seq'
    _order = 'sequence,name'

    def _select_objects(self, cr, uid, context=None):
        model_pool = self.pool.get('ir.model')
        ids = model_pool.search(cr, uid, [], limit=None)
        res = model_pool.read(cr, uid, ids, ['model', 'name'])
        return [(r['model'], r['name']) for r in res] + [('', '')]

    def _get_states(self, cr, uid, context=None):
        """ Override me in order to add new states in the server action. Please
        note that the added key length should not be higher than already-existing
        ones. """
        return [('code', 'Execute Python Code'),
                ('trigger', 'Trigger a Workflow Signal'),
                ('client_action', 'Run a Client Action'),
                ('object_create', 'Create or Copy a new Record'),
                ('object_write', 'Write on a Record'),
                ('multi', 'Execute several actions')]

    def _get_states_wrapper(self, cr, uid, context=None):
        return self._get_states(cr, uid, context)

    _columns = {
        'name': fields.char('Action Name', required=True, translate=True),
        'condition': fields.char('Condition',
                                 help="Condition verified before executing the server action. If it "
                                 "is not verified, the action will not be executed. The condition is "
                                 "a Python expression, like 'object.list_price > 5000'. A void "
                                 "condition is considered as always True. Help about python expression "
                                 "is given in the help tab."),
        'state': fields.selection(_get_states_wrapper, 'Action To Do', required=True,
                                  help="Type of server action. The following values are available:\n"
                                  "- 'Execute Python Code': a block of python code that will be executed\n"
                                  "- 'Trigger a Workflow Signal': send a signal to a workflow\n"
                                  "- 'Run a Client Action': choose a client action to launch\n"
                                  "- 'Create or Copy a new Record': create a new record with new values, or copy an existing record in your database\n"
                                  "- 'Write on a Record': update the values of a record\n"
                                  "- 'Execute several actions': define an action that triggers several other server actions\n"
                                  "- 'Send Email': automatically send an email (available in email_template)"),
        'usage': fields.char('Action Usage'),
        'type': fields.char('Action Type', required=True),
        # Generic
        'sequence': fields.integer('Sequence',
                                   help="When dealing with multiple actions, the execution order is "
                                   "based on the sequence. Low number means high priority."),
        'model_id': fields.many2one('ir.model', 'Base Model', required=True, ondelete='cascade',
                                    help="Base model on which the server action runs."),
        'model_name': fields.related('model_id', 'model', type='char',
                                     string='Model Name', readonly=True),
        'menu_ir_values_id': fields.many2one('ir.values', 'More Menu entry', readonly=True,
                                             help='More menu entry.', copy=False),
        # Client Action
        'action_id': fields.many2one('ir.actions.actions', 'Client Action',
                                     help="Select the client action that has to be executed."),
        # Python code
        'code': fields.text('Python Code',
                            help="Write Python code that the action will execute. Some variables are "
                            "available for use; help about pyhon expression is given in the help tab."),
        # Workflow signal
        'use_relational_model': fields.selection([('base', 'Use the base model of the action'),
                                                  ('relational', 'Use a relation field on the base model')],
                                                 string='Target Model', required=True),
        'wkf_transition_id': fields.many2one('workflow.transition', string='Signal to Trigger',
                                             help="Select the workflow signal to trigger."),
        'wkf_model_id': fields.many2one('ir.model', 'Target Model',
                                        help="The model that will receive the workflow signal. Note that it should have a workflow associated with it."),
        'wkf_model_name': fields.related('wkf_model_id', 'model', type='char', string='Target Model Name', store=True, readonly=True),
        'wkf_field_id': fields.many2one('ir.model.fields', string='Relation Field',
                                        oldname='trigger_obj_id',
                                        help="The field on the current object that links to the target object record (must be a many2one, or an integer field with the record ID)"),
        # Multi
        'child_ids': fields.many2many('ir.actions.server', 'rel_server_actions',
                                      'server_id', 'action_id',
                                      string='Child Actions',
                                      help='Child server actions that will be executed. Note that the last return returned action value will be used as global return value.'),
        # Create/Copy/Write
        'use_create': fields.selection([('new', 'Create a new record in the Base Model'),
                                        ('new_other', 'Create a new record in another model'),
                                        ('copy_current', 'Copy the current record'),
                                        ('copy_other', 'Choose and copy a record in the database')],
                                       string="Creation Policy", required=True,
                                       help=""),
        'crud_model_id': fields.many2one('ir.model', 'Target Model',
                                         oldname='srcmodel_id',
                                         help="Model for record creation / update. Set this field only to specify a different model than the base model."),
        'crud_model_name': fields.related('crud_model_id', 'model', type='char',
                                          string='Create/Write Target Model Name',
                                          store=True, readonly=True),
        'ref_object': fields.reference('Reference record', selection=_select_objects, size=128,
                                       oldname='copy_object'),
        'link_new_record': fields.boolean('Attach the new record',
                                          help="Check this if you want to link the newly-created record "
                                          "to the current record on which the server action runs."),
        'link_field_id': fields.many2one('ir.model.fields', 'Link using field',
                                         oldname='record_id',
                                         help="Provide the field where the record id is stored after the operations."),
        'use_write': fields.selection([('current', 'Update the current record'),
                                       ('expression', 'Update a record linked to the current record using python'),
                                       ('other', 'Choose and Update a record in the database')],
                                      string='Update Policy', required=True,
                                      help=""),
        'write_expression': fields.char('Expression',
                                        oldname='write_id',
                                        help="Provide an expression that, applied on the current record, gives the field to update."),
        'fields_lines': fields.one2many('ir.server.object.lines', 'server_id',
                                        string='Value Mapping',
                                        copy=True),

        # Fake fields used to implement the placeholder assistant
        'model_object_field': fields.many2one('ir.model.fields', string="Field",
                                              help="Select target field from the related document model.\n"
                                                   "If it is a relationship field you will be able to select "
                                                   "a target field at the destination of the relationship."),
        'sub_object': fields.many2one('ir.model', 'Sub-model', readonly=True,
                                      help="When a relationship field is selected as first field, "
                                           "this field shows the document model the relationship goes to."),
        'sub_model_object_field': fields.many2one('ir.model.fields', 'Sub-field',
                                                  help="When a relationship field is selected as first field, "
                                                       "this field lets you select the target field within the "
                                                       "destination document model (sub-model)."),
        'copyvalue': fields.char('Placeholder Expression', help="Final placeholder expression, to be copy-pasted in the desired template field."),
        # Fake fields used to implement the ID finding assistant
        'id_object': fields.reference('Record', selection=_select_objects, size=128),
        'id_value': fields.char('Record ID'),
    }

    _defaults = {
        'state': 'code',
        'condition': 'True',
        'type': 'ir.actions.server',
        'sequence': 5,
        'code': """# Available locals:
#  - time, datetime, dateutil: Python libraries
#  - env: Odoo Environement
#  - model: Model of the record on which the action is triggered
#  - object: Record on which the action is triggered if there is one, otherwise None
#  - workflow: Workflow engine
#  - log : log(message), function to log debug information in logging table
#  - Warning: Warning Exception to use with raise
# To return an action, assign: action = {...}""",
        'use_relational_model': 'base',
        'use_create': 'new',
        'use_write': 'current',
    }

    def _check_expression(self, cr, uid, expression, model_id, context):
        """ Check python expression (condition, write_expression). Each step of
        the path must be a valid many2one field, or an integer field for the last
        step.

        :param str expression: a python expression, beginning by 'obj' or 'object'
        :param int model_id: the base model of the server action
        :returns tuple: (is_valid, target_model_name, error_msg)
        """
        if not model_id:
            return (False, None, 'Your expression cannot be validated because the Base Model is not set.')
        # fetch current model
        current_model_name = self.pool.get('ir.model').browse(cr, uid, model_id, context).model
        # transform expression into a path that should look like 'object.many2onefield.many2onefield'
        path = expression.split('.')
        initial = path.pop(0)
        if initial not in ['obj', 'object']:
            return (False, None, 'Your expression should begin with obj or object.\nAn expression builder is available in the help tab.')
        # analyze path
        while path:
            step = path.pop(0)
            field = self.pool[current_model_name]._fields.get(step)
            if not field:
                return (False, None, 'Part of the expression (%s) is not recognized as a column in the model %s.' % (step, current_model_name))
            ftype = field.type
            if ftype not in ['many2one', 'int']:
                return (False, None, 'Part of the expression (%s) is not a valid column type (is %s, should be a many2one or an int)' % (step, ftype))
            if ftype == 'int' and path:
                return (False, None, 'Part of the expression (%s) is an integer field that is only allowed at the end of an expression' % (step))
            if ftype == 'many2one':
                current_model_name = field.comodel_name
        return (True, current_model_name, None)

    def _check_write_expression(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if record.write_expression and record.model_id:
                correct, model_name, message = self._check_expression(cr, uid, record.write_expression, record.model_id.id, context=context)
                if not correct:
                    _logger.warning('Invalid expression: %s' % message)
                    return False
        return True

    _constraints = [
        (_check_write_expression,
            'Incorrect Write Record Expression',
            ['write_expression']),
        (partial(osv.Model._check_m2m_recursion, field_name='child_ids'),
            'Recursion found in child server actions',
            ['child_ids']),
    ]

    def on_change_model_id(self, cr, uid, ids, model_id, wkf_model_id, crud_model_id, context=None):
        """ When changing the action base model, reset workflow and crud config
        to ease value coherence. """
        values = {
            'use_create': 'new',
            'use_write': 'current',
            'use_relational_model': 'base',
            'wkf_model_id': model_id,
            'wkf_field_id': False,
            'crud_model_id': model_id,
        }

        if model_id:
            values['model_name'] = self.pool.get('ir.model').browse(cr, uid, model_id, context).model

        return {'value': values}

    def on_change_wkf_wonfig(self, cr, uid, ids, use_relational_model, wkf_field_id, wkf_model_id, model_id, context=None):
        """ Update workflow type configuration

         - update the workflow model (for base (model_id) /relational (field.relation))
         - update wkf_transition_id to False if workflow model changes, to force
           the user to choose a new one
        """
        values = {}
        if use_relational_model == 'relational' and wkf_field_id:
            field = self.pool['ir.model.fields'].browse(cr, uid, wkf_field_id, context=context)
            new_wkf_model_id = self.pool.get('ir.model').search(cr, uid, [('model', '=', field.relation)], context=context)[0]
            values['wkf_model_id'] = new_wkf_model_id
        else:
            values['wkf_model_id'] = model_id
        return {'value': values}

    def on_change_wkf_model_id(self, cr, uid, ids, wkf_model_id, context=None):
        """ When changing the workflow model, update its stored name also """
        wkf_model_name = False
        if wkf_model_id:
            wkf_model_name = self.pool.get('ir.model').browse(cr, uid, wkf_model_id, context).model
        values = {'wkf_transition_id': False, 'wkf_model_name': wkf_model_name}
        return {'value': values}

    def on_change_crud_config(self, cr, uid, ids, state, use_create, use_write, ref_object, crud_model_id, model_id, context=None):
        """ Wrapper on CRUD-type (create or write) on_change """
        if state == 'object_create':
            return self.on_change_create_config(cr, uid, ids, use_create, ref_object, crud_model_id, model_id, context=context)
        elif state == 'object_write':
            return self.on_change_write_config(cr, uid, ids, use_write, ref_object, crud_model_id, model_id, context=context)
        else:
            return {}

    def on_change_create_config(self, cr, uid, ids, use_create, ref_object, crud_model_id, model_id, context=None):
        """ When changing the object_create type configuration:

         - `new` and `copy_current`: crud_model_id is the same as base model
         - `new_other`: user choose crud_model_id
         - `copy_other`: disassemble the reference object to have its model
         - if the target model has changed, then reset the link field that is
           probably not correct anymore
        """
        values = {}
        if use_create == 'new':
            values['crud_model_id'] = model_id
        elif use_create == 'new_other':
            pass
        elif use_create == 'copy_current':
            values['crud_model_id'] = model_id
        elif use_create == 'copy_other' and ref_object:
            ref_model, ref_id = ref_object.split(',')
            ref_model_id = self.pool['ir.model'].search(cr, uid, [('model', '=', ref_model)], context=context)[0]
            values['crud_model_id'] = ref_model_id

        if values.get('crud_model_id') != crud_model_id:
            values['link_field_id'] = False
        return {'value': values}

    def on_change_write_config(self, cr, uid, ids, use_write, ref_object, crud_model_id, model_id, context=None):
        """ When changing the object_write type configuration:

         - `current`: crud_model_id is the same as base model
         - `other`: disassemble the reference object to have its model
         - `expression`: has its own on_change, nothing special here
        """
        values = {}
        if use_write == 'current':
            values['crud_model_id'] = model_id
        elif use_write == 'other' and ref_object:
            ref_model, ref_id = ref_object.split(',')
            ref_model_id = self.pool['ir.model'].search(cr, uid, [('model', '=', ref_model)], context=context)[0]
            values['crud_model_id'] = ref_model_id
        elif use_write == 'expression':
            pass

        if values.get('crud_model_id') != crud_model_id:
            values['link_field_id'] = False
        return {'value': values}

    def on_change_write_expression(self, cr, uid, ids, write_expression, model_id, context=None):
        """ Check the write_expression and update crud_model_id accordingly """
        values = {}
        if write_expression:
            valid, model_name, message = self._check_expression(cr, uid, write_expression, model_id, context=context)
        else:
            valid, model_name, message = True, None, False
            if model_id:
                model_name = self.pool['ir.model'].browse(cr, uid, model_id, context).model
        if not valid:
            return {
                'warning': {
                    'title': 'Incorrect expression',
                    'message': message or 'Invalid expression',
                }
            }
        if model_name:
            ref_model_id = self.pool['ir.model'].search(cr, uid, [('model', '=', model_name)], context=context)[0]
            values['crud_model_id'] = ref_model_id
            return {'value': values}
        return {'value': {}}

    def on_change_crud_model_id(self, cr, uid, ids, crud_model_id, context=None):
        """ When changing the CRUD model, update its stored name also """
        crud_model_name = False
        if crud_model_id:
            crud_model_name = self.pool.get('ir.model').browse(cr, uid, crud_model_id, context).model
        values = {'link_field_id': False, 'crud_model_name': crud_model_name}
        return {'value': values}

    def _build_expression(self, field_name, sub_field_name):
        """ Returns a placeholder expression for use in a template field,
        based on the values provided in the placeholder assistant.

        :param field_name: main field name
        :param sub_field_name: sub field name (M2O)
        :return: final placeholder expression
        """
        expression = ''
        if field_name:
            expression = "object." + field_name
            if sub_field_name:
                expression += "." + sub_field_name
        return expression

    def onchange_sub_model_object_value_field(self, cr, uid, ids, model_object_field, sub_model_object_field=False, context=None):
        result = {
            'sub_object': False,
            'copyvalue': False,
            'sub_model_object_field': False,
        }
        if model_object_field:
            fields_obj = self.pool.get('ir.model.fields')
            field_value = fields_obj.browse(cr, uid, model_object_field, context)
            if field_value.ttype in ['many2one', 'one2many', 'many2many']:
                res_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', field_value.relation)], context=context)
                sub_field_value = False
                if sub_model_object_field:
                    sub_field_value = fields_obj.browse(cr, uid, sub_model_object_field, context)
                if res_ids:
                    result.update({
                        'sub_object': res_ids[0],
                        'copyvalue': self._build_expression(field_value.name, sub_field_value and sub_field_value.name or False),
                        'sub_model_object_field': sub_model_object_field or False,
                    })
            else:
                result.update({
                    'copyvalue': self._build_expression(field_value.name, False),
                })
        return {'value': result}

    def onchange_id_object(self, cr, uid, ids, id_object, context=None):
        if id_object:
            ref_model, ref_id = id_object.split(',')
            return {'value': {'id_value': ref_id}}
        return {'value': {'id_value': False}}

    def create_action(self, cr, uid, ids, context=None):
        """ Create a contextual action for each of the server actions. """
        for action in self.browse(cr, uid, ids, context=context):
            ir_values_id = self.pool.get('ir.values').create(cr, SUPERUSER_ID, {
                'name': _('Run %s') % action.name,
                'model': action.model_id.model,
                'key2': 'client_action_multi',
                'value': "ir.actions.server,%s" % action.id,
            }, context)
            action.write({
                'menu_ir_values_id': ir_values_id,
            })
        return True

    def unlink_action(self, cr, uid, ids, context=None):
        """ Remove the contextual actions created for the server actions. """
        self.check_access_rights(cr , uid, 'write', raise_exception=True)
        for action in self.browse(cr, uid, ids, context=context):
            if action.menu_ir_values_id:
                try:
                    self.pool.get('ir.values').unlink(cr, SUPERUSER_ID, action.menu_ir_values_id.id, context)
                except Exception:
                    raise UserError(_('Deletion of the action record failed.'))
        return True

    def run_action_client_action(self, cr, uid, action, eval_context=None, context=None):
        if not action.action_id:
            raise UserError(_("Please specify an action to launch!"))
        return self.pool[action.action_id.type].read(cr, uid, [action.action_id.id], context=context)[0]

    def run_action_code_multi(self, cr, uid, action, eval_context=None, context=None):
        eval(action.code.strip(), eval_context, mode="exec", nocopy=True)  # nocopy allows to return 'action'
        if 'action' in eval_context:
            return eval_context['action']

    def run_action_trigger(self, cr, uid, action, eval_context=None, context=None):
        """ Trigger a workflow signal, depending on the use_relational_model:

         - `base`: base_model_pool.signal_workflow(cr, uid, context.get('active_id'), <TRIGGER_NAME>)
         - `relational`: find the related model and object, using the relational
           field, then target_model_pool.signal_workflow(cr, uid, target_id, <TRIGGER_NAME>)
        """
        # weird signature and calling -> no self.env, use action param's
        record = action.env[action.model_id.model].browse(context['active_id'])
        if action.use_relational_model == 'relational':
            record = getattr(record, action.wkf_field_id.name)
            if not isinstance(record, openerp.models.BaseModel):
                record = action.env[action.wkf_model_id.model].browse(record)

        record.signal_workflow(action.wkf_transition_id.signal)

    def run_action_multi(self, cr, uid, action, eval_context=None, context=None):
        res = False
        for act in action.child_ids:
            result = self.run(cr, uid, [act.id], context=context)
            if result:
                res = result
        return res

    def run_action_object_write(self, cr, uid, action, eval_context=None, context=None):
        """ Write server action.

         - 1. evaluate the value mapping
         - 2. depending on the write configuration:

          - `current`: id = active_id
          - `other`: id = from reference object
          - `expression`: id = from expression evaluation
        """
        res = {}
        for exp in action.fields_lines:
            res[exp.col1.name] = exp.eval_value(eval_context=eval_context)[exp.id]

        if action.use_write == 'current':
            model = action.model_id.model
            ref_id = context.get('active_id')
        elif action.use_write == 'other':
            model = action.crud_model_id.model
            ref_id = action.ref_object.id
        elif action.use_write == 'expression':
            model = action.crud_model_id.model
            ref = eval(action.write_expression, eval_context)
            if isinstance(ref, browse_record):
                ref_id = getattr(ref, 'id')
            else:
                ref_id = int(ref)

        obj_pool = self.pool[model]
        obj_pool.write(cr, uid, [ref_id], res, context=context)

    def run_action_object_create(self, cr, uid, action, eval_context=None, context=None):
        """ Create and Copy server action.

         - 1. evaluate the value mapping
         - 2. depending on the write configuration:

          - `new`: new record in the base model
          - `copy_current`: copy the current record (id = active_id) + gives custom values
          - `new_other`: new record in target model
          - `copy_other`: copy the current record (id from reference object)
            + gives custom values
        """
        res = {}
        for exp in action.fields_lines:
            res[exp.col1.name] = exp.eval_value(eval_context=eval_context)[exp.id]

        if action.use_create in ['new', 'copy_current']:
            model = action.model_id.model
        elif action.use_create in ['new_other', 'copy_other']:
            model = action.crud_model_id.model

        obj_pool = self.pool[model]
        if action.use_create == 'copy_current':
            ref_id = context.get('active_id')
            res_id = obj_pool.copy(cr, uid, ref_id, res, context=context)
        elif action.use_create == 'copy_other':
            ref_id = action.ref_object.id
            res_id = obj_pool.copy(cr, uid, ref_id, res, context=context)
        else:
            res_id = obj_pool.create(cr, uid, res, context=context)

        if action.link_new_record and action.link_field_id:
            self.pool[action.model_id.model].write(cr, uid, [context.get('active_id')], {action.link_field_id.name: res_id})

    def _get_eval_context(self, cr, uid, action=None, context=None):
        """ Prepare the context used when evaluating python code, like the
        condition or code server actions.

        :param action: the current server action
        :type action: browse record
        :returns: dict -- evaluation context given to (safe_)eval """
        def log(message, level="info"):
            val = (uid, 'server', cr.dbname, __name__, level, message, "action", action.id, action.name)
            cr.execute("""
                INSERT INTO ir_logging(create_date, create_uid, type, dbname, name, level, message, path, line, func)
                VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, val)

        eval_context = super(ir_actions_server, self)._get_eval_context(cr, uid, action=action, context=context)
        obj_pool = self.pool[action.model_id.model]
        env = openerp.api.Environment(cr, uid, context)
        model = env[action.model_id.model]
        obj = None
        if context.get('active_model') == action.model_id.model and context.get('active_id'):
            obj = model.browse(context['active_id'])
        if context.get('onchange_self'):
            obj = context['onchange_self']
        eval_context.update({
            # orm
            'env': env,
            'model': model,
            'workflow': workflow,
            # Exceptions
            'Warning': openerp.exceptions.Warning,
            # record
            # TODO: When porting to master move badly named obj and object to
            # deprecated and define record (active_id) and records (active_ids)
            'object': obj,
            'obj': obj,
            # Deprecated use env or model instead
            'self': obj_pool,
            'pool': self.pool,
            'cr': cr,
            'context': context,
            'user': env.user,
            # helpers
            'log': log,
        })
        return eval_context

    def run(self, cr, uid, ids, context=None):
        """ Runs the server action. For each server action, the condition is
        checked. Note that a void (``False``) condition is considered as always
        valid. If it is verified, the run_action_<STATE> method is called. This
        allows easy overriding of the server actions.

        :param dict context: context should contain following keys

                             - active_id: id of the current object (single mode)
                             - active_model: current model that should equal the action's model

                             The following keys are optional:

                             - active_ids: ids of the current records (mass mode). If active_ids
                               and active_id are present, active_ids is given precedence.

        :return: an action_id to be executed, or False is finished correctly without
                 return action
        """
        if context is None:
            context = {}
        res = False
        for action in self.browse(cr, uid, ids, context):
            eval_context = self._get_eval_context(cr, uid, action, context=context)
            condition = action.condition
            if condition is False:
                # Void (aka False) conditions are considered as True
                condition = True
            if hasattr(self, 'run_action_%s_multi' % action.state):
                run_context = eval_context['context']
                expr = eval(str(condition), eval_context)
                if not expr:
                    continue
                # call the multi method
                func = getattr(self, 'run_action_%s_multi' % action.state)
                res = func(cr, uid, action, eval_context=eval_context, context=run_context)

            elif hasattr(self, 'run_action_%s' % action.state):
                func = getattr(self, 'run_action_%s' % action.state)
                active_id = context.get('active_id')
                active_ids = context.get('active_ids', [active_id] if active_id else [])
                for active_id in active_ids:
                    # run context dedicated to a particular active_id
                    run_context = dict(context, active_ids=[active_id], active_id=active_id)
                    eval_context["context"] = run_context
                    expr = eval(str(condition), eval_context)
                    if not expr:
                        continue
                    # call the single method related to the action: run_action_<STATE>
                    res = func(cr, uid, action, eval_context=eval_context, context=run_context)
        return res


class ir_server_object_lines(osv.osv):
    _name = 'ir.server.object.lines'
    _description = 'Server Action value mapping'
    _sequence = 'ir_actions_id_seq'

    _columns = {
        'server_id': fields.many2one('ir.actions.server', 'Related Server Action', ondelete='cascade'),
        'col1': fields.many2one('ir.model.fields', 'Field', required=True),
        'value': fields.text('Value', required=True, help="Expression containing a value specification. \n"
                                                          "When Formula type is selected, this field may be a Python expression "
                                                          " that can use the same values as for the condition field on the server action.\n"
                                                          "If Value type is selected, the value will be used directly without evaluation."),
        'type': fields.selection([
            ('value', 'Value'),
            ('equation', 'Python expression')
        ], 'Evaluation Type', required=True, change_default=True),
    }

    _defaults = {
        'type': 'value',
    }

    def eval_value(self, cr, uid, ids, eval_context=None, context=None):
        res = dict.fromkeys(ids, False)
        for line in self.browse(cr, uid, ids, context=context):
            expr = line.value
            if line.type == 'equation':
                expr = eval(line.value, eval_context)
            elif line.col1.ttype in ['many2one', 'integer']:
                try:
                    expr = int(line.value)
                except Exception:
                    pass
            res[line.id] = expr
        return res


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
        'state': fields.selection(TODO_STATES, string='Status', required=True),
        'name': fields.char('Name'),
        'type': fields.selection(TODO_TYPES, 'Type', required=True,
            help="""Manual: Launched manually.
Automatic: Runs whenever the system is reconfigured.
Launch Manually Once: after having been launched manually, it sets automatically to Done."""),
        'groups_id': fields.many2many('res.groups', 'res_groups_action_rel', 'uid', 'gid', 'Groups'),
        'note': fields.text('Text', translate=True),
    }
    _defaults={
        'state': 'open',
        'sequence': 10,
        'type': 'manual',
    }
    _order="sequence,id"

    @openerp.api.multi
    def unlink(self):
        if self:
            try:
                todo_open_menu = self.env.ref('base.open_menu')
                # don't remove base.open_menu todo but set its original action
                if todo_open_menu in self:
                    todo_open_menu.action_id = self.env.ref('base.action_client_base_menu').id
                    self -= todo_open_menu
            except ValueError:
                pass
        return super(ir_actions_todo, self).unlink()

    def name_get(self, cr, uid, ids, context=None):
        return [(rec.id, rec.action_id.name) for rec in self.browse(cr, uid, ids, context=context)]

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if args is None:
            args = []
        if name:
            ids = self.search(cr, user, [('action_id', operator, name)] + args, limit=limit)
            return self.name_get(cr, user, ids, context=context)
        return super(ir_actions_todo, self).name_search(cr, user, name, args=args, operator=operator, context=context, limit=limit)


    def action_launch(self, cr, uid, ids, context=None):
        """ Launch Action of Wizard"""
        wizard_id = ids and ids[0] or False
        wizard = self.browse(cr, uid, wizard_id, context=context)
        if wizard.type in ('automatic', 'once'):
            wizard.write({'state': 'done'})

        # Load action
        act_type = wizard.action_id.type

        res = self.pool[act_type].read(cr, uid, [wizard.action_id.id], [], context=context)[0]
        if act_type != 'ir.actions.act_window':
            return res
        res.setdefault('context','{}')

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


class ir_actions_act_client(osv.osv):
    _name = 'ir.actions.client'
    _inherit = 'ir.actions.actions'
    _table = 'ir_act_client'
    _sequence = 'ir_actions_id_seq'
    _order = 'name'

    def _get_params(self, cr, uid, ids, field_name, arg, context):
        result = {}
        # Need to remove bin_size from context, to obtains the binary and not the length.
        context = dict(context, bin_size_params_store=False)
        for record in self.browse(cr, uid, ids, context=context):
            result[record.id] = record.params_store and eval(record.params_store, {'uid': uid}) or False
        return result

    def _set_params(self, cr, uid, id, field_name, field_value, arg, context):
        if isinstance(field_value, dict):
            self.write(cr, uid, id, {'params_store': repr(field_value)}, context=context)
        else:
            self.write(cr, uid, id, {'params_store': field_value}, context=context)

    _columns = {
        'name': fields.char('Action Name', required=True, translate=True),
        'tag': fields.char('Client action tag', required=True,
                           help="An arbitrary string, interpreted by the client"
                                " according to its own needs and wishes. There "
                                "is no central tag repository across clients."),
        'res_model': fields.char('Destination Model', 
            help="Optional model, mostly used for needactions."),
        'context': fields.char('Context Value', required=True,
            help="Context dictionary as Python expression, empty by default (Default: {})"),
        'params': fields.function(_get_params, fnct_inv=_set_params,
                                  type='binary', 
                                  string="Supplementary arguments",
                                  help="Arguments sent to the client along with"
                                       "the view tag"),
        'params_store': fields.binary("Params storage", readonly=True)
    }
    _defaults = {
        'type': 'ir.actions.client',
        'context': '{}',

    }
