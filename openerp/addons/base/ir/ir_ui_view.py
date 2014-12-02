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
import datetime
import dateutil
from dateutil.relativedelta import relativedelta
import fnmatch
import logging
import os
import time
from operator import itemgetter

import simplejson
import werkzeug
import HTMLParser
from lxml import etree

import openerp
from openerp import tools, api
from openerp.http import request
from openerp.modules.module import get_resource_path, get_resource_from_path
from openerp.osv import fields, osv, orm
from openerp.tools import config, graph, SKIPPED_ELEMENT_TYPES, SKIPPED_ELEMENTS
from openerp.tools.convert import _fix_multiple_roots
from openerp.tools.parse_version import parse_version
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.view_validation import valid_view
from openerp.tools import misc
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

MOVABLE_BRANDING = ['data-oe-model', 'data-oe-id', 'data-oe-field', 'data-oe-xpath', 'data-oe-source-id']

def keep_query(*keep_params, **additional_params):
    """
    Generate a query string keeping the current request querystring's parameters specified
    in ``keep_params`` and also adds the parameters specified in ``additional_params``.

    Multiple values query string params will be merged into a single one with comma seperated
    values.

    The ``keep_params`` arguments can use wildcards too, eg:

        keep_query('search', 'shop_*', page=4)
    """
    if not keep_params and not additional_params:
        keep_params = ('*',)
    params = additional_params.copy()
    qs_keys = request.httprequest.args.keys()
    for keep_param in keep_params:
        for param in fnmatch.filter(qs_keys, keep_param):
            if param not in additional_params and param in qs_keys:
                params[param] = ','.join(request.httprequest.args.getlist(param))
    return werkzeug.urls.url_encode(params)

class view_custom(osv.osv):
    _name = 'ir.ui.view.custom'
    _order = 'create_date desc'  # search(limit=1) should return the last customization
    _columns = {
        'ref_id': fields.many2one('ir.ui.view', 'Original View', select=True, required=True, ondelete='cascade'),
        'user_id': fields.many2one('res.users', 'User', select=True, required=True, ondelete='cascade'),
        'arch': fields.text('View Architecture', required=True),
    }

    def name_get(self, cr, uid, ids, context=None):
        return [(rec.id, rec.user_id.name) for rec in self.browse(cr, uid, ids, context=context)]

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if args is None:
            args = []
        if name:
            ids = self.search(cr, user, [('user_id', operator, name)] + args, limit=limit)
            return self.name_get(cr, user, ids, context=context)
        return super(view_custom, self).name_search(cr, user, name, args=args, operator=operator, context=context, limit=limit)


    def _auto_init(self, cr, context=None):
        super(view_custom, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'ir_ui_view_custom_user_id_ref_id\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_ui_view_custom_user_id_ref_id ON ir_ui_view_custom (user_id, ref_id)')

def _hasclass(context, *cls):
    """ Checks if the context node has all the classes passed as arguments
    """
    node_classes = set(context.context_node.attrib.get('class', '').split())

    return node_classes.issuperset(cls)

def get_view_arch_from_file(filename, xmlid):
    doc = etree.parse(filename)
    node = None
    for n in doc.xpath('//*[@id="%s"] | //*[@id="%s"]' % (xmlid, xmlid.split('.')[1])):
        if n.tag in ('template', 'record'):
            node = n
            break
    if node is not None:
        if node.tag == 'record':
            field = node.find('field[@name="arch"]')
            _fix_multiple_roots(field)
            inner = ''.join([etree.tostring(child) for child in field.iterchildren()])
            return field.text + inner
        elif node.tag == 'template':
            # The following dom operations has been copied from convert.py's _tag_template()
            if not node.get('inherit_id'):
                node.set('t-name', xmlid)
                node.tag = 't'
            else:
                node.tag = 'data'
            node.attrib.pop('id', None)
            return etree.tostring(node)
    _logger.warning("Could not find view arch definition in file '%s' for xmlid '%s'" % (filename, xmlid))
    return None

