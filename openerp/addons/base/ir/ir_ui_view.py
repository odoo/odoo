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
import collections
import copy
import logging
from lxml import etree
from operator import itemgetter
import os
import time

import HTMLParser
from lxml import etree

import openerp
from openerp import tools
from openerp.osv import fields, osv, orm
from openerp.tools import graph, SKIPPED_ELEMENT_TYPES
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.view_validation import valid_view
from openerp.tools import misc
from openerp.osv.orm import browse_record, browse_record_list

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
        'arch': fields.text('View Architecture', required=True),
        'inherit_id': fields.many2one('ir.ui.view', 'Inherited View', ondelete='cascade', select=True),
        'inherit_children_ids': fields.one2many('ir.ui.view','inherit_id', 'Inherit Views'),
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
        if context is None:
            context = {}
        context['check_view_ids'] = ids

        for view in self.browse(cr, uid, ids, context):
            # Sanity check: the view should not break anything upon rendering!
            try:
                fvg = self.read_combined(cr, uid, view.id, None, context=context)
                view_arch_utf8 = fvg['arch']
            except Exception, e:
                _logger.exception(e)
                return False
            if view.type != 'qweb':
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

    def create(self, cr, uid, values, context=None):
        if 'type' not in values:
            if values.get('inherit_id'):
                values['type'] = self.browse(cr, uid, values['inherit_id'], context).type
            else:
                values['type'] = etree.fromstring(values['arch']).tag

        if not values.get('name'):
            values['name'] = "%s %s" % (values['model'], values['type'])

        self.read_template.clear_cache(self)
        return super(view, self).create(cr, uid, values, context)

    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, (list, tuple)):
            ids = [ids]

        # drop the corresponding view customizations (used for dashboards for example), otherwise
        # not all users would see the updated views
        custom_view_ids = self.pool.get('ir.ui.view.custom').search(cr, uid, [('ref_id','in',ids)])
        if custom_view_ids:
            self.pool.get('ir.ui.view.custom').unlink(cr, uid, custom_view_ids)

        self.read_template.clear_cache(self)
        return super(view, self).write(cr, uid, ids, vals, context)

    # default view selection

    def default_view(self, cr, uid, model, view_type, context=None):
        """ Fetches the default view for the provided (model, view_type) pair:
         view with no parent (inherit_id=Fase) with the lowest priority.

        :param str model:
        :param int view_type:
        :return: id of the default view of False if none found
        :rtype: int
        """
        domain = [
            ['model', '=', model],
            ['type', '=', view_type],
            ['inherit_id', '=', False],
        ]
        ids = self.search(cr, uid, domain, limit=1, order='priority', context=context)
        if not ids:
            return False
        return ids[0]

    # inheritance

    def get_inheriting_views_arch(self, cr, uid, view_id, model, context=None):
        """Retrieves the architecture of views that inherit from the given view, from the sets of
           views that should currently be used in the system. During the module upgrade phase it
           may happen that a view is present in the database but the fields it relies on are not
           fully loaded yet. This method only considers views that belong to modules whose code
           is already loaded. Custom views defined directly in the database are loaded only
           after the module initialization phase is completely finished.

           :param int view_id: id of the view whose inheriting views should be retrieved
           :param str model: model identifier of the inheriting views.
           :rtype: list of tuples
           :return: [(view_arch,view_id), ...]
        """

        user_groups = frozenset(self.pool.get('res.users').browse(cr, 1, uid, context).groups_id)

        check_view_ids = context and context.get('check_view_ids') or (0,)
        conditions = [['inherit_id', '=', view_id], ['model', '=', model]]
        if self.pool._init:
            # Module init currently in progress, only consider views from
            # modules whose code is already loaded
            conditions.extend([
                ['model_ids.model', '=', 'ir.ui.view'],
                '|',
                ['model_ids.module', 'in', tuple(self.pool._init_modules)],
                ['id', 'in', check_view_ids],
            ])
        view_ids = self.search(cr, uid, conditions, context=context)

        return [(view.arch, view.id)
                for view in self.browse(cr, 1, view_ids, context)
                if not (view.groups_id and user_groups.isdisjoint(view.groups_id))]

    def raise_view_error(self, cr, uid, message, view_id, context=None):
        view = self.browse(cr, uid, [view_id], context)[0]
        message = "Inherit error: %s view_id: %s, xml_id: %s, model: %s, parent_view: %s" % (message, view_id, view.xml_id, view.model, view.inherit_id)
        raise AttributeError(message)

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

    def inherit_branding(self, specs_tree, view_id, source_id):
        for node in specs_tree.iterchildren(tag=etree.Element):
            xpath = node.getroottree().getpath(node)
            if node.tag == 'data' or node.tag == 'xpath':
                self.inherit_branding(node, view_id, source_id)
            else:
                node.set('data-oe-id', str(view_id))
                node.set('data-oe-source-id', str(source_id))
                node.set('data-oe-xpath', xpath)
                node.set('data-oe-model', 'ir.ui.view')
                node.set('data-oe-field', 'arch')

        return specs_tree

    def apply_inheritance_specs(self, cr, uid, source, specs_tree, inherit_id, context=None):
        """ Apply an inheriting view (a descendant of the base view)

        Apply to a source architecture all the spec nodes (i.e. nodes
        describing where and what changes to apply to some parent
        architecture) given by an inheriting view.

        :param Element source: a parent architecture to modify
        :param Elepect specs_tree: a modifying architecture in an inheriting view
        :param inherit_id: the database id of specs_arch
        :return: a modified source where the specs are applied
        :rtype: Element
        """
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
                            self.raise_view_error(cr, uid, "Invalid position value: '%s'" % pos, inherit_id, context=context)
            else:
                attrs = ''.join([
                    ' %s="%s"' % (attr, spec.get(attr))
                    for attr in spec.attrib
                    if attr != 'position'
                ])
                tag = "<%s%s>" % (spec.tag, attrs)
                self.raise_view_error(cr, uid, "Element '%s' not found in parent view " % tag, inherit_id, context=context)

        return source

    def apply_view_inheritance(self, cr, uid, source, source_id, model, context=None):
        """ Apply all the (directly and indirectly) inheriting views.

        :param source: a parent architecture to modify (with parent modifications already applied)
        :param source_id: the database view_id of the parent view
        :param model: the original model for which we create a view (not
            necessarily the same as the source's model); only the inheriting
            views with that specific model will be applied.
        :return: a modified source where all the modifying architecture are applied
        """
        if context is None: context = {}
        sql_inherit = self.pool.get('ir.ui.view').get_inheriting_views_arch(cr, uid, source_id, model, context=context)
        for (specs, view_id) in sql_inherit:
            specs_tree = etree.fromstring(specs.encode('utf-8'))
            if context.get('inherit_branding'):
                self.inherit_branding(specs_tree, view_id, source_id)
            source = self.apply_inheritance_specs(cr, uid, source, specs_tree, view_id, context=context)
            source = self.apply_view_inheritance(cr, uid, source, view_id, model, context=context)
        return source

    def read_combined(self, cr, uid, view_id, fields=None, context=None):
        """
        Utility function to get a view combined with its inherited views.

        * Gets the top of the view tree if a sub-view is requested
        * Applies all inherited archs on the root view
        * Returns the view with all requested fields
          .. note:: ``arch`` is always added to the fields list even if not
                    requested (similar to ``id``)
        """
        if context is None: context = {}

        # if view_id is not a root view, climb back to the top.
        v = self.browse(cr, uid, view_id, context=context)
        while v.inherit_id:
            v = v.inherit_id
        root_id = v.id

        # arch and model fields are always returned
        if fields:
            fields = list(set(fields) | set(['arch', 'model']))

        # read the view arch
        [view] = self.read(cr, uid, [root_id], fields=fields, context=context)
        arch_tree = etree.fromstring(view['arch'].encode('utf-8'))

        if context.get('inherit_branding'):
            arch_tree.attrib.update({
                'data-oe-model': 'ir.ui.view',
                'data-oe-id': str(root_id),
                'data-oe-field': 'arch',
            })

        # and apply inheritance
        arch = self.apply_view_inheritance(cr, uid, arch_tree, root_id, v.model, context=context)

        return dict(view, arch=etree.tostring(arch, encoding='utf-8'))

    # postprocessing: groups, modifiers, ...

    def postprocess(self, cr, user, model, node, view_id, in_tree_view, model_fields, context=None):
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
                xarch, xfields = self.postprocess_and_fields(cr, user, node.get('object'), new_xml, view_id, ctx)
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
                            xarch, xfields = self.postprocess_and_fields(cr, user, column._obj or None, f, view_id, ctx)
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
                fields.update(self.postprocess(cr, user, model, f, view_id, in_tree_view, model_fields, context))

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

    def postprocess_and_fields(self, cr, user, model, node, view_id, context=None):
        """ Return an architecture and a description of all the fields.

        The field description combines the result of fields_get() and
        postprocess().

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

        fields_def = self.postprocess(cr, user, model, node, view_id, False, fields, context=context)
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

    # view used as templates

    @tools.ormcache_context(accepted_keys=('lang','inherit_branding'))
    def read_template(self, cr, uid, id_, context=None):
        try:
            id_ = int(id_)
        except ValueError:
            if '.' not in id_:
                raise ValueError('Invalid id: %r' % (id_,))
            IMD = self.pool['ir.model.data']
            m, _, n = id_.partition('.')
            _, id_ = IMD.get_object_reference(cr, uid, m, n)

        arch = self.read_combined(cr, uid, id_, fields=['arch'], context=context)['arch']
        arch_tree = etree.fromstring(arch)

        if 'lang' in context:
            arch_tree = self.translate_qweb(cr, uid, id_, arch_tree, context['lang'], context)
        self.distribute_branding(arch_tree)
        root = etree.Element('tpl')
        root.append(arch_tree)
        arch = etree.tostring(root, encoding='utf-8', xml_declaration=True)
        return arch

    def distribute_branding(self, e, branding=None, parent_xpath='',
                            index_map=misc.ConstantMapping(1)):
        if e.get('t-ignore') or e.tag == 'head':
            # TODO: find a better name and check if we have a string to boolean helper
            return

        node_path = e.get('data-oe-xpath')
        if node_path is None:
            node_path = "%s/%s[%d]" % (parent_xpath, e.tag, index_map[e.tag])
        if branding and not (e.get('data-oe-model') or e.get('t-field')):
            e.attrib.update(branding)
            e.set('data-oe-xpath', node_path)
        if not e.get('data-oe-model'): return

        # if a branded element contains branded elements distribute own
        # branding to children unless it's t-raw, then just remove branding
        # on current element
        if e.tag == 't' or 't-raw' in e.attrib or \
                any(self.is_node_branded(child) for child in e.iterdescendants()):
            distributed_branding = dict(
                (attribute, e.attrib.pop(attribute))
                for attribute in MOVABLE_BRANDING
                if e.get(attribute))

            if 't-raw' not in e.attrib:
                # TODO: collections.Counter if remove p2.6 compat
                # running index by tag type, for XPath query generation
                indexes = collections.defaultdict(lambda: 0)
                for child in e.iterchildren(tag=etree.Element):
                    indexes[child.tag] += 1
                    self.distribute_branding(child, distributed_branding,
                                             parent_xpath=node_path,
                                             index_map=indexes)

    def is_node_branded(self, node):
        """ Finds out whether a node is branded or qweb-active (bears a
        @data-oe-model or a @t-* *which is not t-field* as t-field does not
        section out views)

        :param node: an etree-compatible element to test
        :type node: etree._Element
        :rtype: boolean
        """
        return any(
            (attr == 'data-oe-model' or (attr != 't-field' and attr.startswith('t-')))
            for attr in node.attrib
        )

    def translate_qweb(self, cr, uid, id_, arch, lang, context=None):
        # TODO: this should be moved in a place before inheritance is applied
        #       but process() is only called on fields_view_get()
        Translations = self.pool['ir.translation']
        h = HTMLParser.HTMLParser()
        def get_trans(text):
            if not text or not text.strip():
                return None
            text = h.unescape(text.strip())
            if len(text) < 2 or (text.startswith('<!') and text.endswith('>')):
                return None
            # if text == 'Our Events':
            #     from pudb import set_trace;set_trace() ############################## Breakpoint ##############################
            return Translations._get_source(cr, uid, 'website', 'view', lang, text, id_)

        if arch.tag not in ['script']:
            text = get_trans(arch.text)
            if text:
                arch.text = arch.text.replace(arch.text.strip(), text)
            tail = get_trans(arch.tail)
            if tail:
                arch.tail = arch.tail.replace(arch.tail.strip(), tail)

            for attr_name in ('title', 'alt', 'placeholder'):
                attr = get_trans(arch.get(attr_name))
                if attr:
                    arch.set(attr_name, attr)
            for node in arch.iterchildren("*"):
                self.translate_qweb(cr, uid, id_, node, lang, context)
        return arch

    def render(self, cr, uid, id_or_xml_id, values=None, engine='ir.qweb', context=None):
        if not context:
            context = {}

        def loader(name):
            return self.read_template(cr, uid, name, context=context)

        return self.pool[engine].render(
            cr, uid, id_or_xml_id, values,
            loader=loader, undefined_handler=lambda key, v: None,
            context=context)

    # maybe used to print the workflow ?

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

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'model_ids': [],
        })
        return super(view, self).copy(cr, uid, id, default, context=context)

    def _validate_custom_views(self, cr, uid, model):
        """Validate architecture of custom views (= without xml id) for a given model.
            This method is called at the end of registry update.
        """
        cr.execute("""SELECT max(v.id)
                        FROM ir_ui_view v
                   LEFT JOIN ir_model_data md ON (md.model = 'ir.ui.view' AND md.res_id = v.id)
                       WHERE md.module IS NULL
                         AND v.model = %s
                    GROUP BY coalesce(v.inherit_id, v.id)
                   """, (model,))

        ids = map(itemgetter(0), cr.fetchall())
        return self._check_xml(cr, uid, ids)

MOVABLE_BRANDING = ['data-oe-model', 'data-oe-id', 'data-oe-field', 'data-oe-xpath']
