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
from functools import partial
import itertools
import logging
import os
import sys
import time

from lxml import etree

from openerp import tools
from openerp.modules import module
from openerp.osv import fields, osv, orm
from openerp.tools import graph, SKIPPED_ELEMENT_TYPES
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from openerp.tools.view_validation import valid_view
from openerp.tools import misc, qweb

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

    def _arch_get(self, cr, uid, ids, name, arg, context=None):
        """
        For each id being read, return arch_db or the content of arch_file
        """
        result = {}
        for record in self.read(cr, uid, ids, ['arch_file', 'arch_db'], context=context):
            if record['arch_db']:
                result[record['id']] = record['arch_db']
                continue

            view_module, path = record['arch_file'].split('/', 1)
            arch_path = module.get_module_resource(view_module, path)
            if not arch_path:
                raise IOError("No file '%s' in module '%s'" % (path, view_module))

            with misc.file_open(arch_path) as f:
                result[record['id']] = f.read().decode('utf-8')

        return result

    def _arch_set(self, cr, uid, id, name, value, arg, context=None):
        """
        Forward writing to arch_db
        """
        self.write(cr, uid, id, {'arch_db': value}, context=context)

    _columns = {
        'name': fields.char('View Name', required=True),
        'model': fields.char('Object', size=64, select=True),
        'priority': fields.integer('Sequence', required=True),
        'type': fields.selection([
            ('tree','Tree'),
            ('form','Form'),
            ('mdx','mdx'),
            ('graph', 'Graph'),
            ('calendar', 'Calendar'),
            ('diagram','Diagram'),
            ('gantt', 'Gantt'),
            ('kanban', 'Kanban'),
            ('search','Search'),
            ('qweb', 'QWeb')], string='View Type'),
        'arch_file': fields.char("View path"),
        'arch_db': fields.text("Arch content", oldname='arch'),
        'arch': fields.function(_arch_get, fnct_inv=_arch_set, store=False, string="View Architecture", type='text', nodrop=True),
        'inherit_id': fields.many2one('ir.ui.view', 'Inherited View', ondelete='cascade', select=True),
        'field_parent': fields.char('Child Field',size=64),
        'xml_id': fields.function(osv.osv.get_xml_id, type='char', size=128, string="External ID",
                                  help="ID of the view defined in xml file"),
        'groups_id': fields.many2many('res.groups', 'ir_ui_view_group_rel', 'view_id', 'group_id',
            string='Groups', help="If this field is empty, the view applies to all users. Otherwise, the view applies to the users of those groups only."),
        'model_ids': fields.one2many('ir.model.data', 'res_id', auto_join=True),
    }
    _defaults = {
        'priority': 16,
    }
    _order = "priority,name"

    # Holds the RNG schema
    _relaxng_validator = None

    def create(self, cr, uid, values, context=None):
        if not 'type' in values:
            if values.get('inherit_id'):
                values['type'] = self.browse(cr, uid, values['inherit_id'], context).type
            else:
                values['type'] = etree.fromstring(values['arch'].encode('utf8')).tag
        if not values.get('name'):
            values['name'] = "%s %s" % (values['model'], values[''])
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

    def _check_xml(self, cr, uid, ids, context=None):
        for view in self.browse(cr, uid, ids, context):
            # Sanity check: the view should not break anything upon rendering!
            try:
                fvg = self.read_combined(cr, uid, view.id, view.type, view.model, context=context)
                view_arch_utf8 = fvg['arch']
            except Exception, e:
                _logger.exception(e)
                return False

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

    def _check_model(self, cr, uid, ids, context=None):
        for view in self.browse(cr, uid, ids, context):
            if view.model and view.model not in self.pool:
                return False
        return True

    _constraints = [
        (_check_xml, 'Invalid XML for View Architecture!', ['arch'])
        #(_check_model, 'The model name does not exist.', ['model']),
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

            if fields:
                needed_fields = ['arch', 'model']
                fields = list(itertools.chain(
                    [field for field in needed_fields if field not in fields],
                    fields))

            [view] = self.read(cr, uid, [root_id], fields=fields, context=context)

            arch_tree = etree.fromstring(
                view['arch'].encode('utf-8') if isinstance(view['arch'], unicode)
                else view['arch'])
            descendants = self.iter(
                cr, uid, view['id'], model, exclude_base=True, context=context)


            arch = self.apply_inherited_archs(
                cr, uid, arch_tree, descendants,
                model, view['id'], context=context)

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

    # this really needs to be refixtored
    def __view_look_dom(self, cr, user, model, node, view_id, in_tree_view, model_fields, context=None):
        """Return the description of the fields in the node.

        In a normal call to this method, node is a complete view architecture
        but it is actually possible to give some sub-node (this is used so
        that the method can call itself recursively).

        Originally, the field descriptions are drawn from the node itself.
        But there is now some code calling fields_get() in order to merge some
        of those information in the architecture.

        """
        if context is None:
            context = {}
        result = False
        fields = {}
        children = True

        modifiers = {}
        Model = self.pool.get(model)

        def encode(s):
            if isinstance(s, unicode):
                return s.encode('utf8')
            return s

        def check_group(node):
            """Apply group restrictions,  may be set at view level or model level::
               * at view level this means the element should be made invisible to
                 people who are not members
               * at model level (exclusively for fields, obviously), this means
                 the field should be completely removed from the view, as it is
                 completely unavailable for non-members

               :return: True if field should be included in the result of fields_view_get
            """
            if Model and node.tag == 'field' and node.get('name') in Model._all_columns:
                column = Model._all_columns[node.get('name')].column
                if column.groups and not self.user_has_groups(
                        cr, user, groups=column.groups, context=context):
                    node.getparent().remove(node)
                    fields.pop(node.get('name'), None)
                    # no point processing view-level ``groups`` anymore, return
                    return False
            if node.get('groups'):
                can_see = self.user_has_groups(
                    cr, user, groups=node.get('groups'), context=context)
                if not can_see:
                    node.set('invisible', '1')
                    modifiers['invisible'] = True
                    if 'attrs' in node.attrib:
                        del(node.attrib['attrs']) #avoid making field visible later
                del(node.attrib['groups'])
            return True

        if node.tag in ('field', 'node', 'arrow'):
            if node.get('object'):
                attrs = {}
                views = {}
                xml = "<form>"
                for f in node:
                    if f.tag == 'field':
                        xml += etree.tostring(f, encoding="utf-8")
                xml += "</form>"
                new_xml = etree.fromstring(encode(xml))
                ctx = context.copy()
                ctx['base_model_name'] = model
                xarch, xfields = self.__view_look_dom_arch(cr, user, node.get('object'), new_xml, view_id, ctx)
                views['form'] = {
                    'arch': xarch,
                    'fields': xfields
                }
                attrs = {'views': views}
                fields = xfields
            if node.get('name'):
                attrs = {}
                try:
                    if node.get('name') in Model._columns:
                        column = Model._columns[node.get('name')]
                    else:
                        column = Model._inherit_fields[node.get('name')][2]
                except Exception:
                    column = False

                if column:
                    relation = self.pool[column._obj] if column._obj else None

                    children = False
                    views = {}
                    for f in node:
                        if f.tag in ('form', 'tree', 'graph', 'kanban'):
                            node.remove(f)
                            ctx = context.copy()
                            ctx['base_model_name'] = Model
                            xarch, xfields = self.__view_look_dom_arch(cr, user, column._obj or None, f, view_id, ctx)
                            views[str(f.tag)] = {
                                'arch': xarch,
                                'fields': xfields
                            }
                    attrs = {'views': views}
                    if node.get('widget') and node.get('widget') == 'selection':
                        # Prepare the cached selection list for the client. This needs to be
                        # done even when the field is invisible to the current user, because
                        # other events could need to change its value to any of the selectable ones
                        # (such as on_change events, refreshes, etc.)

                        # If domain and context are strings, we keep them for client-side, otherwise
                        # we evaluate them server-side to consider them when generating the list of
                        # possible values
                        # TODO: find a way to remove this hack, by allow dynamic domains
                        dom = []
                        if column._domain and not isinstance(column._domain, basestring):
                            dom = list(column._domain)
                        dom += eval(node.get('domain', '[]'), {'uid': user, 'time': time})
                        search_context = dict(context)
                        if column._context and not isinstance(column._context, basestring):
                            search_context.update(column._context)
                        attrs['selection'] = relation._name_search(cr, user, '', dom, context=search_context, limit=None, name_get_uid=1)
                        if (node.get('required') and not int(node.get('required'))) or not column.required:
                            attrs['selection'].append((False, ''))
                fields[node.get('name')] = attrs

                field = model_fields.get(node.get('name'))
                if field:
                    orm.transfer_field_to_modifiers(field, modifiers)


        elif node.tag in ('form', 'tree'):
            result = Model.view_header_get(cr, user, False, node.tag, context)
            if result:
                node.set('string', result)
            in_tree_view = node.tag == 'tree'

        elif node.tag == 'calendar':
            for additional_field in ('date_start', 'date_delay', 'date_stop', 'color'):
                if node.get(additional_field):
                    fields[node.get(additional_field)] = {}

        if not check_group(node):
            # node must be removed, no need to proceed further with its children
            return fields

        # The view architeture overrides the python model.
        # Get the attrs before they are (possibly) deleted by check_group below
        orm.transfer_node_to_modifiers(node, modifiers, context, in_tree_view)

        # TODO remove attrs couterpart in modifiers when invisible is true ?

        # translate view
        if 'lang' in context:
            Translations = self.pool['ir.translation']
            if node.text and node.text.strip():
                trans = Translations._get_source(cr, user, model, 'view', context['lang'], node.text.strip())
                if trans:
                    node.text = node.text.replace(node.text.strip(), trans)
            if node.tail and node.tail.strip():
                trans = Translations._get_source(cr, user, model, 'view', context['lang'], node.tail.strip())
                if trans:
                    node.tail =  node.tail.replace(node.tail.strip(), trans)

            if node.get('string') and not result:
                trans = Translations._get_source(cr, user, model, 'view', context['lang'], node.get('string'))
                if trans == node.get('string') and ('base_model_name' in context):
                    # If translation is same as source, perhaps we'd have more luck with the alternative model name
                    # (in case we are in a mixed situation, such as an inherited view where parent_view.model != model
                    trans = Translations._get_source(cr, user, context['base_model_name'], 'view', context['lang'], node.get('string'))
                if trans:
                    node.set('string', trans)

            for attr_name in ('confirm', 'sum', 'avg', 'help', 'placeholder'):
                attr_value = node.get(attr_name)
                if attr_value:
                    trans = Translations._get_source(cr, user, model, 'view', context['lang'], attr_value)
                    if trans:
                        node.set(attr_name, trans)

        for f in node:
            if children or (node.tag == 'field' and f.tag in ('filter','separator')):
                fields.update(self.__view_look_dom(cr, user, model, f, view_id, in_tree_view, model_fields, context))

        orm.transfer_modifiers_to_node(modifiers, node)
        return fields

    def _disable_workflow_buttons(self, cr, user, model, node):
        """ Set the buttons in node to readonly if the user can't activate them. """
        if model is None or user == 1:
            # admin user can always activate workflow buttons
            return node

        # TODO handle the case of more than one workflow for a model or multiple
        # transitions with different groups and same signal
        usersobj = self.pool.get('res.users')
        buttons = (n for n in node.getiterator('button') if n.get('type') != 'object')
        for button in buttons:
            user_groups = usersobj.read(cr, user, [user], ['groups_id'])[0]['groups_id']
            cr.execute("""SELECT DISTINCT t.group_id
                        FROM wkf
                  INNER JOIN wkf_activity a ON a.wkf_id = wkf.id
                  INNER JOIN wkf_transition t ON (t.act_to = a.id)
                       WHERE wkf.osv = %s
                         AND t.signal = %s
                         AND t.group_id is NOT NULL
                   """, (model, button.get('name')))
            group_ids = [x[0] for x in cr.fetchall() if x[0]]
            can_click = not group_ids or bool(set(user_groups).intersection(group_ids))
            button.set('readonly', str(int(not can_click)))
        return node

    def __view_look_dom_arch(self, cr, user, model, node, view_id, context=None):
        """ Return an architecture and a description of all the fields.

        The field description combines the result of fields_get() and
        __view_look_dom().

        :param node: the architecture as as an etree
        :return: a tuple (arch, fields) where arch is the given node as a
            string and fields is the description of all the fields.

        """
        fields = {}
        Model = self.pool.get(model)

        if node.tag == 'diagram':
            if node.getchildren()[0].tag == 'node':
                node_model = self.pool[node.getchildren()[0].get('object')]
                node_fields = node_model.fields_get(cr, user, None, context)
                fields.update(node_fields)
                if not node.get("create") and not node_model.check_access_rights(cr, user, 'create', raise_exception=False):
                    node.set("create", 'false')
            if node.getchildren()[1].tag == 'arrow':
                arrow_fields = self.pool[node.getchildren()[1].get('object')].fields_get(cr, user, None, context)
                fields.update(arrow_fields)
        elif Model:
            fields = Model.fields_get(cr, user, None, context)

        fields_def = self.__view_look_dom(cr, user, model, node, view_id, False, fields, context=context)
        node = self._disable_workflow_buttons(cr, user, model, node)
        if node.tag in ('kanban', 'tree', 'form', 'gantt'):
            for action, operation in (('create', 'create'), ('delete', 'unlink'), ('edit', 'write')):
                if not node.get(action) and not Model.check_access_rights(cr, user, operation, raise_exception=False):
                    node.set(action, 'false')
        arch = etree.tostring(node, encoding="utf-8").replace('\t', '')
        for k in fields.keys():
            if k not in fields_def:
                del fields[k]
        for field in fields_def:
            if field == 'id':
                # sometime, the view may contain the (invisible) field 'id' needed for a domain (when 2 objects have cross references)
                fields['id'] = {'readonly': True, 'type': 'integer', 'string': 'ID'}
            elif field in fields:
                fields[field].update(fields_def[field])
            else:
                cr.execute('select name, model from ir_ui_view where (id=%s or inherit_id=%s) and arch like %s', (view_id, view_id, '%%%s%%' % field))
                res = cr.fetchall()[:]
                model = res[0][1]
                res.insert(0, ("Can't find field '%s' in the following view parts composing the view of object model '%s':" % (field, model), None))
                msg = "\n * ".join([r[0] for r in res])
                msg += "\n\nEither you wrongly customized this view, or some modules bringing those views are not compatible with your current data model"
                _logger.error(msg)
                raise orm.except_orm('View error', msg)
        return arch, fields

    def _get_arch(self, cr, uid, id_, context=None):
        from pprint import pprint as pp
        pp(id_)
        try:
            id_ = int(id_)
        except ValueError:
            if '/' not in id_ and '.' not in id_:
                raise ValueError('Invalid id: %r' % (id_,))
            s = id_.find('/')
            s = s if s >= 0 else sys.maxint
            d = id_.find('.')
            d = d if d >= 0 else sys.maxint

            if d < s:
                # xml id
                IMD = self.pool['ir.model.data']
                m, _, n = id_.partition('.')
                _, id_ = IMD.get_object_reference(cr, uid, m, n)
            else:
                # path id => read directly on disk
                # TODO apply inheritence
                try:
                    with misc.file_open(id_) as f:
                        return f.read().decode('utf-8')
                except Exception:
                    raise ValueError('Invalid id: %r' % (id_,))

        pp(id_)
        r = self.read_combined(cr, uid, id_, fields=['arch'], view_type=None, model=None, context=context)
        pp(r)
        return r['arch']

    def render(self, cr, uid, id_or_xml_id, values, context=None):
        def loader(name):
            arch = self._get_arch(cr, uid, name, context=context)
            # parse arch
            # on the root tag of arch add the attribute t-name="<name>"
            arch = u'<?xml version="1.0" encoding="utf-8"?><tpl><t t-name="{0}">{1}</t></tpl>'.format(name, arch)
            return arch
        engine = qweb.QWebXml(loader)
        return engine.render(id_or_xml_id, values)

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