xpath_utils = etree.FunctionNamespace(None)
xpath_utils['hasclass'] = _hasclass

class view(osv.osv):
    _name = 'ir.ui.view'

    def _get_model_data(self, cr, uid, ids, fname, args, context=None):
        result = dict.fromkeys(ids, False)
        IMD = self.pool['ir.model.data']
        data_ids = IMD.search_read(cr, uid, [('res_id', 'in', ids), ('model', '=', 'ir.ui.view')], ['res_id'], context=context)
        result.update(map(itemgetter('res_id', 'id'), data_ids))
        return result

    def _views_from_model_data(self, cr, uid, ids, context=None):
        IMD = self.pool['ir.model.data']
        data_ids = IMD.search_read(cr, uid, [('id', 'in', ids), ('model', '=', 'ir.ui.view')], ['res_id'], context=context)
        return map(itemgetter('res_id'), data_ids)

    def _arch_get(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for view in self.browse(cr, uid, ids, context=context):
            arch_fs = None
            if config['dev_mode'] and view.arch_fs and view.xml_id:
                # It is safe to split on / herebelow because arch_fs is explicitely stored with '/'
                fullpath = get_resource_path(*view.arch_fs.split('/'))
                arch_fs = get_view_arch_from_file(fullpath, view.xml_id)
            result[view.id] = arch_fs or view.arch_db
        return result

    def _arch_set(self, cr, uid, ids, field_name, field_value, args, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        if field_value:
            for view in self.browse(cr, uid, ids, context=context):
                data = dict(arch_db=field_value)
                key = 'install_mode_data'
                if context and key in context:
                    imd = context[key]
                    if self._model._name == imd['model'] and (not view.xml_id or view.xml_id == imd['xml_id']):
                        # we store the relative path to the resource instead of the absolute path
                        data['arch_fs'] = '/'.join(get_resource_from_path(imd['xml_file'])[0:2])
                self.write(cr, uid, ids, data, context=context)

        return True

    _columns = {
        'name': fields.char('View Name', required=True),
        'model': fields.char('Object', select=True),
        'key': fields.char(string='Key'),
        'priority': fields.integer('Sequence', required=True),
        'type': fields.selection([
            ('tree','Tree'),
            ('form','Form'),
            ('graph', 'Graph'),
            ('pivot', 'Pivot'),
            ('calendar', 'Calendar'),
            ('diagram','Diagram'),
            ('gantt', 'Gantt'),
            ('kanban', 'Kanban'),
            ('search','Search'),
            ('qweb', 'QWeb')], string='View Type'),
        'arch': fields.function(_arch_get, fnct_inv=_arch_set, string='View Architecture', type="text", nodrop=True),
        'arch_db': fields.text('Arch Blob'),
        'arch_fs': fields.char('Arch Filename'),
        'inherit_id': fields.many2one('ir.ui.view', 'Inherited View', ondelete='restrict', select=True),
        'inherit_children_ids': fields.one2many('ir.ui.view','inherit_id', 'Inherit Views'),
        'field_parent': fields.char('Child Field'),
        'model_data_id': fields.function(_get_model_data, type='many2one', relation='ir.model.data', string="Model Data",
                                         store={
                                             _name: (lambda s, c, u, i, ctx=None: i, None, 10),
                                             'ir.model.data': (_views_from_model_data, ['model', 'res_id'], 10),
                                         }),
        'xml_id': fields.function(osv.osv.get_xml_id, type='char', size=128, string="External ID",
                                  help="ID of the view defined in xml file"),
        'groups_id': fields.many2many('res.groups', 'ir_ui_view_group_rel', 'view_id', 'group_id',
            string='Groups', help="If this field is empty, the view applies to all users. Otherwise, the view applies to the users of those groups only."),
        'model_ids': fields.one2many('ir.model.data', 'res_id', domain=[('model','=','ir.ui.view')], auto_join=True),
        'create_date': fields.datetime('Create Date', readonly=True),
        'write_date': fields.datetime('Last Modification Date', readonly=True),

        'mode': fields.selection(
            [('primary', "Base view"), ('extension', "Extension View")],
            string="View inheritance mode", required=True,
            help="""Only applies if this view inherits from an other one (inherit_id is not False/Null).

* if extension (default), if this view is requested the closest primary view
  is looked up (via inherit_id), then all views inheriting from it with this
  view's model are applied
* if primary, the closest primary view is fully resolved (even if it uses a
  different model than this one), then this view's inheritance specs
  (<xpath/>) are applied, and the result is used as if it were this view's
  actual arch.
"""),
        'active': fields.boolean("Active",
            help="""If this view is inherited,
* if True, the view always extends its parent
* if False, the view currently does not extend its parent but can be enabled
             """),
    }
    _defaults = {
        'mode': 'primary',
        'active': True,
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
        context = dict(context, check_view_ids=ids)

        # Sanity checks: the view should not break anything upon rendering!
        # Any exception raised below will cause a transaction rollback.
        for view in self.browse(cr, uid, ids, context):
            view_def = self.read_combined(cr, uid, view.id, None, context=context)
            view_arch_utf8 = view_def['arch']
            if view.type != 'qweb':
                view_doc = etree.fromstring(view_arch_utf8)
                # verify that all fields used are valid, etc.
                self.postprocess_and_fields(cr, uid, view.model, view_doc, view.id, context=context)
                # RNG-based validation is not possible anymore with 7.0 forms
                view_docs = [view_doc]
                if view_docs[0].tag == 'data':
                    # A <data> element is a wrapper for multiple root nodes
                    view_docs = view_docs[0]
                validator = self._relaxng()
                for view_arch in view_docs:
                    version = view_arch.get('version', '7.0')
                    if parse_version(version) < parse_version('7.0') and validator and not validator.validate(view_arch):
                        for error in validator.error_log:
                            _logger.error(tools.ustr(error))
                        return False
                    if not valid_view(view_arch):
                        return False
        return True

    _sql_constraints = [
        ('inheritance_mode',
         "CHECK (mode != 'extension' OR inherit_id IS NOT NULL)",
         "Invalid inheritance mode: if the mode is 'extension', the view must"
         " extend an other view"),
    ]
    _constraints = [
        (_check_xml, 'Invalid view definition', ['arch']),
    ]

    def _auto_init(self, cr, context=None):
        super(view, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'ir_ui_view_model_type_inherit_id\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_ui_view_model_type_inherit_id ON ir_ui_view (model, inherit_id)')

    def _compute_defaults(self, cr, uid, values, context=None):
        if 'inherit_id' in values:
            values.setdefault(
                'mode', 'extension' if values['inherit_id'] else 'primary')
        return values

    def create(self, cr, uid, values, context=None):
        if not values.get('type'):
            if values.get('inherit_id'):
                values['type'] = self.browse(cr, uid, values['inherit_id'], context).type
            else:
                values['type'] = etree.fromstring(values['arch']).tag

        if not values.get('name'):
            values['name'] = "%s %s" % (values.get('model'), values['type'])

        self.clear_cache()
        return super(view, self).create(
            cr, uid,
            self._compute_defaults(cr, uid, values, context=context),
            context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
        if context is None:
            context = {}

        # If view is modified we remove the arch_fs information thus activating the arch_db
        # version. An `init` of the view will restore the arch_fs for the --dev mode
        if 'arch' in vals and 'install_mode_data' not in context:
            vals['arch_fs'] = False

        # drop the corresponding view customizations (used for dashboards for example), otherwise
        # not all users would see the updated views
        custom_view_ids = self.pool.get('ir.ui.view.custom').search(cr, uid, [('ref_id', 'in', ids)])
        if custom_view_ids:
            self.pool.get('ir.ui.view.custom').unlink(cr, uid, custom_view_ids)

        self.clear_cache()
        ret = super(view, self).write(
            cr, uid, ids,
            self._compute_defaults(cr, uid, vals, context=context),
            context)
        return ret

    def toggle(self, cr, uid, ids, context=None):
        """ Switches between enabled and disabled statuses
        """
        for view in self.browse(cr, uid, ids, context=dict(context or {}, active_test=False)):
            view.write({'active': not view.active})

    # default view selection
    def default_view(self, cr, uid, model, view_type, context=None):
        """ Fetches the default view for the provided (model, view_type) pair:
         primary view with the lowest priority.

        :param str model:
        :param int view_type:
        :return: id of the default view of False if none found
        :rtype: int
        """
        domain = [
            ['model', '=', model],
            ['type', '=', view_type],
            ['mode', '=', 'primary'],
        ]
        ids = self.search(cr, uid, domain, limit=1, context=context)
        if not ids:
            return False
        return ids[0]

    #------------------------------------------------------
    # Inheritance mecanism
    #------------------------------------------------------
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

        user = self.pool['res.users'].browse(cr, 1, uid, context=context)
        user_groups = frozenset(user.groups_id or ())

        conditions = [
            ['inherit_id', '=', view_id],
            ['model', '=', model],
            ['mode', '=', 'extension'],
            ['active', '=', True],
        ]
        if self.pool._init:
            # Module init currently in progress, only consider views from
            # modules whose code is already loaded
            conditions.extend([
                '|',
                ['model_ids.module', 'in', tuple(self.pool._init_modules)],
                ['id', 'in', context and context.get('check_view_ids') or (0,)],
            ])
        view_ids = self.search(cr, uid, conditions, context=context)

        return [(view.arch, view.id)
                for view in self.browse(cr, 1, view_ids, context)
                if not (view.groups_id and user_groups.isdisjoint(view.groups_id))]

    def raise_view_error(self, cr, uid, message, view_id, context=None):
        view = self.browse(cr, uid, view_id, context)
        not_avail = _('n/a')
        message = ("%(msg)s\n\n" +
                   _("Error context:\nView `%(view_name)s`") + 
                   "\n[view_id: %(viewid)s, xml_id: %(xmlid)s, "
                   "model: %(model)s, parent_id: %(parent)s]") % \
                        {
                          'view_name': view.name or not_avail, 
                          'viewid': view_id or not_avail,
                          'xmlid': view.xml_id or not_avail,
                          'model': view.model or not_avail,
                          'parent': view.inherit_id.id or not_avail,
                          'msg': message,
                        }
        _logger.error(message)
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

    def inherit_branding(self, specs_tree, view_id, root_id):
        for node in specs_tree.iterchildren(tag=etree.Element):
            xpath = node.getroottree().getpath(node)
            if node.tag == 'data' or node.tag == 'xpath':
                self.inherit_branding(node, view_id, root_id)
            else:
                node.set('data-oe-id', str(view_id))
                node.set('data-oe-source-id', str(root_id))
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
                specs += [c for c in spec]
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
                        attribute = (child.get('name'), child.text or None)
                        if attribute[1]:
                            node.set(attribute[0], attribute[1])
                        elif attribute[0] in node.attrib:
                            del node.attrib[attribute[0]]
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
                            self.raise_view_error(cr, uid, _("Invalid position attribute: '%s'") % pos, inherit_id, context=context)
            else:
                attrs = ''.join([
                    ' %s="%s"' % (attr, spec.get(attr))
                    for attr in spec.attrib
                    if attr != 'position'
                ])
                tag = "<%s%s>" % (spec.tag, attrs)
                self.raise_view_error(cr, uid, _("Element '%s' cannot be located in parent view") % tag, inherit_id, context=context)

        return source

    def apply_view_inheritance(self, cr, uid, source, source_id, model, root_id=None, context=None):
        """ Apply all the (directly and indirectly) inheriting views.

        :param source: a parent architecture to modify (with parent modifications already applied)
        :param source_id: the database view_id of the parent view
        :param model: the original model for which we create a view (not
            necessarily the same as the source's model); only the inheriting
            views with that specific model will be applied.
        :return: a modified source where all the modifying architecture are applied
        """
        if context is None: context = {}
        if root_id is None:
            root_id = source_id
        sql_inherit = self.get_inheriting_views_arch(cr, uid, source_id, model, context=context)
        for (specs, view_id) in sql_inherit:
            specs_tree = etree.fromstring(specs.encode('utf-8'))
            if context.get('inherit_branding'):
                self.inherit_branding(specs_tree, view_id, root_id)
            source = self.apply_inheritance_specs(cr, uid, source, specs_tree, view_id, context=context)
            source = self.apply_view_inheritance(cr, uid, source, view_id, model, root_id=root_id, context=context)
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
        base = v = self.browse(cr, uid, view_id, context=context)
        while v.mode != 'primary':
            v = v.inherit_id
        root_id = v.id

        # arch and model fields are always returned
        if fields:
            fields = list(set(fields) | set(['arch', 'model']))

        # read the view arch
        [view] = self.read(cr, uid, [root_id], fields=fields, context=context)
        view_arch = etree.fromstring(view['arch'].encode('utf-8'))
        if not v.inherit_id:
            arch_tree = view_arch
        else:
            parent_view = self.read_combined(
                cr, uid, v.inherit_id.id, fields=fields, context=context)
            arch_tree = etree.fromstring(parent_view['arch'])
            self.apply_inheritance_specs(
                cr, uid, arch_tree, view_arch, parent_view['id'], context=context)


        if context.get('inherit_branding'):
            arch_tree.attrib.update({
                'data-oe-model': 'ir.ui.view',
                'data-oe-id': str(root_id),
                'data-oe-field': 'arch',
            })

        # and apply inheritance
        arch = self.apply_view_inheritance(
            cr, uid, arch_tree, root_id, base.model, context=context)

        return dict(view, arch=etree.tostring(arch, encoding='utf-8'))

    #------------------------------------------------------
    # Postprocessing: translation, groups and modifiers
    #------------------------------------------------------
    # TODO: 
    # - split postprocess so that it can be used instead of translate_qweb
    # - remove group processing from ir_qweb
    #------------------------------------------------------
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
        if Model is None:
            self.raise_view_error(cr, user, _('Model not found: %(model)s') % dict(model=model),
                                  view_id, context)

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
            if node.tag == 'field' and node.get('name') in Model._fields:
                field = Model._fields[node.get('name')]
                if field.groups and not self.user_has_groups(
                        cr, user, groups=field.groups, context=context):
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
                field = Model._fields.get(node.get('name'))
                if field:
                    children = False
                    views = {}
                    for f in node:
                        if f.tag in ('form', 'tree', 'graph', 'kanban', 'calendar'):
                            node.remove(f)
                            ctx = context.copy()
                            ctx['base_model_name'] = model
                            xarch, xfields = self.postprocess_and_fields(cr, user, field.comodel_name, f, view_id, ctx)
                            views[str(f.tag)] = {
                                'arch': xarch,
                                'fields': xfields
                            }
                    attrs = {'views': views}
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
            for additional_field in ('date_start', 'date_delay', 'date_stop', 'color', 'all_day', 'attendee'):
                if node.get(additional_field):
                    fields[node.get(additional_field)] = {}

        if not check_group(node):
            # node must be removed, no need to proceed further with its children
            return fields

        # The view architeture overrides the python model.
        # Get the attrs before they are (possibly) deleted by check_group below
        orm.transfer_node_to_modifiers(node, modifiers, context, in_tree_view)

        # TODO remove attrs counterpart in modifiers when invisible is true ?

        # translate view
        if 'lang' in context:
            Translations = self.pool['ir.translation']
            if node.text and node.text.strip():
                term = node.text.strip()
                trans = Translations._get_source(cr, user, model, 'view', context['lang'], term)
                if trans:
                    node.text = node.text.replace(term, trans)
            if node.tail and node.tail.strip():
                term = node.tail.strip()
                trans = Translations._get_source(cr, user, model, 'view', context['lang'], term)
                if trans:
                    node.tail =  node.tail.replace(term, trans)

            if node.get('string') and node.get('string').strip() and not result:
                term = node.get('string').strip()
                trans = Translations._get_source(cr, user, model, 'view', context['lang'], term)
                if trans == term and ('base_model_name' in context):
                    # If translation is same as source, perhaps we'd have more luck with the alternative model name
                    # (in case we are in a mixed situation, such as an inherited view where parent_view.model != model
                    trans = Translations._get_source(cr, user, context['base_model_name'], 'view', context['lang'], term)
                if trans:
                    node.set('string', trans)

            for attr_name in ('confirm', 'sum', 'avg', 'help', 'placeholder'):
                attr_value = node.get(attr_name)
                if attr_value and attr_value.strip():
                    trans = Translations._get_source(cr, user, model, 'view', context['lang'], attr_value.strip())
                    if trans:
                        node.set(attr_name, trans)

        for f in node:
            if children or (node.tag == 'field' and f.tag in ('filter','separator')):
                fields.update(self.postprocess(cr, user, model, f, view_id, in_tree_view, model_fields, context))

        orm.transfer_modifiers_to_node(modifiers, node)
        return fields

    def add_on_change(self, cr, user, model_name, arch):
        """ Add attribute on_change="1" on fields that are dependencies of
            computed fields on the same view.
        """
        # map each field object to its corresponding nodes in arch
        field_nodes = collections.defaultdict(list)

        def collect(node, model):
            if node.tag == 'field':
                field = model._fields.get(node.get('name'))
                if field:
                    field_nodes[field].append(node)
                    if field.relational:
                        model = self.pool.get(field.comodel_name)
            for child in node:
                collect(child, model)

        collect(arch, self.pool[model_name])

        for field, nodes in field_nodes.iteritems():
            # if field should trigger an onchange, add on_change="1" on the
            # nodes referring to field
            model = self.pool[field.model_name]
            if model._has_onchange(field, field_nodes):
                for node in nodes:
                    if not node.get('on_change'):
                        node.set('on_change', '1')

        return arch

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
        if Model is None:
            self.raise_view_error(cr, user, _('Model not found: %(model)s') % dict(model=model), view_id, context)

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
        else:
            fields = Model.fields_get(cr, user, None, context)

        node = self.add_on_change(cr, user, model, node)
        fields_def = self.postprocess(cr, user, model, node, view_id, False, fields, context=context)
        node = self._disable_workflow_buttons(cr, user, model, node)
        if node.tag in ('kanban', 'tree', 'form', 'gantt'):
            for action, operation in (('create', 'create'), ('delete', 'unlink'), ('edit', 'write')):
                if not node.get(action) and not Model.check_access_rights(cr, user, operation, raise_exception=False):
                    node.set(action, 'false')
        if node.tag in ('kanban'):
            group_by_name = node.get('default_group_by')
            if group_by_name in Model._fields:
                group_by_field = Model._fields[group_by_name]
                if group_by_field.type == 'many2one':
                    group_by_model = Model.pool[group_by_field.comodel_name]
                    for action, operation in (('group_create', 'create'), ('group_delete', 'unlink'), ('group_edit', 'write')):
                        if not node.get(action) and not group_by_model.check_access_rights(cr, user, operation, raise_exception=False):
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
                message = _("Field `%(field_name)s` does not exist") % \
                                dict(field_name=field)
                self.raise_view_error(cr, user, message, view_id, context)
        return arch, fields

    #------------------------------------------------------
    # QWeb template views
    #------------------------------------------------------
    _read_template_cache = dict(accepted_keys=('lang','inherit_branding', 'editable', 'translatable'))
    if config['dev_mode']:
        _read_template_cache['size'] = 0
    @tools.ormcache_context(**_read_template_cache)
    def _read_template(self, cr, uid, view_id, context=None):
        arch = self.read_combined(cr, uid, view_id, fields=['arch'], context=context)['arch']
        arch_tree = etree.fromstring(arch)

        if 'lang' in context:
            arch_tree = self.translate_qweb(cr, uid, view_id, arch_tree, context['lang'], context)

        self.distribute_branding(arch_tree)
        root = etree.Element('templates')
        root.append(arch_tree)
        arch = etree.tostring(root, encoding='utf-8', xml_declaration=True)
        return arch

    def read_template(self, cr, uid, xml_id, context=None):
        if isinstance(xml_id, (int, long)):
            view_id = xml_id
        else:
            if '.' not in xml_id:
                raise ValueError('Invalid template id: %r' % (xml_id,))
            view_id = self.get_view_id(cr, uid, xml_id, context=context)
        return self._read_template(cr, uid, view_id, context=context)

    @tools.ormcache(skiparg=3)
    def get_view_id(self, cr, uid, xml_id, context=None):
        return self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, xml_id, raise_if_not_found=True)

    def clear_cache(self):
        self._read_template.clear_cache(self)

    def _contains_branded(self, node):
        return node.tag == 't'\
            or 't-raw' in node.attrib\
            or any(self.is_node_branded(child) for child in node.iterdescendants())

    def _pop_view_branding(self, element):
        distributed_branding = dict(
            (attribute, element.attrib.pop(attribute))
            for attribute in MOVABLE_BRANDING
            if element.get(attribute))
        return distributed_branding

    def distribute_branding(self, e, branding=None, parent_xpath='',
                            index_map=misc.ConstantMapping(1)):
        if e.get('t-ignore') or e.tag == 'head':
            # remove any view branding possibly injected by inheritance
            attrs = set(MOVABLE_BRANDING)
            for descendant in e.iterdescendants(tag=etree.Element):
                if not attrs.intersection(descendant.attrib): continue
                self._pop_view_branding(descendant)
            # TODO: find a better name and check if we have a string to boolean helper
            return

        node_path = e.get('data-oe-xpath')
        if node_path is None:
            node_path = "%s/%s[%d]" % (parent_xpath, e.tag, index_map[e.tag])
        if branding and not (e.get('data-oe-model') or e.get('t-field')):
            e.attrib.update(branding)
            e.set('data-oe-xpath', node_path)
        if not e.get('data-oe-model'): return

        if {'t-esc', 't-raw'}.intersection(e.attrib):
            # nodes which fully generate their content and have no reason to
            # be branded because they can not sensibly be edited
            self._pop_view_branding(e)
        elif self._contains_branded(e):
            # if a branded element contains branded elements distribute own
            # branding to children unless it's t-raw, then just remove branding
            # on current element
            distributed_branding = self._pop_view_branding(e)

            if 't-raw' not in e.attrib:
                # TODO: collections.Counter if remove p2.6 compat
                # running index by tag type, for XPath query generation
                indexes = collections.defaultdict(lambda: 0)
                for child in e.iterchildren(tag=etree.Element):
                    if child.get('data-oe-xpath'):
                        # injected by view inheritance, skip otherwise
                        # generated xpath is incorrect
                        self.distribute_branding(child)
                    else:
                        indexes[child.tag] += 1
                        self.distribute_branding(
                            child, distributed_branding,
                            parent_xpath=node_path, index_map=indexes)

    def is_node_branded(self, node):
        """ Finds out whether a node is branded or qweb-active (bears a
        @data-oe-model or a @t-* *which is not t-field* as t-field does not
        section out views)

        :param node: an etree-compatible element to test
        :type node: etree._Element
        :rtype: boolean
        """
        return any(
            (attr in ('data-oe-model', 'group') or (attr != 't-field' and attr.startswith('t-')))
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
            return Translations._get_source(cr, uid, 'website', 'view', lang, text, id_)

        if type(arch) not in SKIPPED_ELEMENT_TYPES and arch.tag not in SKIPPED_ELEMENTS:
            text = get_trans(arch.text)
            if text:
                arch.text = arch.text.replace(arch.text.strip(), text)
            tail = get_trans(arch.tail)
            if tail:
                arch.tail = arch.tail.replace(arch.tail.strip(), tail)

            for attr_name in ('title', 'alt', 'label', 'placeholder'):
                attr = get_trans(arch.get(attr_name))
                if attr:
                    arch.set(attr_name, attr)
            for node in arch.iterchildren("*"):
                self.translate_qweb(cr, uid, id_, node, lang, context)
        return arch

    @openerp.tools.ormcache()
    def get_view_xmlid(self, cr, uid, id):
        imd = self.pool['ir.model.data']
        domain = [('model', '=', 'ir.ui.view'), ('res_id', '=', id)]
        xmlid = imd.search_read(cr, uid, domain, ['module', 'name'])[0]
        return '%s.%s' % (xmlid['module'], xmlid['name'])

    @api.cr_uid_ids_context
    def render(self, cr, uid, id_or_xml_id, values=None, engine='ir.qweb', context=None):
        if isinstance(id_or_xml_id, list):
            id_or_xml_id = id_or_xml_id[0]

        if not context:
            context = {}

        if values is None:
            values = dict()
        qcontext = dict(
            keep_query=keep_query,
            request=request, # might be unbound if we're not in an httprequest context
            debug=request.debug if request else False,
            json=simplejson,
            quote_plus=werkzeug.url_quote_plus,
            time=time,
            datetime=datetime,
            relativedelta=relativedelta,
        )
        qcontext.update(values)

        # TODO: This helper can be used by any template that wants to embedd the backend.
        #       It is currently necessary because the ir.ui.view bundle inheritance does not
        #       match the module dependency graph.
        def get_modules_order():
            if request:
                from openerp.addons.web.controllers.main import module_boot
                return simplejson.dumps(module_boot())
            return '[]'
        qcontext['get_modules_order'] = get_modules_order

        def loader(name):
            return self.read_template(cr, uid, name, context=context)

        return self.pool[engine].render(cr, uid, id_or_xml_id, qcontext, loader=loader, context=context)

    #------------------------------------------------------
    # Misc
    #------------------------------------------------------

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

    def _validate_module_views(self, cr, uid, module):
        """Validate architecture of all the views of a given module"""
        assert not self.pool._init or module in self.pool._init_modules
        xmlid_filter = ''
        params = (module,)
        if self.pool._init:
            # only validate the views that are still existing...
            xmlid_filter = "AND md.name IN %s"
            names = tuple(name for (xmod, name), (model, res_id) in self.pool.model_data_reference_ids.items() if xmod == module and model == self._name)
            if not names:
                # no views for this module, nothing to validate
                return
            params += (names,)
        cr.execute("""SELECT max(v.id)
                        FROM ir_ui_view v
                   LEFT JOIN ir_model_data md ON (md.model = 'ir.ui.view' AND md.res_id = v.id)
                       WHERE md.module = %s
                         {0}
                    GROUP BY coalesce(v.inherit_id, v.id)
                   """.format(xmlid_filter), params)

        for vid, in cr.fetchall():
            if not self._check_xml(cr, uid, [vid]):
                self.raise_view_error(cr, uid, "Can't validate view", vid)

# vim:et:
