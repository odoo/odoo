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

from osv import fields,osv
from lxml import etree
from tools import graph
from tools.safe_eval import safe_eval as eval
import tools
from tools.view_validation import valid_view
import os
import logging

_logger = logging.getLogger(__name__)

class view_custom(osv.osv):
    _name = 'ir.ui.view.custom'
    _order = 'create_date desc'  # search(limit=1) should return the last customization
    _columns = {
        'ref_id': fields.many2one('ir.ui.view', 'Original View', select=True, required=True, ondelete='cascade'),
        'user_id': fields.many2one('res.users', 'User', select=True, required=True, ondelete='cascade'),
        'arch': fields.text('View Architecture', required=True),
    }

    def _auto_init(self, cr, context=None):
        super(view_custom, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'ir_ui_view_custom_user_id_ref_id\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_ui_view_custom_user_id_ref_id ON ir_ui_view_custom (user_id, ref_id)')
view_custom()

class view(osv.osv):
    _name = 'ir.ui.view'

    def _type_field(self, cr, uid, ids, name, args, context=None):
        result = {}
        for record in self.browse(cr, uid, ids, context):
            # Get the type from the inherited view if any.
            if record.inherit_id:
                result[record.id] = record.inherit_id.type
            else:
                result[record.id] = etree.fromstring(record.arch.encode('utf8')).tag
        return result

    _columns = {
        'name': fields.char('View Name',size=64,  required=True),
        'model': fields.char('Object', size=64, required=True, select=True),
        'priority': fields.integer('Sequence', required=True),
        'type': fields.function(_type_field, type='selection', selection=[
            ('tree','Tree'),
            ('form','Form'),
            ('mdx','mdx'),
            ('graph', 'Graph'),
            ('calendar', 'Calendar'),
            ('diagram','Diagram'),
            ('gantt', 'Gantt'),
            ('kanban', 'Kanban'),
            ('search','Search')], string='View Type', required=True, select=True, store=True),
        'arch': fields.text('View Architecture', required=True),
        'inherit_id': fields.many2one('ir.ui.view', 'Inherited View', ondelete='cascade', select=True),
        'field_parent': fields.char('Child Field',size=64),
        'xml_id': fields.function(osv.osv.get_xml_id, type='char', size=128, string="External ID",
                                  help="ID of the view defined in xml file"),
        'groups_id': fields.many2many('res.groups', 'ir_ui_view_group_rel', 'view_id', 'group_id',
            string='Groups', help="If this field is empty, the view applies to all users. Otherwise, the view applies to the users of those groups only."),
    }
    _defaults = {
        'arch': '<?xml version="1.0"?>\n<tree string="My view">\n\t<field name="name"/>\n</tree>',
        'priority': 16
    }
    _order = "priority,name"

    # Holds the RNG schema
    _relaxng_validator = None  

    def create(self, cr, uid, values, context=None):
        if 'type' in values:
            _logger.warning("Setting the `type` field is deprecated in the `ir.ui.view` model.")
        return super(osv.osv, self).create(cr, uid, values, context)

    def _relaxng(self):
        if not self._relaxng_validator:
            frng = tools.file_open(os.path.join('base','rng','view.rng'))
            try:
                relaxng_doc = etree.parse(frng)
                self._relaxng_validator = etree.RelaxNG(relaxng_doc)
            except Exception:
                _logger.exception('Failed to load RelaxNG XML schema for views validation')
            finally:
                frng.close()
        return self._relaxng_validator
        
        
    def _check_render_view(self, cr, uid, view, context=None):
        """Verify that the given view's hierarchy is valid for rendering, along with all the changes applied by
           its inherited views, by rendering it using ``fields_view_get()``.
           
           @param browse_record view: view to validate
           @return: the rendered definition (arch) of the view, always utf-8 bytestring (legacy convention)
               if no error occurred, else False.  
        """
        try:
            fvg = self.pool.get(view.model).fields_view_get(cr, uid, view_id=view.id, view_type=view.type, context=context)
            return fvg['arch']
        except:
            _logger.exception("Can't render view %s for model: %s", view.xml_id, view.model)
            return False

    def _check_xml(self, cr, uid, ids, context=None):
        for view in self.browse(cr, uid, ids, context):
            # Sanity check: the view should not break anything upon rendering!
            view_arch_utf8 = self._check_render_view(cr, uid, view, context=context)
            # always utf-8 bytestring - legacy convention
            if not view_arch_utf8: return False

            # RNG-based validation is not possible anymore with 7.0 forms
            # TODO 7.0: provide alternative assertion-based validation of view_arch_utf8
            view_docs = [etree.fromstring(view_arch_utf8)]
            if view_docs[0].tag == 'data':
                # A <data> element is a wrapper for multiple root nodes
                view_docs = view_docs[0]
            validator = self._relaxng()
            for view_arch in view_docs:
                if (view_arch.get('version') < '7.0') and validator and not validator.validate(view_arch):
                    for error in validator.error_log:
                        _logger.error(tools.ustr(error))
                    return False
                if not valid_view(view_arch):
                    return False
        return True

    _constraints = [
        (_check_xml, 'Invalid XML for View Architecture!', ['arch'])
    ]

    def _auto_init(self, cr, context=None):
        super(view, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'ir_ui_view_model_type_inherit_id\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_ui_view_model_type_inherit_id ON ir_ui_view (model, inherit_id)')

    def get_inheriting_views_arch(self, cr, uid, view_id, model, context=None):
        """Retrieves the architecture of views that inherit from the given view, from the sets of
           views that should currently be used in the system. During the module upgrade phase it
           may happen that a view is present in the database but the fields it relies on are not
           fully loaded yet. This method only considers views that belong to modules whose code
           is already loaded. Custom views defined directly in the database are loaded only
           after the module initialization phase is completely finished.

           :param int view_id: id of the view whose inheriting views should be retrieved
           :param str model: model identifier of the view's related model (for double-checking)
           :rtype: list of tuples
           :return: [(view_arch,view_id), ...]
        """
        user_groups = frozenset(self.pool.get('res.users').browse(cr, 1, uid, context).groups_id)
        if self.pool._init:
            # Module init currently in progress, only consider views from modules whose code was already loaded 
            query = """SELECT v.id FROM ir_ui_view v LEFT JOIN ir_model_data md ON (md.model = 'ir.ui.view' AND md.res_id = v.id)
                       WHERE v.inherit_id=%s AND v.model=%s AND md.module in %s  
                       ORDER BY priority"""
            query_params = (view_id, model, tuple(self.pool._init_modules))
        else:
            # Modules fully loaded, consider all views
            query = """SELECT v.id FROM ir_ui_view v
                       WHERE v.inherit_id=%s AND v.model=%s  
                       ORDER BY priority"""
            query_params = (view_id, model)
        cr.execute(query, query_params)
        view_ids = [v[0] for v in cr.fetchall()]
        # filter views based on user groups
        return [(view.arch, view.id)
                for view in self.browse(cr, 1, view_ids, context)
                if not (view.groups_id and user_groups.isdisjoint(view.groups_id))]

    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
        result = super(view, self).write(cr, uid, ids, vals, context)

        # drop the corresponding view customizations (used for dashboards for example), otherwise
        # not all users would see the updated views
        custom_view_ids = self.pool.get('ir.ui.view.custom').search(cr, uid, [('ref_id','in',ids)])
        if custom_view_ids:
            self.pool.get('ir.ui.view.custom').unlink(cr, uid, custom_view_ids)

        return result

    def graph_get(self, cr, uid, id, model, node_obj, conn_obj, src_node, des_node, label, scale, context=None):
        nodes=[]
        nodes_name=[]
        transitions=[]
        start=[]
        tres={}
        labels={}
        no_ancester=[]
        blank_nodes = []

        _Model_Obj=self.pool.get(model)
        _Node_Obj=self.pool.get(node_obj)
        _Arrow_Obj=self.pool.get(conn_obj)

        for model_key,model_value in _Model_Obj._columns.items():
                if model_value._type=='one2many':
                    if model_value._obj==node_obj:
                        _Node_Field=model_key
                        _Model_Field=model_value._fields_id
                    flag=False
                    for node_key,node_value in _Node_Obj._columns.items():
                        if node_value._type=='one2many':
                             if node_value._obj==conn_obj:
                                 if src_node in _Arrow_Obj._columns and flag:
                                    _Source_Field=node_key
                                 if des_node in _Arrow_Obj._columns and not flag:
                                    _Destination_Field=node_key
                                    flag = True

        datas = _Model_Obj.read(cr, uid, id, [],context)
        for a in _Node_Obj.read(cr,uid,datas[_Node_Field],[]):
            if a[_Source_Field] or a[_Destination_Field]:
                nodes_name.append((a['id'],a['name']))
                nodes.append(a['id'])
            else:
                blank_nodes.append({'id': a['id'],'name':a['name']})

            if a.has_key('flow_start') and a['flow_start']:
                start.append(a['id'])
            else:
                if not a[_Source_Field]:
                    no_ancester.append(a['id'])
            for t in _Arrow_Obj.read(cr,uid, a[_Destination_Field],[]):
                transitions.append((a['id'], t[des_node][0]))
                tres[str(t['id'])] = (a['id'],t[des_node][0])
                label_string = ""
                if label:
                    for lbl in eval(label):
                        if t.has_key(tools.ustr(lbl)) and tools.ustr(t[lbl])=='False':
                            label_string = label_string + ' '
                        else:
                            label_string = label_string + " " + tools.ustr(t[lbl])
                labels[str(t['id'])] = (a['id'],label_string)
        g  = graph(nodes, transitions, no_ancester)
        g.process(start)
        g.scale(*scale)
        result = g.result_get()
        results = {}
        for node in nodes_name:
            results[str(node[0])] = result[node[0]]
            results[str(node[0])]['name'] = node[1]
        return {'nodes': results,
                'transitions': tres,
                'label' : labels,
                'blank_nodes': blank_nodes,
                'node_parent_field': _Model_Field,}
view()

class view_sc(osv.osv):
    _name = 'ir.ui.view_sc'
    _columns = {
        'name': fields.char('Shortcut Name', size=64), # Kept for backwards compatibility only - resource name used instead (translatable)
        'res_id': fields.integer('Resource Ref.', help="Reference of the target resource, whose model/table depends on the 'Resource Name' field."),
        'sequence': fields.integer('Sequence'),
        'user_id': fields.many2one('res.users', 'User Ref.', required=True, ondelete='cascade', select=True),
        'resource': fields.char('Resource Name', size=64, required=True, select=True)
    }

    def _auto_init(self, cr, context=None):
        super(view_sc, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'ir_ui_view_sc_user_id_resource\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_ui_view_sc_user_id_resource ON ir_ui_view_sc (user_id, resource)')

    def get_sc(self, cr, uid, user_id, model='ir.ui.menu', context=None):
        ids = self.search(cr, uid, [('user_id','=',user_id),('resource','=',model)], context=context)
        results = self.read(cr, uid, ids, ['res_id'], context=context)
        name_map = dict(self.pool.get(model).name_get(cr, uid, [x['res_id'] for x in results], context=context))
        # Make sure to return only shortcuts pointing to exisintg menu items.
        filtered_results = filter(lambda result: result['res_id'] in name_map, results)
        for result in filtered_results:
            result.update(name=name_map[result['res_id']])
        return filtered_results

    _order = 'sequence,name'
    _defaults = {
        'resource': lambda *a: 'ir.ui.menu',
        'user_id': lambda obj, cr, uid, context: uid,
    }
    _sql_constraints = [
        ('shortcut_unique', 'unique(res_id, resource, user_id)', 'Shortcut for this menu already exists!'),
    ]

view_sc()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

