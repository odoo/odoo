# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import collections
import datetime
import fnmatch
import json
import logging
import re
import time
import uuid

import itertools
from dateutil.relativedelta import relativedelta
from difflib import HtmlDiff
from operator import itemgetter

import werkzeug
from lxml import etree
from lxml.etree import LxmlError
from lxml.builder import E

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.modules.module import get_resource_from_path, get_resource_path
from odoo.tools import config, graph, ConstantMapping, pycompat, apply_inheritance_specs, locate_node
from odoo.tools.convert import _fix_multiple_roots
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.safe_eval import safe_eval
from odoo.tools.view_validation import valid_view, get_attrs_field_names, field_is_editable
from odoo.tools.translate import xml_translate, TRANSLATED_ATTRS
from odoo.tools.image import image_data_uri

_logger = logging.getLogger(__name__)

MOVABLE_BRANDING = ['data-oe-model', 'data-oe-id', 'data-oe-field', 'data-oe-xpath', 'data-oe-source-id']

# First sort criterion for inheritance is priority, second is chronological order of installation
# Note: natural _order has `name`, but only because that makes list browsing easier
INHERIT_ORDER = 'priority,id'


def transfer_field_to_modifiers(field, modifiers):
    default_values = {}
    state_exceptions = {}
    for attr in ('invisible', 'readonly', 'required'):
        state_exceptions[attr] = []
        default_values[attr] = bool(field.get(attr))
    for state, modifs in field.get("states",{}).items():
        for modif in modifs:
            if default_values[modif[0]] != modif[1]:
                state_exceptions[modif[0]].append(state)

    for attr, default_value in default_values.items():
        if state_exceptions[attr]:
            modifiers[attr] = [("state", "not in" if default_value else "in", state_exceptions[attr])]
        else:
            modifiers[attr] = default_value


def transfer_node_to_modifiers(node, modifiers, context=None, in_tree_view=False):
    # Don't deal with groups, it is done by check_group().
    # Need the context to evaluate the invisible attribute on tree views.
    # For non-tree views, the context shouldn't be given.
    if node.get('attrs'):
        modifiers.update(safe_eval(node.get('attrs')))

    if node.get('states'):
        if 'invisible' in modifiers and isinstance(modifiers['invisible'], list):
            # TODO combine with AND or OR, use implicit AND for now.
            modifiers['invisible'].append(('state', 'not in', node.get('states').split(',')))
        else:
            modifiers['invisible'] = [('state', 'not in', node.get('states').split(','))]

    for a in ('invisible', 'readonly', 'required'):
        if node.get(a):
            v = bool(safe_eval(node.get(a), {'context': context or {}}))
            if in_tree_view and a == 'invisible':
                # Invisible in a tree view has a specific meaning, make it a
                # new key in the modifiers attribute.
                modifiers['column_invisible'] = v
            elif v or (a not in modifiers or not isinstance(modifiers[a], list)):
                # Don't set the attribute to False if a dynamic value was
                # provided (i.e. a domain from attrs or states).
                modifiers[a] = v


def simplify_modifiers(modifiers):
    for a in ('invisible', 'readonly', 'required'):
        if a in modifiers and not modifiers[a]:
            del modifiers[a]


def transfer_modifiers_to_node(modifiers, node):
    if modifiers:
        simplify_modifiers(modifiers)
        node.set('modifiers', json.dumps(modifiers))


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
    qs_keys = list(request.httprequest.args) if request else []
    for keep_param in keep_params:
        for param in fnmatch.filter(qs_keys, keep_param):
            if param not in additional_params and param in qs_keys:
                params[param] = request.httprequest.args.getlist(param)
    return werkzeug.urls.url_encode(params)


