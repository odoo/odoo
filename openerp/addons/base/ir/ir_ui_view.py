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
import copy

import logging
import itertools
from lxml import etree
import os

from openerp import tools
from openerp.osv import fields,osv
from openerp.tools import graph, SKIPPED_ELEMENT_TYPES
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from openerp.tools.view_validation import valid_view

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

class view(osv.osv):
    _name = 'ir.ui.view'

    class NoViewError(Exception): pass
    class NoDefaultError(NoViewError): pass

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
        'name': fields.char('View Name', required=True),
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
        'model_ids': fields.one2many('ir.model.data', 'res_id', auto_join=True),
    }
    _defaults = {
        'arch': '<?xml version="1.0"?>\n<tree string="My view">\n\t<field name="name"/>\n</tree>',
        'priority': 16,
        'type': 'tree',
    }
    _order = "priority,name"

    # Holds the RNG schema
    _relaxng_validator = None

    def create(self, cr, uid, values, context=None):
        if 'type' in values:
            _logger.warning("Setting the `type` field is deprecated in the `ir.ui.view` model.")
        if not values.get('name'):
            if values.get('inherit_id'):
                inferred_type = self.browse(cr, uid, values['inherit_id'], context).type
            else:
                inferred_type = etree.fromstring(values['arch'].encode('utf8')).tag
            values['name'] = "%s %s" % (values['model'], inferred_type)
        return super(view, self).create(cr, uid, values, context)

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
            fvg = self.pool[view.model].fields_view_get(cr, uid, view_id=view.id, view_type=view.type, context=context)
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
        #(_check_xml, 'Invalid XML for View Architecture!', ['arch'])
    ]

    def _auto_init(self, cr, context=None):
        super(view, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'ir_ui_view_model_type_inherit_id\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_ui_view_model_type_inherit_id ON ir_ui_view (model, inherit_id)')

    def read_combined(self, cr, uid, view_id, view_type, model,
                      fields=None, fallback=None, context=None):
        """
        Utility function stringing together all method calls necessary to get
        a full, final view:

        * Gets the default view if no view_id is provided
        * Gets the top of the view tree if a sub-view is requested
        * Applies all inherited archs on the root view
        * Applies post-processing
        * Returns the view with all requested fields

          .. note:: ``arch`` is always added to the fields list even if not
                    requested (similar to ``id``)

        If no view is available (no view_id or invalid view_id provided, or
        no view stored for (model, view_type)) a view record will be fetched
        from the ``defaults`` mapping?

        :param fallback: a mapping of {view_type: view_dict}, if no view can
                         be found (read) will be used to provide a default
                         before post-processing
        :type fallback: mapping
        """
        if context is None: context = {}
        try:
            if not view_id:
                view_id = self.default_view(cr, uid, model, view_type, context=context)
            root_id = self.root_ancestor(cr, uid, view_id, context=context)

            if fields and 'arch' not in fields:
                fields = list(itertools.chain(['arch'], fields))

            [view] = self.read(cr, uid, [root_id], fields=fields, context=context)

            arch_tree = etree.fromstring(
                view['arch'].encode('utf-8') if isinstance(view['arch'], unicode)
                else view['arch'])
            descendants = self.iter(
                cr, uid, view['id'], model, exclude_base=True, context=context)
            arch = self.apply_inherited_archs(
                cr, uid, arch_tree, descendants,
                model, view['id'], context=context)

            if view['model'] != model:
                context = dict(context, base_model_name=view['model'])
        except self.NoViewError:
            # defaultdict is "empty" until first __getattr__
            if fallback is None: raise
            view = fallback[view_type]
            arch = view['arch']
            if isinstance(arch, basestring):
                arch = etree.fromstring(
                    arch.encode('utf-8') if isinstance(arch, unicode) else arch)

        # TODO: post-processing

        return dict(view, arch=etree.tostring(arch, encoding='utf-8'))

    def locate_node(self, arch, spec):
        """ Locate a node in a source (parent) architecture.

        Given a complete source (parent) architecture (i.e. the field
        `arch` in a view), and a 'spec' node (a node in an inheriting
        view that specifies the location in the source view of what
        should be changed), return (if it exists) the node in the
        source view matching the specification.

        :param arch: a parent architecture to modify
        :param spec: a modifying node in an inheriting view
        :return: a node in the source matching the spec

        """
        if spec.tag == 'xpath':
            nodes = arch.xpath(spec.get('expr'))
            return nodes[0] if nodes else None
        elif spec.tag == 'field':
            # Only compare the field name: a field can be only once in a given view
            # at a given level (and for multilevel expressions, we should use xpath
            # inheritance spec anyway).
            for node in arch.iter('field'):
                if node.get('name') == spec.get('name'):
                    return node
            return None

        for node in arch.iter(spec.tag):
            if isinstance(node, SKIPPED_ELEMENT_TYPES):
                continue
            if all(node.get(attr) == spec.get(attr) for attr in spec.attrib
                   if attr not in ('position','version')):
                # Version spec should match parent's root element's version
                if spec.get('version') and spec.get('version') != arch.get('version'):
                    return None
                return node
        return None

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

        conditions = [['inherit_id', '=', view_id], ['model', '=', model]]
        if self.pool._init:
            # Module init currently in progress, only consider views from
            # modules whose code is already loaded
            conditions.extend([
                ['model_ids.model', '=', 'ir.ui.view'],
                ['model_ids.module', 'in', tuple(self.pool._init_modules)],
            ])
        view_ids = self.search(cr, uid, conditions, context=context)

        # filter views based on user groups
        return [(view.arch, view.id)
                for view in self.browse(cr, 1, view_ids, context)
                if not (view.groups_id and user_groups.isdisjoint(view.groups_id))]

    def iter(self, cr, uid, view_id, model, exclude_base=False, context=None):
        """ iterates on all of ``view_id``'s descendants tree depth-first.

        If ``exclude_base`` is ``False``, also yields ``view_id`` itself. It is
        ``False`` by default to match the behavior of etree's Element.iter.

        :param int view_id: database id of the root view
        :param str model: name of the view's related model (for filtering)
        :param bool exclude_base: whether ``view_id`` should be excluded
                                  from the iteration
        :return: iterator of (database_id, arch_string) pairs for all
                 descendants of ``view_id`` (including ``view_id`` itself if
                 ``exclude_base`` is ``False``, the default)
        """
        if not exclude_base:
            base = self.browse(cr, uid, view_id, context=context)
            yield base.id, base.arch

        for arch, id in self.get_inheriting_views_arch(
                cr, uid, view_id, model, context=context):
            yield id, arch
            for info in self.iter(
                    cr, uid, id, model, exclude_base=True, context=None):
                yield info

    def default_view(self, cr, uid, model, view_type, context=None):
        """ Fetches the default view for the provided (model, view_type) pair:
         view with no parent (inherit_id=Fase) with the lowest priority.

        :param str model:
        :param int view_type:
        :return: id of the default view for the (model, view_type) pair
        :rtype: int
        """
        ids = self.search(cr, uid, [
            ['model', '=', model],
            ['type', '=', view_type],
            ['inherit_id', '=', False],
        ], limit=1, order='priority', context=context)
        if not ids:
            raise self.NoDefaultError(
                _("No default view of type %s for model %s") % (
                    view_type, model))
        return ids[0]

    def root_ancestor(self, cr, uid, view_id, context=None):
        """
        Fetches the id of the root of the view tree of which view_id is part

        If view_id is specified, view_type and model aren't needed (and the
        other way around)

        :param view_id: id of view to search the root ancestor of
        :return: id of the root view for the tree
        """
        view = self.browse(cr, uid, view_id, context=context)
        if not view.exists():
            raise self.NoViewError(
                _("No view for id %s, root ancestor not available") % view_id)

        # Search for a root (i.e. without any parent) view.
        while view.inherit_id:
            view = view.inherit_id

        return view.id

    def apply_inherited_archs(self, cr, uid, source, descendants,
                              model, source_view_id, context=None):
        """ Applies descendants to the ``source`` view, returns the result of
        the application.

        :param Element source: source arch to apply descendant on
        :param descendants: iterable of (id, arch_string) pairs of all
                            descendants in the view tree, depth-first,
                            excluding the base view
        :type descendants: iter((int, str))
        :return: new architecture etree produced by applying all descendants
                 on ``source``
        :rtype: Element
        """
        return reduce(
            lambda current_arch, descendant: self.apply_inheritance_specs(
                cr, uid, model, source_view_id, current_arch,
                *descendant, context=context),
            descendants, source)

    def raise_view_error(self, cr, uid, model, error_msg, view_id, child_view_id, context=None):
        view, child_view = self.browse(cr, uid, [view_id, child_view_id], context)
        error_msg = error_msg % {'parent_xml_id': view.xml_id}
        raise AttributeError("View definition error for inherited view '%s' on model '%s': %s"
                             %  (child_view.xml_id, model, error_msg))

    def apply_inheritance_specs(self, cr, uid, model, root_view_id, source, descendant_id, specs_arch, context=None):
        """ Apply an inheriting view (a descendant of the base view)

        Apply to a source architecture all the spec nodes (i.e. nodes
        describing where and what changes to apply to some parent
        architecture) given by an inheriting view.

        :param Element source: a parent architecture to modify
        :param descendant_id: the database id of the descendant
        :param specs_arch: a modifying architecture in an inheriting view
        :return: a modified source where the specs are applied
        :rtype: Element
        """
        if isinstance(specs_arch, unicode):
            specs_arch = specs_arch.encode('utf-8')
        specs_tree = etree.fromstring(specs_arch)
        # Queue of specification nodes (i.e. nodes describing where and
        # changes to apply to some parent architecture).
        specs = [specs_tree]

        while len(specs):
            spec = specs.pop(0)
            if isinstance(spec, SKIPPED_ELEMENT_TYPES):
                continue
            if spec.tag == 'data':
                specs += [ c for c in specs_tree ]
                continue
            node = self.locate_node(source, spec)
            if node is not None:
                pos = spec.get('position', 'inside')
                if pos == 'replace':
                    if node.getparent() is None:
                        source = copy.deepcopy(spec[0])
                    else:
                        for child in spec:
                            node.addprevious(child)
                        node.getparent().remove(node)
                elif pos == 'attributes':
                    for child in spec.getiterator('attribute'):
                        attribute = (child.get('name'), child.text and child.text.encode('utf8') or None)
                        if attribute[1]:
                            node.set(attribute[0], attribute[1])
                        else:
                            del(node.attrib[attribute[0]])
                else:
                    sib = node.getnext()
                    for child in spec:
                        if pos == 'inside':
                            node.append(child)
                        elif pos == 'after':
                            if sib is None:
                                node.addnext(child)
                                node = child
                            else:
                                sib.addprevious(child)
                        elif pos == 'before':
                            node.addprevious(child)
                        else:
                            self.raise_view_error(cr, uid, model, "Invalid position value: '%s'" % pos, root_view_id, descendant_id, context=context)
            else:
                attrs = ''.join([
                    ' %s="%s"' % (attr, spec.get(attr))
                    for attr in spec.attrib
                    if attr != 'position'
                ])
                tag = "<%s%s>" % (spec.tag, attrs)
                if spec.get('version') and spec.get('version') != source.get('version'):
                    self.raise_view_error(cr, uid, model, "Mismatching view API version for element '%s': %r vs %r in parent view '%%(parent_xml_id)s'" % \
                                        (tag, spec.get('version'), source.get('version')), root_view_id, descendant_id, context=context)
                self.raise_view_error(cr, uid, model, "Element '%s' not found in parent view '%%(parent_xml_id)s'" % tag, root_view_id, descendant_id, context=context)

        return source

    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, (list, tuple)):
            ids = [ids]

        # drop the corresponding view customizations (used for dashboards for example), otherwise
        # not all users would see the updated views
        custom_view_ids = self.pool.get('ir.ui.view.custom').search(cr, uid, [('ref_id','in',ids)])
        if custom_view_ids:
            self.pool.get('ir.ui.view.custom').unlink(cr, uid, custom_view_ids)

        return super(view, self).write(cr, uid, ids, vals, context)

    def graph_get(self, cr, uid, id, model, node_obj, conn_obj, src_node, des_node, label, scale, context=None):
        nodes=[]
        nodes_name=[]
        transitions=[]
        start=[]
        tres={}
        labels={}
        no_ancester=[]
        blank_nodes = []

        _Model_Obj = self.pool[model]
        _Node_Obj = self.pool[node_obj]
        _Arrow_Obj = self.pool[conn_obj]

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
                            label_string += ' '
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
        name_map = dict(self.pool[model].name_get(cr, uid, [x['res_id'] for x in results], context=context))
        # Make sure to return only shortcuts pointing to exisintg menu items.
        filtered_results = filter(lambda result: result['res_id'] in name_map, results)
        for result in filtered_results:
            result.update(name=name_map[result['res_id']])
        return filtered_results

    _order = 'sequence,name'
    _defaults = {
        'resource': 'ir.ui.menu',
        'user_id': lambda obj, cr, uid, context: uid,
    }
    _sql_constraints = [
        ('shortcut_unique', 'unique(res_id, resource, user_id)', 'Shortcut for this menu already exists!'),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