class ViewCustom(models.Model):
    _name = 'ir.ui.view.custom'
    _description = 'Custom View'
    _order = 'create_date desc'  # search(limit=1) should return the last customization

    ref_id = fields.Many2one('ir.ui.view', string='Original View', index=True, required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', index=True, required=True, ondelete='cascade')
    arch = fields.Text(string='View Architecture', required=True)

    def name_get(self):
        return [(rec.id, rec.user_id.name) for rec in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if name:
            view_ids = self._search([('user_id', operator, name)] + (args or []), limit=limit, access_rights_uid=name_get_uid)
            return models.lazy_name_get(self.browse(view_ids).with_user(name_get_uid))
        return super(ViewCustom, self)._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    def _auto_init(self):
        res = super(ViewCustom, self)._auto_init()
        tools.create_index(self._cr, 'ir_ui_view_custom_user_id_ref_id',
                           self._table, ['user_id', 'ref_id'])
        return res


def _hasclass(context, *cls):
    """ Checks if the context node has all the classes passed as arguments
    """
    node_classes = set(context.context_node.attrib.get('class', '').split())
    return node_classes.issuperset(cls)


def get_view_arch_from_file(filename, xmlid):
    doc = etree.parse(filename)

    xmlid_search = (xmlid, xmlid.split('.')[1])

    # when view is created from model with inheritS of ir_ui_view, the xml id has been suffixed by '_ir_ui_view'
    suffix = '_ir_ui_view'
    if xmlid.endswith(suffix):
        xmlid_search += (xmlid.rsplit(suffix, 1)[0], xmlid.split('.')[1].rsplit(suffix, 1)[0])

    for node in doc.xpath('//*[%s]' % ' or '.join(["@id='%s'" % _id for _id in xmlid_search])):
        if node.tag in ('template', 'record'):
            if node.tag == 'record':
                field = node.find('field[@name="arch"]')
                if field is None:
                    if node.find('field[@name="view_id"]') is not None:
                        view_id = node.find('field[@name="view_id"]').attrib.get('ref')
                        ref_id = '%s%s' % ('.' not in view_id and xmlid.split('.')[0] + '.' or '', view_id)
                        return get_view_arch_from_file(filename, ref_id)
                    else:
                        return None
                _fix_multiple_roots(field)
                inner = u''.join([etree.tostring(child, encoding='unicode') for child in field.iterchildren()])
                return field.text + inner
            elif node.tag == 'template':
                # The following dom operations has been copied from convert.py's _tag_template()
                if not node.get('inherit_id'):
                    node.set('t-name', xmlid)
                    node.tag = 't'
                else:
                    node.tag = 'data'
                node.attrib.pop('id', None)
                return etree.tostring(node, encoding='unicode')
    _logger.warning("Could not find view arch definition in file '%s' for xmlid '%s'", filename, xmlid_search)
    return None



xpath_utils = etree.FunctionNamespace(None)
xpath_utils['hasclass'] = _hasclass

TRANSLATED_ATTRS_RE = re.compile(r"@(%s)\b" % "|".join(TRANSLATED_ATTRS))
WRONGCLASS = re.compile(r"(@class\s*=|=\s*@class|contains\(@class)")


class View(models.Model):
    _name = 'ir.ui.view'
    _description = 'View'
    _order = "priority,name,id"

    name = fields.Char(string='View Name', required=True)
    model = fields.Char(index=True)
    key = fields.Char()
    priority = fields.Integer(string='Sequence', default=16, required=True)
    type = fields.Selection([('tree', 'Tree'),
                             ('form', 'Form'),
                             ('graph', 'Graph'),
                             ('pivot', 'Pivot'),
                             ('calendar', 'Calendar'),
                             ('diagram', 'Diagram'),
                             ('gantt', 'Gantt'),
                             ('kanban', 'Kanban'),
                             ('search', 'Search'),
                             ('qweb', 'QWeb')], string='View Type')
    arch = fields.Text(compute='_compute_arch', inverse='_inverse_arch', string='View Architecture',
                       help="""This field should be used when accessing view arch. It will use translation.
                               Note that it will read `arch_db` or `arch_fs` if in dev-xml mode.""")
    arch_base = fields.Text(compute='_compute_arch_base', inverse='_inverse_arch_base', string='Base View Architecture',
                            help="This field is the same as `arch` field without translations")
    arch_db = fields.Text(string='Arch Blob', translate=xml_translate,
                          help="This field stores the view arch.")
    arch_fs = fields.Char(string='Arch Filename', help="""File from where the view originates.
                                                          Useful to (hard) reset broken views or to read arch from file in dev-xml mode.""")
    arch_updated = fields.Boolean(string='Modified Architecture')
    arch_prev = fields.Text(string='Previous View Architecture', help="""This field will save the current `arch_db` before writing on it.
                                                                         Useful to (soft) reset a broken view.""")
    inherit_id = fields.Many2one('ir.ui.view', string='Inherited View', ondelete='restrict', index=True)
    inherit_children_ids = fields.One2many('ir.ui.view', 'inherit_id', string='Views which inherit from this one')
    field_parent = fields.Char(string='Child Field')
    model_data_id = fields.Many2one('ir.model.data', string="Model Data",
                                    compute='_compute_model_data_id', search='_search_model_data_id')
    xml_id = fields.Char(string="External ID", compute='_compute_xml_id',
                         help="ID of the view defined in xml file")
    groups_id = fields.Many2many('res.groups', 'ir_ui_view_group_rel', 'view_id', 'group_id',
                                 string='Groups', help="If this field is empty, the view applies to all users. Otherwise, the view applies to the users of those groups only.")
    model_ids = fields.One2many('ir.model.data', 'res_id', string="Models", domain=[('model', '=', 'ir.ui.view')], auto_join=True)

    mode = fields.Selection([('primary', "Base view"), ('extension', "Extension View")],
                            string="View inheritance mode", default='primary', required=True,
                            help="""Only applies if this view inherits from an other one (inherit_id is not False/Null).

* if extension (default), if this view is requested the closest primary view
is looked up (via inherit_id), then all views inheriting from it with this
view's model are applied
* if primary, the closest primary view is fully resolved (even if it uses a
different model than this one), then this view's inheritance specs
(<xpath/>) are applied, and the result is used as if it were this view's
actual arch.
""")
    active = fields.Boolean(default=True,
                            help="""If this view is inherited,
* if True, the view always extends its parent
* if False, the view currently does not extend its parent but can be enabled
         """)

    @api.depends('arch_db', 'arch_fs', 'arch_updated')
    @api.depends_context('read_arch_from_file', 'lang')
    def _compute_arch(self):
        def resolve_external_ids(arch_fs, view_xml_id):
            def replacer(m):
                xmlid = m.group('xmlid')
                if '.' not in xmlid:
                    xmlid = '%s.%s' % (view_xml_id.split('.')[0], xmlid)
                return m.group('prefix') + str(self.env['ir.model.data'].xmlid_to_res_id(xmlid))
            return re.sub(r'(?P<prefix>[^%])%\((?P<xmlid>.*?)\)[ds]', replacer, arch_fs)

        for view in self:
            arch_fs = None
            xml_id = view.xml_id or view.key
            read_file = self._context.get('read_arch_from_file') or \
                ('xml' in config['dev_mode'] and not view.arch_updated)
            if read_file and view.arch_fs and xml_id:
                # It is safe to split on / herebelow because arch_fs is explicitely stored with '/'
                fullpath = get_resource_path(*view.arch_fs.split('/'))
                if fullpath:
                    arch_fs = get_view_arch_from_file(fullpath, xml_id)
                    # replace %(xml_id)s, %(xml_id)d, %%(xml_id)s, %%(xml_id)d by the res_id
                    arch_fs = arch_fs and resolve_external_ids(arch_fs, xml_id).replace('%%', '%')
                else:
                    _logger.warning("View %s: Full path [%s] cannot be found.", xml_id, view.arch_fs)
                    arch_fs = False
            view.arch = pycompat.to_text(arch_fs or view.arch_db)

    def _inverse_arch(self):
        for view in self:
            data = dict(arch_db=view.arch)
            if 'install_filename' in self._context:
                # we store the relative path to the resource instead of the absolute path, if found
                # (it will be missing e.g. when importing data-only modules using base_import_module)
                path_info = get_resource_from_path(self._context['install_filename'])
                if path_info:
                    data['arch_fs'] = '/'.join(path_info[0:2])
                    data['arch_updated'] = False
            view.write(data)
        # the field 'arch' depends on the context and has been implicitly
        # modified in all languages; the invalidation below ensures that the
        # field does not keep an old value in another environment
        self.invalidate_cache(['arch'], self._ids)

    @api.depends('arch')
    @api.depends_context('read_arch_from_file')
    def _compute_arch_base(self):
        # 'arch_base' is the same as 'arch' without translation
        for view, view_wo_lang in zip(self, self.with_context(lang=None)):
            view.arch_base = view_wo_lang.arch

    def _inverse_arch_base(self):
        for view, view_wo_lang in zip(self, self.with_context(lang=None)):
            view_wo_lang.arch = view.arch_base

    def reset_arch(self, mode='soft'):
        for view in self:
            arch = False
            if mode == 'soft':
                arch = view.arch_prev
            elif mode == 'hard' and view.arch_fs:
                arch = view.with_context(read_arch_from_file=True).arch
            if arch:
                # Don't save current arch in previous since we reset, this arch is probably broken
                view.with_context(no_save_prev=True).write({'arch_db': arch})

    @api.depends('write_date')
    def _compute_model_data_id(self):
        # get the first ir_model_data record corresponding to self
        for view in self:
            view.model_data_id = False
        domain = [('model', '=', 'ir.ui.view'), ('res_id', 'in', self.ids)]
        for data in self.env['ir.model.data'].sudo().search_read(domain, ['res_id'], order='id desc'):
            view = self.browse(data['res_id'])
            view.model_data_id = data['id']

    def _search_model_data_id(self, operator, value):
        name = 'name' if isinstance(value, str) else 'id'
        domain = [('model', '=', 'ir.ui.view'), (name, operator, value)]
        data = self.env['ir.model.data'].sudo().search(domain)
        return [('id', 'in', data.mapped('res_id'))]

    def _compute_xml_id(self):
        xml_ids = collections.defaultdict(list)
        domain = [('model', '=', 'ir.ui.view'), ('res_id', 'in', self.ids)]
        for data in self.env['ir.model.data'].sudo().search_read(domain, ['module', 'name', 'res_id']):
            xml_ids[data['res_id']].append("%s.%s" % (data['module'], data['name']))
        for view in self:
            view.xml_id = xml_ids.get(view.id, [''])[0]

    def _valid_inheritance(self, arch):
        """ Check whether view inheritance is based on translated attribute. """
        for node in arch.xpath('//*[@position]'):
            # inheritance may not use a translated attribute as selector
            if node.tag == 'xpath':
                match = TRANSLATED_ATTRS_RE.search(node.get('expr', ''))
                if match:
                    message = "View inheritance may not use attribute %r as a selector." % match.group(1)
                    self.raise_view_error(message, self.id)
                if WRONGCLASS.search(node.get('expr', '')):
                    _logger.warn(
                        "Error-prone use of @class in view %s (%s): use the "
                        "hasclass(*classes) function to filter elements by "
                        "their classes", self.name, self.xml_id
                    )
            else:
                for attr in TRANSLATED_ATTRS:
                    if node.get(attr):
                        message = "View inheritance may not use attribute %r as a selector." % attr
                        self.raise_view_error(message, self.id)
        return True

    def _check_groups_validity(self, view, view_name):
        for node in view.xpath('//*[@groups]'):
            for group in node.get('groups').replace('!', '').split(','):
                if not self.env.ref(group.strip(), raise_if_not_found=False):
                    _logger.warning("The group %s defined in view %s does not exist!", group, view_name)

    @api.constrains('arch_db')
    def _check_xml(self):
        # Sanity checks: the view should not break anything upon rendering!
        # Any exception raised below will cause a transaction rollback.
        self = self.with_context(check_field_names=True)
        for view in self:
            view_arch = etree.fromstring(view.arch.encode('utf-8'))
            view._valid_inheritance(view_arch)
            view_def = view.read_combined(['arch'])
            view_arch_utf8 = view_def['arch']
            if view.type != 'qweb':
                view_doc = etree.fromstring(view_arch_utf8)
                self._check_groups_validity(view_doc, view.name)
                # verify that all fields used are valid, etc.
                try:
                    self.postprocess_and_fields(view.model, view_doc, view.id)
                except ValueError as e:
                    raise ValidationError("%s\n\n%s" % (_("Error while validating view"), tools.ustr(e)))
                # RNG-based validation is not possible anymore with 7.0 forms
                view_docs = [view_doc]
                if view_docs[0].tag == 'data':
                    # A <data> element is a wrapper for multiple root nodes
                    view_docs = view_docs[0]
                for view_arch in view_docs:
                    check = valid_view(view_arch, env=self.env, model=view.model)
                    view_name = ('%s (%s)' % (view.name, view.xml_id)) if view.xml_id else view.name
                    if not check:
                        raise ValidationError(_('Invalid view %s definition in %s') % (view_name, view.arch_fs))
                    if check == "Warning":
                        _logger.warning(_('Invalid view %s definition in %s \n%s'), view_name, view.arch_fs, view.arch)
        return True

    @api.constrains('type', 'groups_id')
    def _check_groups(self):
        for view in self:
            if view.type == 'qweb' and view.groups_id:
                raise ValidationError(_("Qweb view cannot have 'Groups' define on the record. Use 'groups' attributes inside the view definition"))

    @api.constrains('inherit_id')
    def _check_000_inheritance(self):
        # NOTE: constraints methods are check alphabetically. Always ensure this method will be
        #       called before other constraint metheods to avoid infinite loop in `read_combined`.
        if not self._check_recursion(parent='inherit_id'):
            raise ValidationError(_('You cannot create recursive inherited views.'))

    _sql_constraints = [
        ('inheritance_mode',
         "CHECK (mode != 'extension' OR inherit_id IS NOT NULL)",
         "Invalid inheritance mode: if the mode is 'extension', the view must"
         " extend an other view"),
        ('qweb_required_key',
         "CHECK (type != 'qweb' OR key IS NOT NULL)",
         "Invalid key: QWeb view should have a key"),
    ]

    def _auto_init(self):
        res = super(View, self)._auto_init()
        tools.create_index(self._cr, 'ir_ui_view_model_type_inherit_id',
                           self._table, ['model', 'inherit_id'])
        return res

    def _compute_defaults(self, values):
        if 'inherit_id' in values:
            # Do not automatically change the mode if the view already has an inherit_id,
            # and the user change it to another.
            if not values['inherit_id'] or all(not view.inherit_id for view in self):
                values.setdefault('mode', 'extension' if values['inherit_id'] else 'primary')
        return values

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if not values.get('type'):
                if values.get('inherit_id'):
                    values['type'] = self.browse(values['inherit_id']).type
                else:

                    try:
                        if not values.get('arch') and not values.get('arch_base'):
                            raise ValidationError(_('Missing view architecture.'))
                        values['type'] = etree.fromstring(values.get('arch') or values.get('arch_base')).tag
                    except LxmlError:
                        # don't raise here, the constraint that runs `self._check_xml` will
                        # do the job properly.
                        pass
            if not values.get('key') and values.get('type') == 'qweb':
                values['key'] = "gen_key.%s" % str(uuid.uuid4())[:6]
                if values.get('model'):
                    values['key'] = "%s.gen_key_%s" % (values.get('model'), str(uuid.uuid4())[:6])
            if not values.get('name'):
                values['name'] = "%s %s" % (values.get('model'), values['type'])
            # Create might be called with either `arch` (xml files), `arch_base` (form view) or `arch_db`.
            values['arch_prev'] = values.get('arch_base') or values.get('arch_db') or values.get('arch')
            values.update(self._compute_defaults(values))

        self.clear_caches()
        return super(View, self).create(vals_list)

    def write(self, vals):
        # Keep track if view was modified. That will be useful for the --dev mode
        # to prefer modified arch over file arch.
        if 'arch_updated' not in vals and ('arch' in vals or 'arch_base' in vals) and 'install_filename' not in self._context:
            vals['arch_updated'] = True

        # drop the corresponding view customizations (used for dashboards for example), otherwise
        # not all users would see the updated views
        custom_view = self.env['ir.ui.view.custom'].search([('ref_id', 'in', self.ids)])
        if custom_view:
            custom_view.unlink()

        self.clear_caches()
        if 'arch_db' in vals and not self.env.context.get('no_save_prev'):
            vals['arch_prev'] = self.arch_db

        res = super(View, self).write(self._compute_defaults(vals))

        # Check the xml of the view if it gets re-activated.
        # Ideally, `active` shoud have been added to the `api.constrains` of `_check_xml`,
        # but the ORM writes and validates regular field (such as `active`) before inverse fields (such as `arch`),
        # and therefore when writing `active` and `arch` at the same time, `_check_xml` is called twice,
        # and the first time it tries to validate the view without the modification to the arch,
        # which is problematic if the user corrects the view at the same time he re-enables it.
        if vals.get('active'):
            # Call `_validate_fields` instead of `_check_xml` to have the regular constrains error dialog
            # instead of the traceback dialog.
            self._validate_fields(['arch_db'])

        return res

    def unlink(self):
        # if in uninstall mode and has children views, emulate an ondelete cascade
        if self.env.context.get('_force_unlink', False) and self.inherit_children_ids:
            self.inherit_children_ids.unlink()
        return super(View, self).unlink()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        if self.key and default and 'key' not in default:
            new_key = self.key + '_%s' % str(uuid.uuid4())[:6]
            default = dict(default or {}, key=new_key)
        return super(View, self).copy(default)

    def toggle(self):
        """ Switches between enabled and disabled statuses
        """
        for view in self:
            view.write({'active': not view.active})

    # default view selection
    @api.model
    def default_view(self, model, view_type):
        """ Fetches the default view for the provided (model, view_type) pair:
         primary view with the lowest priority.

        :param str model:
        :param int view_type:
        :return: id of the default view of False if none found
        :rtype: int
        """
        domain = [('model', '=', model), ('type', '=', view_type), ('mode', '=', 'primary')]
        return self.search(domain, limit=1).id

    #------------------------------------------------------
    # Inheritance mecanism
    #------------------------------------------------------
    @api.model
    def _get_inheriting_views(self, view_id, model):
        conditions = self._get_inheriting_views_arch_domain(view_id, model)

        if self.pool._init and not self._context.get('load_all_views'):
            # Module init currently in progress, only consider views from
            # modules whose code is already loaded

            # Search terms inside an OR branch in a domain
            # cannot currently use relationships that are
            # not required. The root cause is the INNER JOIN
            # used to implement it.
            modules = tuple(self.pool._init_modules) + (self._context.get('install_module'),)
            views = self.search(conditions + [('model_ids.module', 'in', modules)])
            views_cond = [('id', 'in', list(self._context.get('check_view_ids') or (0,)) + views.ids)]
            views = self.search(conditions + views_cond, order=INHERIT_ORDER)
        else:
            views = self.search(conditions, order=INHERIT_ORDER)
        return views

    @api.model
    def _get_inheriting_views_arch_domain(self, view_id, model):
        return [
            ['inherit_id', '=', view_id],
            ['model', '=', model],
            ['mode', '=', 'extension'],
            ['active', '=', True],
        ]

    @api.model
    def get_inheriting_views_arch(self, view_id, model):
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

        user_groups = self.env.user.groups_id
        views = self._get_inheriting_views(view_id, model)

        return [(view.arch, view.id)
                for view in views.sudo()
                if not view.groups_id or (view.groups_id & user_groups)]

    @api.model
    def raise_view_error(self, message, view_id):
        view = self.browse(view_id)
        not_avail = _('n/a')
        message = (
            "%(msg)s\n\n" +
            _("Error context:\nView `%(view_name)s`") +
            "\n[view_id: %(viewid)s, xml_id: %(xmlid)s, "
            "model: %(model)s, parent_id: %(parent)s]"
        ) % {
            'view_name': view.name or not_avail,
            'viewid': view_id or not_avail,
            'xmlid': view.xml_id or not_avail,
            'model': view.model or not_avail,
            'parent': view.inherit_id.id or not_avail,
            'msg': message,
        }
        _logger.info(message)
        raise ValueError(message)

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
        return locate_node(arch, spec)

    def inherit_branding(self, specs_tree, view_id, root_id):
        for node in specs_tree.iterchildren(tag=etree.Element):
            xpath = node.getroottree().getpath(node)
            if node.tag == 'data' or node.tag == 'xpath' or node.get('position'):
                self.inherit_branding(node, view_id, root_id)
            elif node.get('t-field'):
                # Note: 'data-oe-field-xpath' and not 'data-oe-xpath' as this
                # was introduced as a fix. To avoid breaking customizations and
                # to make a minimal diff fix, a separated attribute was used.
                # TODO Try to use a common attribute in master (14.1).
                node.set('data-oe-field-xpath', xpath)
                self.inherit_branding(node, view_id, root_id)
            else:
                node.set('data-oe-id', str(view_id))
                node.set('data-oe-xpath', xpath)
                node.set('data-oe-model', 'ir.ui.view')
                node.set('data-oe-field', 'arch')
        return specs_tree

    @api.model
    def apply_inheritance_specs(self, source, specs_tree, inherit_id, pre_locate=lambda s: True):
        """ Apply an inheriting view (a descendant of the base view)

        Apply to a source architecture all the spec nodes (i.e. nodes
        describing where and what changes to apply to some parent
        architecture) given by an inheriting view.

        :param Element source: a parent architecture to modify
        :param Elepect specs_tree: a modifying architecture in an inheriting view
        :param inherit_id: the database id of specs_arch
        :param (optional) pre_locate: function that is execute before locating a node.
                                        This function receives an arch as argument.
        :return: a modified source where the specs are applied
        :rtype: Element
        """
        # Queue of specification nodes (i.e. nodes describing where and
        # changes to apply to some parent architecture).
        try:
            source = apply_inheritance_specs(source, specs_tree,
                                             inherit_branding=self._context.get('inherit_branding'),
                                             pre_locate=pre_locate)
        except ValueError as e:
            self.raise_view_error(str(e), inherit_id)
        return source

    @api.model
    def apply_view_inheritance(self, source, source_id, model, root_id=None):
        """ Apply all the (directly and indirectly) inheriting views.

        :param source: a parent architecture to modify (with parent modifications already applied)
        :param source_id: the database view_id of the parent view
        :param model: the original model for which we create a view (not
            necessarily the same as the source's model); only the inheriting
            views with that specific model will be applied.
        :return: a modified source where all the modifying architecture are applied
        """
        if root_id is None:
            root_id = source_id
        sql_inherit = self.get_inheriting_views_arch(source_id, model)
        for (specs, view_id) in sql_inherit:
            specs_tree = etree.fromstring(specs.encode('utf-8'))
            if self._context.get('inherit_branding'):
                self.inherit_branding(specs_tree, view_id, root_id)
            source = self.apply_inheritance_specs(source, specs_tree, view_id)
            source = self.apply_view_inheritance(source, view_id, model, root_id=root_id)
        return source

    def read_combined(self, fields=None):
        """
        Utility function to get a view combined with its inherited views.

        * Gets the top of the view tree if a sub-view is requested
        * Applies all inherited archs on the root view
        * Returns the view with all requested fields
          .. note:: ``arch`` is always added to the fields list even if not
                    requested (similar to ``id``)
        """
        # introduce check_view_ids in context
        if 'check_view_ids' not in self._context:
            self = self.with_context(check_view_ids=[])

        check_view_ids = self._context['check_view_ids']

        # if view_id is not a root view, climb back to the top.
        root = self
        while root.mode != 'primary':
            # Add inherited views to the list of loading forced views
            # Otherwise, inherited views could not find elements created in their direct parents if that parent is defined in the same module
            check_view_ids.append(root.id)
            root = root.inherit_id

        # arch and model fields are always returned
        if fields:
            fields = list({'arch', 'model'}.union(fields))

        # read the view arch
        [view_data] = root.read(fields=fields)
        view_arch = etree.fromstring(view_data['arch'].encode('utf-8'))
        if not root.inherit_id:
            if self._context.get('inherit_branding'):
                view_arch.attrib.update({
                    'data-oe-model': 'ir.ui.view',
                    'data-oe-id': str(root.id),
                    'data-oe-field': 'arch',
                })
            arch_tree = view_arch
        else:
            if self._context.get('inherit_branding'):
                self.inherit_branding(view_arch, root.id, root.id)
            parent_view = root.inherit_id.read_combined(fields=fields)
            arch_tree = etree.fromstring(parent_view['arch'])
            arch_tree = self.apply_inheritance_specs(arch_tree, view_arch, parent_view['id'])

        # and apply inheritance
        arch = self.apply_view_inheritance(arch_tree, root.id, self.model)

        return dict(view_data, arch=etree.tostring(arch, encoding='unicode'))

    def _apply_group(self, model, node, modifiers, fields):
        """Apply group restrictions,  may be set at view level or model level::
           * at view level this means the element should be made invisible to
             people who are not members
           * at model level (exclusively for fields, obviously), this means
             the field should be completely removed from the view, as it is
             completely unavailable for non-members

           :return: True if field should be included in the result of fields_view_get
        """
        Model = self.env[model]

        field_name = None
        if node.tag == "field":
            field_name = node.get("name")
        elif node.tag == "label":
            field_name = node.get("for")
        if field_name and field_name in Model._fields:
            field = Model._fields[field_name]
            if field.groups and not self.user_has_groups(groups=field.groups):
                node.getparent().remove(node)
                fields.pop(field_name, None)
                # no point processing view-level ``groups`` anymore, return
                return False
        if node.get('groups'):
            can_see = self.user_has_groups(groups=node.get('groups'))
            if not can_see:
                node.set('invisible', '1')
                modifiers['invisible'] = True
                if 'attrs' in node.attrib:
                    del node.attrib['attrs']    # avoid making field visible later
            del node.attrib['groups']
        return True

    #------------------------------------------------------
    # Postprocessing: translation, groups and modifiers
    #------------------------------------------------------
    # TODO: remove group processing from ir_qweb
    #------------------------------------------------------
    @api.model
    def postprocess(self, model, node, view_id, in_tree_view, model_fields):
        """Return the description of the fields in the node.

        In a normal call to this method, node is a complete view architecture
        but it is actually possible to give some sub-node (this is used so
        that the method can call itself recursively).

        Originally, the field descriptions are drawn from the node itself.
        But there is now some code calling fields_get() in order to merge some
        of those information in the architecture.

        """
        result = False
        fields = {}
        children = True

        modifiers = {}
        if model not in self.env:
            self.raise_view_error(_('Model not found: %(model)s') % dict(model=model), view_id)
        Model = self.env[model]

        if node.tag in ('field', 'node', 'arrow'):
            if node.get('object'):
                attrs = {}
                views = {}
                xml_form = E.form(*(f for f in node if f.tag == 'field'))
                xarch, xfields = self.with_context(base_model_name=model).postprocess_and_fields(node.get('object'), xml_form, view_id)
                views['form'] = {
                    'arch': xarch,
                    'fields': xfields,
                }
                attrs = {'views': views}
                fields = xfields
            if node.get('name'):
                attrs = {}
                field = Model._fields.get(node.get('name'))
                if field:
                    editable = self.env.context.get('view_is_editable', True) and field_is_editable(field, node)
                    children = False
                    views = {}
                    for f in node:
                        if f.tag in ('form', 'tree', 'graph', 'kanban', 'calendar'):
                            node.remove(f)
                            xarch, xfields = self.with_context(
                                base_model_name=model,
                                view_is_editable=editable,
                            ).postprocess_and_fields(field.comodel_name, f, view_id)
                            views[str(f.tag)] = {
                                'arch': xarch,
                                'fields': xfields,
                            }
                    attrs = {'views': views}
                    if field.comodel_name in self.env and field.type in ('many2one', 'many2many'):
                        Comodel = self.env[field.comodel_name]
                        node.set('can_create', 'true' if Comodel.check_access_rights('create', raise_exception=False) else 'false')
                        node.set('can_write', 'true' if Comodel.check_access_rights('write', raise_exception=False) else 'false')
                fields[node.get('name')] = attrs

                field = model_fields.get(node.get('name'))
                if field:
                    transfer_field_to_modifiers(field, modifiers)

        elif node.tag == 'groupby':
            # groupby nodes should be considered as nested view because they may
            # contain fields on the comodel
            field = Model._fields.get(node.get('name'))
            if field:
                if field.type != 'many2one':
                    self.raise_view_error(_("'groupby' tags can only target many2one (%(field)s)") % dict(field=field.name), view_id)
                attrs = fields.setdefault(node.get('name'), {})
                children = False
                # move all children nodes into a new node <groupby>
                groupby_node = E.groupby()
                for child in list(node):
                    node.remove(child)
                    groupby_node.append(child)
                # validate the new node as a nested view, and associate it to the field
                xarch, xfields = self.with_context(
                    base_model_name=model,
                    view_is_editable=False,
                ).postprocess_and_fields(field.comodel_name, groupby_node, view_id)
                attrs['views'] = {'groupby': {
                    'arch': xarch,
                    'fields': xfields,
                }}

        elif node.tag in ('form', 'tree'):
            result = Model.view_header_get(False, node.tag)
            if result:
                node.set('string', result)
            in_tree_view = node.tag == 'tree'

        elif node.tag == 'calendar':
            for additional_field in ('date_start', 'date_delay', 'date_stop', 'color', 'all_day'):
                if node.get(additional_field):
                    fields[node.get(additional_field).split('.', 1)[0]] = {}
            for f in node:
                if f.tag == 'filter':
                    fields[f.get('name')] = {}

        elif node.tag == 'search':
            searchpanel = [c for c in node if c.tag == 'searchpanel']
            if searchpanel:
                self.with_context(
                    base_model_name=model,
                    check_field_names=False,  # field validation is a bit more tricky and done apart
                    check_field_names_original=self.env.context.get('check_field_names'),
                    view_is_editable=False,
                ).postprocess_and_fields(model, searchpanel[0], view_id)

        if not self._apply_group(model, node, modifiers, fields):
            # node must be removed, no need to proceed further with its children
            return fields

        # The view architeture overrides the python model.
        # Get the attrs before they are (possibly) deleted by check_group below
        transfer_node_to_modifiers(node, modifiers, self._context, in_tree_view)

        for f in node:
            if node.tag == 'search' and f.tag == 'searchpanel':
                # searchpanel part has to be validated independently
                continue
            if children or (node.tag == 'field' and f.tag in ('filter', 'separator')):
                fields.update(self.postprocess(model, f, view_id, in_tree_view, model_fields))

        transfer_modifiers_to_node(modifiers, node)
        return fields

    def add_on_change(self, model_name, arch):
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
                        model = self.env[field.comodel_name]
            for child in node:
                collect(child, model)

        collect(arch, self.env[model_name])

        for field, nodes in field_nodes.items():
            # if field should trigger an onchange, add on_change="1" on the
            # nodes referring to field
            model = self.env[field.model_name]
            if model._has_onchange(field, field_nodes):
                for node in nodes:
                    if not node.get('on_change'):
                        node.set('on_change', '1')

        return arch

    @api.model
    def postprocess_and_fields(self, model, node, view_id):
        """ Return an architecture and a description of all the fields.

        The field description combines the result of fields_get() and
        postprocess().

        :param node: the architecture as as an etree
        :return: a tuple (arch, fields) where arch is the given node as a
            string and fields is the description of all the fields.

        """
        fields = {}
        if model not in self.env:
            self.raise_view_error(_('Model not found: %(model)s') % dict(model=model), view_id)
        Model = self.env[model]

        if node.tag == 'diagram':
            if node.getchildren()[0].tag == 'node':
                node_model = self.env[node.getchildren()[0].get('object')]
                node_fields = node_model.fields_get(None)
                fields.update(node_fields)
            if node.getchildren()[1].tag == 'arrow':
                arrow_fields = self.env[node.getchildren()[1].get('object')].fields_get(None)
                fields.update(arrow_fields)
        else:
            fields = Model.fields_get(None)

        node = self.add_on_change(model, node)

        attrs_fields = []
        if self.env.context.get('check_field_names'):
            editable = self.env.context.get('view_is_editable', True)
            attrs_fields = get_attrs_field_names(self.env, node, Model, editable)

        fields_def = self.postprocess(model, node, view_id, False, fields)
        self._postprocess_access_rights(model, node)

        arch = etree.tostring(node, encoding="unicode").replace('\t', '')
        for k in list(fields):
            if k not in fields_def:
                del fields[k]
        for field in fields_def:
            if field in fields:
                fields[field].update(fields_def[field])
            else:
                message = _("Field `%(field_name)s` does not exist") % dict(field_name=field)
                self.raise_view_error(message, view_id)

        missing = [item for item in attrs_fields if item[0] not in fields]
        if missing:
            msg_lines = []
            msg_fmt = _("Field %r used in attributes must be present in view but is missing:")
            line_fmt = _(" - %r in %s=%r")
            for name, lines in itertools.groupby(sorted(missing), itemgetter(0)):
                if msg_lines:
                    msg_lines.append("")
                msg_lines.append(msg_fmt % name)
                for line in lines:
                    msg_lines.append(line_fmt % line)
            self.raise_view_error("\n".join(msg_lines), view_id)

        return arch, fields

    def _postprocess_access_rights(self, model, node):
        """ Compute and set on node access rights based on view type. Specific
        views can add additional specific rights like creating columns for
        many2one-based grouping views. """
        Model = self.env[model]
        is_base_model = self.env.context.get('base_model_name', model) == model

        if node.tag == 'diagram':
            if node.getchildren()[0].tag == 'node':
                node_model = self.env[node.getchildren()[0].get('object')]
                if (not node.get("create") and
                        not node_model.check_access_rights('create', raise_exception=False) or
                        not self._context.get("create", True) and is_base_model):
                    node.set("create", 'false')

        if node.tag in ('kanban', 'tree', 'form', 'activity'):
            for action, operation in (('create', 'create'), ('delete', 'unlink'), ('edit', 'write')):
                if (not node.get(action) and
                        not Model.check_access_rights(operation, raise_exception=False) or
                        not self._context.get(action, True) and is_base_model):
                    node.set(action, 'false')

        if node.tag in ('kanban',):
            group_by_name = node.get('default_group_by')
            if group_by_name in Model._fields:
                group_by_field = Model._fields[group_by_name]
                if group_by_field.type == 'many2one':
                    group_by_model = Model.env[group_by_field.comodel_name]
                    for action, operation in (('group_create', 'create'), ('group_delete', 'unlink'), ('group_edit', 'write')):
                        if (not node.get(action) and
                                not group_by_model.check_access_rights(operation, raise_exception=False) or
                                not self._context.get(action, True) and is_base_model):
                            node.set(action, 'false')

        return node

    #------------------------------------------------------
    # QWeb template views
    #------------------------------------------------------

    def _read_template_keys(self):
        """ Return the list of context keys to use for caching ``_read_template``. """
        return ['lang', 'inherit_branding', 'editable', 'translatable', 'edit_translations']

    # apply ormcache_context decorator unless in dev mode...
    @api.model
    @tools.conditional(
        'xml' not in config['dev_mode'],
        tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'view_id',
                       'tuple(self._context.get(k) for k in self._read_template_keys())'),
    )
    def _read_template(self, view_id):
        arch = self.browse(view_id).read_combined(['arch'])['arch']
        arch_tree = etree.fromstring(arch)
        self.distribute_branding(arch_tree)
        arch = etree.tostring(arch_tree, encoding='unicode')
        return arch

    @api.model
    def read_template(self, xml_id):
        return self._read_template(self.get_view_id(xml_id))

    @api.model
    def get_view_id(self, template):
        """ Return the view ID corresponding to ``template``, which may be a
        view ID or an XML ID. Note that this method may be overridden for other
        kinds of template values.

        This method could return the ID of something that is not a view (when
        using fallback to `xmlid_to_res_id`).
        """
        if isinstance(template, int):
            return template
        if '.' not in template:
            raise ValueError('Invalid template id: %r' % template)
        view = self.search([('key', '=', template)], limit=1)
        return view and view.id or self.env['ir.model.data'].xmlid_to_res_id(template, raise_if_not_found=True)

    def clear_cache(self):
        """ Deprecated, use `clear_caches` instead. """
        if 'xml' not in config['dev_mode']:
            self.clear_caches()

    def _contains_branded(self, node):
        return node.tag == 't'\
            or 't-raw' in node.attrib\
            or 't-call' in node.attrib\
            or any(self.is_node_branded(child) for child in node.iterdescendants())

    def _pop_view_branding(self, element):
        distributed_branding = dict(
            (attribute, element.attrib.pop(attribute))
            for attribute in MOVABLE_BRANDING
            if element.get(attribute))
        return distributed_branding

    def distribute_branding(self, e, branding=None, parent_xpath='',
                            index_map=ConstantMapping(1)):
        if e.get('t-ignore') or e.tag == 'head':
            # remove any view branding possibly injected by inheritance
            attrs = set(MOVABLE_BRANDING)
            for descendant in e.iterdescendants(tag=etree.Element):
                if not attrs.intersection(descendant.attrib):
                    continue
                self._pop_view_branding(descendant)
            # TODO: find a better name and check if we have a string to boolean helper
            return

        node_path = e.get('data-oe-xpath')
        if node_path is None:
            node_path = "%s/%s[%d]" % (parent_xpath, e.tag, index_map[e.tag])
        if branding:
            if e.get('t-field'):
                # Note: 'data-oe-field-xpath' and not 'data-oe-xpath' as this
                # was introduced as a fix. To avoid breaking customizations and
                # to make a minimal diff fix, a separated attribute was used.
                # TODO Try to use a common attribute in master (14.1).
                e.set('data-oe-field-xpath', node_path)
            elif not e.get('data-oe-model'):
                e.attrib.update(branding)
                e.set('data-oe-xpath', node_path)
        if not e.get('data-oe-model'):
            return

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
                    if child.get('data-oe-xpath') or child.get('data-oe-field-xpath'):
                        # injected by view inheritance, skip otherwise
                        # generated xpath is incorrect
                        # Also, if a node is known to have been replaced during applying xpath
                        # increment its index to compute an accurate xpath for susequent nodes
                        replaced_node_tag = child.attrib.pop('meta-oe-xpath-replacing', None)
                        if replaced_node_tag:
                            indexes[replaced_node_tag] += 1
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
            (attr in ('data-oe-model', 'groups') or (attr.startswith('t-')))
            for attr in node.attrib
        )

    def translate_qweb(self, arch, lang):
        # Deprecated: templates are translated once read from database
        return arch

    @tools.ormcache('self.id')
    def get_view_xmlid(self):
        domain = [('model', '=', 'ir.ui.view'), ('res_id', '=', self.id)]
        xmlid = self.env['ir.model.data'].sudo().search_read(domain, ['module', 'name'])[0]
        return '%s.%s' % (xmlid['module'], xmlid['name'])

    @api.model
    def render_template(self, template, values=None, engine='ir.qweb'):
        return self.browse(self.get_view_id(template)).render(values, engine)

    def render(self, values=None, engine='ir.qweb', minimal_qcontext=False):
        assert isinstance(self.id, int)

        qcontext = dict() if minimal_qcontext else self._prepare_qcontext()
        qcontext.update(values or {})

        return self.env[engine].render(self.id, qcontext)

    @api.model
    def _prepare_qcontext(self):
        """ Returns the qcontext : rendering context with website specific value (required
            to render website layout template)
        """
        qcontext = dict(
            env=self.env,
            user_id=self.env["res.users"].browse(self.env.user.id),
            res_company=self.env.company.sudo(),
            keep_query=keep_query,
            request=request,  # might be unbound if we're not in an httprequest context
            debug=request.session.debug if request else '',
            test_mode_enabled=bool(config['test_enable'] or config['test_file']),
            json=json_scriptsafe,
            quote_plus=werkzeug.url_quote_plus,
            time=time,
            datetime=datetime,
            relativedelta=relativedelta,
            xmlid=self.key,
            viewid=self.id,
            to_text=pycompat.to_text,
            image_data_uri=image_data_uri,
        )
        return qcontext

    #------------------------------------------------------
    # Misc
    #------------------------------------------------------

    def open_translations(self):
        """ Open a view for editing the translations of field 'arch_db'. """
        return self.env['ir.translation'].translate_fields('ir.ui.view', self.id, 'arch_db')

    @api.model
    def graph_get(self, id, model, node_obj, conn_obj, src_node, des_node, label, scale):
        def rec_name(rec):
            return (rec.name if 'name' in rec else
                    rec.x_name if 'x_name' in rec else
                    None)

        nodes = []
        nodes_name = []
        transitions = []
        start = []
        tres = {}
        labels = {}
        no_ancester = []
        blank_nodes = []

        Model = self.env[model]
        Node = self.env[node_obj]

        for model_key, model_value in Model._fields.items():
            if model_value.type == 'one2many':
                if model_value.comodel_name == node_obj:
                    _Node_Field = model_key
                    _Model_Field = model_value.inverse_name
                for node_key, node_value in Node._fields.items():
                    if node_value.type == 'one2many':
                        if node_value.comodel_name == conn_obj:
                             # _Source_Field = "Incoming Arrows" (connected via des_node)
                            if node_value.inverse_name == des_node:
                                _Source_Field = node_key
                             # _Destination_Field = "Outgoing Arrows" (connected via src_node)
                            if node_value.inverse_name == src_node:
                                _Destination_Field = node_key

        record = Model.browse(id)
        for line in record[_Node_Field]:
            if line[_Source_Field] or line[_Destination_Field]:
                nodes_name.append((line.id, rec_name(line)))
                nodes.append(line.id)
            else:
                blank_nodes.append({'id': line.id, 'name': rec_name(line)})

            if 'flow_start' in line and line.flow_start:
                start.append(line.id)
            elif not line[_Source_Field]:
                no_ancester.append(line.id)

            for t in line[_Destination_Field]:
                transitions.append((line.id, t[des_node].id))
                tres[str(t['id'])] = (line.id, t[des_node].id)
                label_string = ""
                if label:
                    for lbl in safe_eval(label):
                        if tools.ustr(lbl) in t and tools.ustr(t[lbl]) == 'False':
                            label_string += ' '
                        else:
                            label_string = label_string + " " + tools.ustr(t[lbl])
                labels[str(t['id'])] = (line.id, label_string)

        g = graph(nodes, transitions, no_ancester)
        g.process(start)
        g.scale(*scale)
        result = g.result_get()
        results = {}
        for node_id, node_name in nodes_name:
            results[str(node_id)] = result[node_id]
            results[str(node_id)]['name'] = node_name
        return {'nodes': results,
                'transitions': tres,
                'label': labels,
                'blank_nodes': blank_nodes,
                'node_parent_field': _Model_Field}

    @api.model
    def _validate_custom_views(self, model):
        """Validate architecture of custom views (= without xml id) for a given model.
            This method is called at the end of registry update.
        """
        query = """SELECT max(v.id)
                     FROM ir_ui_view v
                LEFT JOIN ir_model_data md ON (md.model = 'ir.ui.view' AND md.res_id = v.id)
                    WHERE md.module IN (SELECT name FROM ir_module_module) IS NOT TRUE
                      AND v.model = %s
                      AND v.active = true
                 GROUP BY coalesce(v.inherit_id, v.id)"""
        self._cr.execute(query, [model])

        rec = self.browse(it[0] for it in self._cr.fetchall())
        return rec.with_context({'load_all_views': True})._check_xml()

    @api.model
    def _validate_module_views(self, module):
        """ Validate the architecture of all the views of a given module that
            are impacted by view updates, but have not been checked yet.
        """
        assert self.pool._init

        # only validate the views that still exist...
        prefix = module + '.'
        prefix_len = len(prefix)
        names = tuple(
            xmlid[prefix_len:]
            for xmlid in self.pool.loaded_xmlids
            if xmlid.startswith(prefix)
        )
        if not names:
            return

        # retrieve the views with an XML id that has not been checked yet, i.e.,
        # the views with noupdate=True on their xml id
        query = """
            SELECT v.id
            FROM ir_ui_view v
            JOIN ir_model_data md ON (md.model = 'ir.ui.view' AND md.res_id = v.id)
            WHERE md.module = %s AND md.name IN %s AND md.noupdate
        """
        self._cr.execute(query, (module, names))
        views = self.browse([row[0] for row in self._cr.fetchall()])

        for view in views:
            try:
                view._check_xml()
            except Exception as e:
                self.raise_view_error("Can't validate view:\n%s" % e, view.id)

    def _create_all_specific_views(self, processed_modules):
        """To be overriden and have specific view behaviour on create"""
        pass

    def _get_specific_views(self):
        """ Given a view, return a record set containing all the specific views
            for that view's key.
        """
        self.ensure_one()
        # Only qweb views have a specific conterpart
        if self.type != 'qweb':
            return self.env['ir.ui.view']
        # A specific view can have a xml_id if exported/imported but it will not be equals to it's key (only generic view will).
        return self.with_context(active_test=False).search([('key', '=', self.key)]).filtered(lambda r: not r.xml_id == r.key)

    def _load_records_write(self, values):
        """ During module update, when updating a generic view, we should also
            update its specific views (COW'd).
            Note that we will only update unmodified fields. That will mimic the
            noupdate behavior on views having an ir.model.data.
        """
        if self.type == 'qweb':
            for cow_view in self._get_specific_views():
                authorized_vals = {}
                for key in values:
                    if key != 'inherit_id' and cow_view[key] == self[key]:
                        authorized_vals[key] = values[key]
                # if inherit_id update, replicate change on cow view but
                # only if that cow view inherit_id wasn't manually changed
                inherit_id = values.get('inherit_id')
                if inherit_id and self.inherit_id.id != inherit_id and \
                   cow_view.inherit_id.key == self.inherit_id.key:
                    self._load_records_write_on_cow(cow_view, inherit_id, authorized_vals)
                else:
                    cow_view.with_context(no_cow=True).write(authorized_vals)
        super(View, self)._load_records_write(values)

    def _load_records_write_on_cow(self, cow_view, inherit_id, values):
        # for modules updated before `website`, we need to
        # store the change to replay later on cow views
        if not hasattr(self.pool, 'website_views_to_adapt'):
            self.pool.website_views_to_adapt = []
        self.pool.website_views_to_adapt.append((
            cow_view.id,
            inherit_id,
            values,
        ))


class ResetViewArchWizard(models.TransientModel):
    """ A wizard to reset views architecture. """
    _name = "reset.view.arch.wizard"
    _description = "Reset View Architecture Wizard"

    def _default_view_id(self):
        view_id = self._context.get('active_model') == 'ir.ui.view' and self._context.get('active_id') or []
        return view_id

    view_id = fields.Many2one('ir.ui.view', string='View', default=_default_view_id)
    view_name = fields.Char(related='view_id.name', string='View Name')
    arch_diff = fields.Html(string='Architecture Diff', compute='_compute_arch_diff', readonly=True, sanitize_tags=False)
    reset_mode = fields.Selection([
        ('soft', 'Restore previous version (soft reset).'),
        ('hard', 'Reset to file version (hard reset).')
    ], string='Reset Mode', default='soft', required=True, help="You might want to try a soft reset first.")

    @api.depends('reset_mode', 'view_id')
    def _compute_arch_diff(self):
        ''' Return the differences between the current view arch and either its
        previous or initial arch, depending of `reset_mode` (soft/hard).
        The diff will be returned in an HTML table like on github.com.
        '''
        def handle_style(html_diff):
            ''' The HtmlDiff lib will add some usefull classes on the DOM to
            identify elements. Simply replace those classes by BS4 ones.
            For the table to fit the modal width, some custom style is needed.
            '''
            to_replace = {
                'diff_header': 'diff_header bg-600 text-center align-top px-2',
                'diff_next': 'd-none',
                'diff_add': 'bg-success',
                'diff_chg': 'bg-warning',
                'diff_sub': 'bg-danger',
                'nowrap': '',
            }
            for old, new in to_replace.items():
                html_diff = html_diff.replace(old, new)
            html_diff += '''
                <style>
                    table.diff { width: 100%; }
                    table.diff .diff_header { white-space: nowrap; }
                    table.diff th.diff_header { width: 50%; }
                    table.diff td { word-break: break-all; }
                </style>
            '''
            return html_diff

        for view in self:
            soft = view.reset_mode == 'soft'
            arch_to_compare = False
            if soft:
                arch_to_compare = view.view_id.arch_prev
            elif not soft and view.view_id.arch_fs:
                arch_to_compare = view.view_id.with_context(read_arch_from_file=True, lang=None).arch

            diff = False
            if arch_to_compare:
                diff = HtmlDiff(tabsize=2).make_table(
                    arch_to_compare.splitlines(),
                    view.view_id.with_context(lang=None).arch.splitlines(),
                    _("Previous Arch") if soft else _("File Arch"),
                    _("Current Arch"),
                    context=True,  # Show only diff lines, not all the code
                )
                diff = handle_style(diff)
            view.arch_diff = diff

    def reset_view_button(self):
        self.ensure_one()
        self.view_id.reset_arch(self.reset_mode)
        return {'type': 'ir.actions.act_window_close'}
