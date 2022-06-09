# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import collections
import datetime
import fnmatch
import inspect
import json
import logging
import math
import pprint
import re
import time
import uuid
import warnings

from dateutil.relativedelta import relativedelta

import werkzeug, werkzeug.urls
from lxml import etree
from lxml.etree import LxmlError
from lxml.builder import E

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, AccessError
from odoo.http import request
from odoo.modules.module import get_resource_from_path, get_resource_path
from odoo.tools import config, ConstantMapping, get_diff, pycompat, apply_inheritance_specs, locate_node
from odoo.tools.convert import _fix_multiple_roots
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools import safe_eval, lazy_property, frozendict
from odoo.tools.view_validation import valid_view, get_variable_names, get_domain_identifiers, get_dict_asts
from odoo.tools.translate import xml_translate, TRANSLATED_ATTRS
from odoo.tools.image import image_data_uri
from odoo.models import check_method_name
from odoo.osv.expression import expression

_logger = logging.getLogger(__name__)

MOVABLE_BRANDING = ['data-oe-model', 'data-oe-id', 'data-oe-field', 'data-oe-xpath', 'data-oe-source-id']


def quick_eval(expr, globals_dict):
    """ Functionally identical to safe_eval(), but optimized with special-casing. """
    # most (~95%) elements are 1/True/0/False
    if expr == '1':
        return 1
    if expr == 'True':
        return True
    if expr == '0':
        return 0
    if expr == 'False':
        return False
    return safe_eval.safe_eval(expr, globals_dict)


def att_names(name):
    yield name
    yield f"t-att-{name}"
    yield f"t-attf-{name}"


def transfer_field_to_modifiers(field, modifiers):
    default_values = {}
    state_exceptions = {}
    for attr in ('invisible', 'readonly', 'required'):
        state_exceptions[attr] = []
        default_values[attr] = bool(field.get(attr))
    for state, modifs in field.get("states", {}).items():
        for modif in modifs:
            if default_values[modif[0]] != modif[1]:
                state_exceptions[modif[0]].append(state)

    for attr, default_value in default_values.items():
        if state_exceptions[attr]:
            modifiers[attr] = [("state", "not in" if default_value else "in", state_exceptions[attr])]
        else:
            modifiers[attr] = default_value


def transfer_node_to_modifiers(node, modifiers, context=None):
    # Don't deal with groups, it is done by check_group().
    # Need the context to evaluate the invisible attribute on tree views.
    # For non-tree views, the context shouldn't be given.
    if node.get('attrs'):
        attrs = node.get('attrs').strip()
        modifiers.update(ast.literal_eval(attrs))

    if node.get('states'):
        if 'invisible' in modifiers and isinstance(modifiers['invisible'], list):
            # TODO combine with AND or OR, use implicit AND for now.
            modifiers['invisible'].append(('state', 'not in', node.get('states').split(',')))
        else:
            modifiers['invisible'] = [('state', 'not in', node.get('states').split(','))]

    for attr in ('invisible', 'readonly', 'required'):
        value_str = node.get(attr)
        if value_str:
            value = bool(quick_eval(value_str, {'context': context or {}}))
            if (attr == 'invisible'
                    and any(parent.tag == 'tree' for parent in node.iterancestors())
                    and not any(parent.tag == 'header' for parent in node.iterancestors())):
                # Invisible in a tree view has a specific meaning, make it a
                # new key in the modifiers attribute.
                modifiers['column_invisible'] = value
            elif value or (attr not in modifiers or not isinstance(modifiers[attr], list)):
                # Don't set the attribute to False if a dynamic value was
                # provided (i.e. a domain from attrs or states).
                modifiers[attr] = value


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
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if name:
            return self._search([('user_id', operator, name)] + (args or []), limit=limit, access_rights_uid=name_get_uid)
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


def get_view_arch_from_file(filepath, xmlid):
    module, view_id = xmlid.split('.')

    xpath = f"//*[@id='{xmlid}' or @id='{view_id}']"
    # when view is created from model with inheritS of ir_ui_view, the
    # xmlid has been suffixed by '_ir_ui_view'. We need to also search
    # for views without this prefix.
    if view_id.endswith('_ir_ui_view'):
        # len('_ir_ui_view') == 11
        xpath = xpath[:-1] + f" or @id='{xmlid[:-11]}' or @id='{view_id[:-11]}']"

    document = etree.parse(filepath)
    for node in document.xpath(xpath):
        if node.tag == 'record':
            field_arch = node.find('field[@name="arch"]')
            if field_arch is not None:
                _fix_multiple_roots(field_arch)
                inner = ''.join(
                    etree.tostring(child, encoding='unicode')
                    for child in field_arch.iterchildren()
                )
                return field_arch.text + inner

            field_view = node.find('field[@name="view_id"]')
            if field_view is not None:
                ref_module, _, ref_view_id = field_view.attrib.get('ref').rpartition('.')
                ref_xmlid = f'{ref_module or module}.{ref_view_id}'
                return get_view_arch_from_file(filepath, ref_xmlid)

            return None

        elif node.tag == 'template':
            # The following dom operations has been copied from convert.py's _tag_template()
            if not node.get('inherit_id'):
                node.set('t-name', xmlid)
                node.tag = 't'
            else:
                node.tag = 'data'
            node.attrib.pop('id', None)
            return etree.tostring(node, encoding='unicode')

    _logger.warning("Could not find view arch definition in file '%s' for xmlid '%s'", filepath, xmlid)
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
                return m.group('prefix') + str(self.env['ir.model.data']._xmlid_to_res_id(xmlid))
            return re.sub(r'(?P<prefix>[^%])%\((?P<xmlid>.*?)\)[ds]', replacer, arch_fs)

        for view in self:
            arch_fs = None
            read_file = self._context.get('read_arch_from_file') or \
                ('xml' in config['dev_mode'] and not view.arch_updated)
            if read_file and view.arch_fs and (view.xml_id or view.key):
                xml_id = view.xml_id or view.key
                # It is safe to split on / herebelow because arch_fs is explicitely stored with '/'
                fullpath = get_resource_path(*view.arch_fs.split('/'))
                if fullpath:
                    arch_fs = get_view_arch_from_file(fullpath, xml_id)
                    # replace %(xml_id)s, %(xml_id)d, %%(xml_id)s, %%(xml_id)d by the res_id
                    if arch_fs:
                        arch_fs = resolve_external_ids(arch_fs, xml_id).replace('%%', '%')
                        if self.env.context.get('lang'):
                            tr = self._fields['arch_db'].get_trans_func(view)
                            arch_fs = tr(view.id, arch_fs)
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
        """ Reset the view arch to its previous arch (soft) or its XML file arch
        if exists (hard).
        """
        for view in self:
            arch = False
            if mode == 'soft':
                arch = view.arch_prev
            elif mode == 'hard' and view.arch_fs:
                arch = view.with_context(read_arch_from_file=True, lang=None).arch
            if arch:
                # Don't save current arch in previous since we reset, this arch is probably broken
                view.with_context(no_save_prev=True, lang=None).write({'arch_db': arch})

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
                    self._raise_view_error(message, node)
                if WRONGCLASS.search(node.get('expr', '')):
                    _logger.warning(
                        "Error-prone use of @class in view %s (%s): use the "
                        "hasclass(*classes) function to filter elements by "
                        "their classes", self.name, self.xml_id
                    )
            else:
                for attr in TRANSLATED_ATTRS:
                    if node.get(attr):
                        message = "View inheritance may not use attribute %r as a selector." % attr
                        self._raise_view_error(message, node)
        return True

    @api.constrains('arch_db')
    def _check_xml(self):
        # Sanity checks: the view should not break anything upon rendering!
        # Any exception raised below will cause a transaction rollback.
        partial_validation = self.env.context.get('ir_ui_view_partial_validation')
        self = self.with_context(validate_view_ids=(self._ids if partial_validation else True))

        for view in self:
            try:
                # verify the view is valid xml and that the inheritance resolves
                if view.inherit_id:
                    view_arch = etree.fromstring(view.arch)
                    view._valid_inheritance(view_arch)
                combined_arch = view._get_combined_arch()
                if view.type == 'qweb':
                    continue
            except ValueError as e:
                err = ValidationError(_(
                    "Error while validating view:\n\n%(error)s",
                    error=tools.ustr(e),
                )).with_traceback(e.__traceback__)
                err.context = getattr(e, 'context', None)
                raise err from None

            try:
                # verify that all fields used are valid, etc.
                view._validate_view(combined_arch, view.model)
                combined_archs = [combined_arch]
                if combined_archs[0].tag == 'data':
                    # A <data> element is a wrapper for multiple root nodes
                    combined_archs = combined_archs[0]
                for view_arch in combined_archs:
                    for node in view_arch.xpath('//*[@__validate__]'):
                        del node.attrib['__validate__']
                    check = valid_view(view_arch, env=self.env, model=view.model)
                    if not check:
                        view_name = ('%s (%s)' % (view.name, view.xml_id)) if view.xml_id else view.name
                        raise ValidationError(_(
                            'Invalid view %(name)s definition in %(file)s',
                            name=view_name, file=view.arch_fs
                        ))
                    if check == "Warning":
                        view_name = ('%s (%s)' % (view.name, view.xml_id)) if view.xml_id else view.name
                        _logger.warning('Invalid view %s definition in %s \n%s', view_name, view.arch_fs, view.arch)
            except ValueError as e:
                lines = etree.tostring(combined_arch, encoding='unicode').splitlines(keepends=True)
                fivelines = "".join(lines[max(0, e.context["line"]-3):e.context["line"]+2])
                err = ValidationError(_(
                    "Error while validating view near:\n\n%(fivelines)s\n%(error)s",
                    fivelines=fivelines, error=tools.ustr(e),
                ))
                err.context = e.context
                raise err.with_traceback(e.__traceback__) from None

        return True

    @api.constrains('type', 'groups_id', 'inherit_id')
    def _check_groups(self):
        for view in self:
            if (view.type == 'qweb' and
                view.groups_id and
                view.inherit_id and
                view.mode != 'primary'):
                raise ValidationError(_("Inherited Qweb view cannot have 'Groups' define on the record. Use 'groups' attributes inside the view definition"))

    @api.constrains('inherit_id')
    def _check_000_inheritance(self):
        # NOTE: constraints methods are check alphabetically. Always ensure this method will be
        #       called before other constraint methods to avoid infinite loop in `_get_combined_arch`.
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
            if not values.get('name'):
                values['name'] = "%s %s" % (values.get('model'), values['type'])
            # Create might be called with either `arch` (xml files), `arch_base` (form view) or `arch_db`.
            values['arch_prev'] = values.get('arch_base') or values.get('arch_db') or values.get('arch')
            # write on arch: bypass _inverse_arch()
            if 'arch' in values:
                values['arch_db'] = values.pop('arch')
                if 'install_filename' in self._context:
                    # we store the relative path to the resource instead of the absolute path, if found
                    # (it will be missing e.g. when importing data-only modules using base_import_module)
                    path_info = get_resource_from_path(self._context['install_filename'])
                    if path_info:
                        values['arch_fs'] = '/'.join(path_info[0:2])
                        values['arch_updated'] = False
            values.update(self._compute_defaults(values))

        self.clear_caches()
        result = super(View, self.with_context(ir_ui_view_partial_validation=True)).create(vals_list)
        return result.with_env(self.env)

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
    def _get_inheriting_views_domain(self):
        """ Return a domain to filter the sub-views to inherit from. """
        return [('active', '=', True)]

    @api.model
    def _get_filter_xmlid_query(self):
        """This method is meant to be overridden by other modules.
        """
        return """SELECT res_id FROM ir_model_data
                  WHERE res_id IN %(res_ids)s AND model = 'ir.ui.view' AND module IN %(modules)s
               """

    def _get_inheriting_views(self):
        """
        Determine the views that inherit from the current recordset, and return
        them as a recordset, ordered by priority then by id.
        """
        self.check_access_rights('read')
        domain = self._get_inheriting_views_domain()
        e = expression(domain, self.env['ir.ui.view'])
        from_clause, where_clause, where_params = e.query.get_sql()
        assert from_clause == '"ir_ui_view"', f"Unexpected from clause: {from_clause}"

        self._flush_search(domain, fields=['inherit_id', 'priority', 'model', 'mode'], order='id')
        query = f"""
            WITH RECURSIVE ir_ui_view_inherits AS (
                SELECT id, inherit_id, priority, mode, model
                FROM ir_ui_view
                WHERE id IN %s AND ({where_clause})
            UNION
                SELECT ir_ui_view.id, ir_ui_view.inherit_id, ir_ui_view.priority,
                       ir_ui_view.mode, ir_ui_view.model
                FROM ir_ui_view
                INNER JOIN ir_ui_view_inherits parent ON parent.id = ir_ui_view.inherit_id
                WHERE coalesce(ir_ui_view.model, '') = coalesce(parent.model, '')
                      AND ir_ui_view.mode = 'extension'
                      AND ({where_clause})
            )
            SELECT
                v.id, v.inherit_id, v.mode,
                ARRAY(SELECT r.group_id FROM ir_ui_view_group_rel r WHERE r.view_id=v.id)
            FROM ir_ui_view_inherits v
            ORDER BY v.priority, v.id
        """
        # ORDER BY v.priority, v.id:
        # 1/ sort by priority: abritrary value set by developers on some
        #    views to solve "dependency hell" problems and force a view
        #    to be combined earlier or later. e.g. all views created via
        #    studio have a priority=99 to be loaded last.
        # 2/ sort by view id: the order the views were inserted in the
        #    database. e.g. base views are placed before stock ones.

        self.env.cr.execute(query, [tuple(self.ids)] + where_params + where_params)
        rows = self.env.cr.fetchall()

        # filter out forbidden views
        if any(row[3] for row in rows):
            user_groups = set(self.env.user.groups_id.ids)
            rows = [row for row in rows if not (row[3] and user_groups.isdisjoint(row[3]))]

        views = self.browse(row[0] for row in rows)

        # optimization: fill in cache of inherit_id and mode
        self.env.cache.update(views, type(self).inherit_id, [row[1] for row in rows])
        self.env.cache.update(views, type(self).mode, [row[2] for row in rows])

        # During an upgrade, we can only use the views that have been
        # fully upgraded already.
        if self.pool._init and not self._context.get('load_all_views'):
            views = views._filter_loaded_views()

        return views

    def _filter_loaded_views(self):
        """
        During the module upgrade phase it may happen that a view is
        present in the database but the fields it relies on are not
        fully loaded yet. This method only considers views that belong
        to modules whose code is already loaded. Custom views defined
        directly in the database are loaded only after the module
        initialization phase is completely finished.
        """
        # check that all found ids have a corresponding xml_id in a loaded module
        check_view_ids = self.env.context['check_view_ids']
        ids_to_check = [vid for vid in self.ids if vid not in check_view_ids]
        if not ids_to_check:
            return self
        loaded_modules = tuple(self.pool._init_modules) + (self._context.get('install_module'),)
        query = self._get_filter_xmlid_query()
        self.env.cr.execute(query, {'res_ids': tuple(ids_to_check), 'modules': loaded_modules})
        valid_view_ids = {r[0] for r in self.env.cr.fetchall()} | set(check_view_ids)
        return self.browse(vid for vid in self.ids if vid in valid_view_ids)

    def _check_view_access(self):
        """ Verify that a view is accessible by the current user based on the
        groups attribute. Views with no groups are considered private.
        """
        if self.inherit_id and self.mode != 'primary':
            return self.inherit_id._check_view_access()
        if self.groups_id & self.env.user.groups_id:
            return True
        if self.groups_id:
            error = _(
                "View '%(name)s' accessible only to groups %(groups)s ",
                name=self.key,
                groups=", ".join([g.name for g in self.groups_id]
            ))
        else:
            error = _("View '%(name)s' is private", name=self.key)
        raise AccessError(error)

    def _raise_view_error(self, message, node=None, *, from_exception=None, from_traceback=None):
        """ Handle a view error by raising an exception.

        :param str message: message to raise or log, augmented with contextual
                            view information
        :param node: the lxml element where the error is located (if any)
        :param BaseException from_exception:
            when raising an exception, chain it to the provided one (default:
            disable chaining)
        :param types.TracebackType from_traceback:
            when raising an exception, start with this traceback (default: start
            at exception creation)
        """
        err = ValueError(message).with_traceback(from_traceback)
        err.context = {
            'view': self,
            'name': getattr(self, 'name', None),
            'xmlid': self.env.context.get('install_xmlid') or self.xml_id,
            'view.model': self.model,
            'view.parent': self.inherit_id,
            'file': self.env.context.get('install_filename'),
            'line': node.sourceline if node is not None else 1,
        }
        raise err from from_exception

    def _log_view_warning(self, message, node):
        """ Handle a view issue by logging a warning.

        :param str message: message to raise or log, augmented with contextual
                            view information
        :param node: the lxml element where the error is located (if any)
        """
        error_context = {
            'view': self,
            'name': getattr(self, 'name', None),
            'xmlid': self.env.context.get('install_xmlid') or self.xml_id,
            'view.model': self.model,
            'view.parent': self.inherit_id,
            'file': self.env.context.get('install_filename'),
            'line': node.sourceline if node is not None else 1,
        }
        _logger.warning(
            "%s\nView error context:\n%s",
            message, pprint.pformat(error_context)
        )

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

    def inherit_branding(self, specs_tree):
        for node in specs_tree.iterchildren(tag=etree.Element):
            xpath = node.getroottree().getpath(node)
            if node.tag == 'data' or node.tag == 'xpath' or node.get('position'):
                self.inherit_branding(node)
            elif node.get('t-field'):
                node.set('data-oe-xpath', xpath)
                self.inherit_branding(node)
            else:
                node.set('data-oe-id', str(self.id))
                node.set('data-oe-xpath', xpath)
                node.set('data-oe-model', 'ir.ui.view')
                node.set('data-oe-field', 'arch')
        return specs_tree

    def _add_validation_flag(self, combined_arch, view=None, arch=None):
        """ Add a validation flag on elements in ``combined_arch`` or ``arch``.
        This is part of the partial validation of views.

        :param Element combined_arch: the architecture to be modified by ``arch``
        :param view: an optional view inheriting ``self``
        :param Element arch: an optional modifying architecture from inheriting
            view ``view``
        """
        # validate_view_ids is either falsy (no validation), True (full
        # validation) or a collection of ids (partial validation)
        validate_view_ids = self.env.context.get('validate_view_ids')
        if not validate_view_ids:
            return

        if validate_view_ids is True or self.id in validate_view_ids:
            # optimization, flag the root node
            combined_arch.set('__validate__', '1')
            return

        if view is None or view.id not in validate_view_ids:
            return

        for node in arch.xpath('//*[@position]'):
            if node.get('position') in ('after', 'before', 'inside'):
                # validate the elements being inserted, except the ones that
                # specify a move, as in:
                #   <field name="foo" position="after">
                #       <field name="bar" position="move"/>
                #   </field>
                for child in node.iterchildren(tag=etree.Element):
                    if not child.get('position'):
                        child.set('__validate__', '1')
            if node.get('position') == 'replace':
                # validate everything, since this impacts the whole arch
                combined_arch.set('__validate__', '1')
                break
            if node.get('position') == 'attributes':
                # validate the element being modified by adding
                # attribute "__validate__" on it:
                #   <field name="foo" position="attributes">
                #       <attribute name="readonly">1</attribute>
                #       <attribute name="__validate__">1</attribute>    <!-- add this -->
                #   </field>
                node.append(E.attribute('1', name='__validate__'))

    @api.model
    def apply_inheritance_specs(self, source, specs_tree, pre_locate=lambda s: True):
        """ Apply an inheriting view (a descendant of the base view)

        Apply to a source architecture all the spec nodes (i.e. nodes
        describing where and what changes to apply to some parent
        architecture) given by an inheriting view.

        :param Element source: a parent architecture to modify
        :param Element specs_tree: a modifying architecture in an inheriting view
        :param (optional) pre_locate: function that is execute before locating a node.
                                        This function receives an arch as argument.
        :return: a modified source where the specs are applied
        :rtype: Element
        """
        # Queue of specification nodes (i.e. nodes describing where and
        # changes to apply to some parent architecture).
        try:
            source = apply_inheritance_specs(
                source, specs_tree,
                inherit_branding=self._context.get('inherit_branding'),
                pre_locate=pre_locate,
            )
        except ValueError as e:
            self._raise_view_error(str(e), specs_tree)
        return source

    def _combine(self, hierarchy: dict):
        """
        Return self's arch combined with its inherited views archs.

        :param hierarchy: mapping from parent views to their child views
        :return: combined architecture
        :rtype: Element
        """
        self.ensure_one()
        assert self.mode == 'primary'

        # We achieve a pre-order depth-first hierarchy traversal where
        # primary views (and their children) are traversed after all the
        # extensions for the current primary view have been visited.
        #
        # https://en.wikipedia.org/wiki/Tree_traversal#Depth-first_search_of_binary_tree
        #
        # Example:                  hierarchy = {
        #                               1: [2, 3],  # primary view
        #             1*                2: [4, 5],
        #            / \                3: [],
        #           2   3               4: [6],     # primary view
        #          / \                  5: [7, 8],
        #         4*  5                 6: [],
        #        /   / \                7: [],
        #       6   7   8               8: [],
        #                           }
        #
        # Tree traversal order (`view` and `queue` at the `while` stmt):
        #   1 [2, 3]
        #   2 [5, 3, 4]
        #   5 [7, 8, 3, 4]
        #   7 [8, 3, 4]
        #   8 [3, 4]
        #   3 [4]
        #   4 [6]
        #   6 []
        combined_arch = etree.fromstring(self.arch)
        if self.env.context.get('inherit_branding'):
            combined_arch.attrib.update({
                'data-oe-model': 'ir.ui.view',
                'data-oe-id': str(self.id),
                'data-oe-field': 'arch',
            })
        self._add_validation_flag(combined_arch)

        # The depth-first traversal is implemented with a double-ended queue.
        # The queue is traversed from left to right, and after each view in the
        # queue is processed, its children are pushed at the left of the queue,
        # so that they are traversed in order.  The queue is therefore mostly
        # used as a stack.  An exception is made for primary views, which are
        # pushed at the other end of the queue, so that they are applied after
        # all extensions have been applied.
        queue = collections.deque(sorted(hierarchy[self], key=lambda v: v.mode))
        while queue:
            view = queue.popleft()
            arch = etree.fromstring(view.arch)
            if view.env.context.get('inherit_branding'):
                view.inherit_branding(arch)
            self._add_validation_flag(combined_arch, view, arch)
            combined_arch = view.apply_inheritance_specs(combined_arch, arch)

            for child_view in reversed(hierarchy[view]):
                if child_view.mode == 'primary':
                    queue.append(child_view)
                else:
                    queue.appendleft(child_view)

        return combined_arch

    def read_combined(self, fields=None):
        """
        Utility function to get a view combined with its inherited views.

        * Gets the top of the view tree if a sub-view is requested
        * Applies all inherited archs on the root view
        * Returns the view with all requested fields
          .. note:: ``arch`` is always added to the fields list even if not
                    requested (similar to ``id``)
        """
        warnings.warn("use get_combined_arch() instead", DeprecationWarning, stacklevel=2)
        if fields:
            fields = list({'arch', 'model'}.union(fields))
        [result] = self.read(fields)
        result['arch'] = self.get_combined_arch()
        return result

    def get_combined_arch(self):
        """ Return the arch of ``self`` (as a string) combined with its inherited views. """
        return etree.tostring(self._get_combined_arch(), encoding='unicode')

    def _get_combined_arch(self):
        """ Return the arch of ``self`` (as an etree) combined with its inherited views. """
        root = self
        view_ids = []
        while True:
            view_ids.append(root.id)
            if not root.inherit_id:
                break
            root = root.inherit_id

        views = self.browse(view_ids)

        # Add inherited views to the list of loading forced views
        # Otherwise, inherited views could not find elements created in
        # their direct parents if that parent is defined in the same module
        # introduce check_view_ids in context
        if 'check_view_ids' not in views.env.context:
            views = views.with_context(check_view_ids=[])
        views.env.context['check_view_ids'].extend(view_ids)

        # Map each node to its children nodes. Note that all children nodes are
        # part of a single prefetch set, which is all views to combine.
        tree_views = views._get_inheriting_views()
        hierarchy = collections.defaultdict(list)
        for view in tree_views:
            hierarchy[view.inherit_id].append(view)

        # optimization: make root part of the prefetch set, too
        arch = root.with_prefetch(tree_views._prefetch_ids)._combine(hierarchy)
        return arch

    def _apply_groups(self, node, name_manager, node_info):
        """ Apply group restrictions: elements with a 'groups' attribute should
        be made invisible to people who are not members.
        """
        if node.get('groups'):
            can_see = self.user_has_groups(groups=node.get('groups'))
            if not can_see:
                node.set('invisible', '1')
                node_info['modifiers']['invisible'] = True
                if 'attrs' in node.attrib:
                    del node.attrib['attrs']    # avoid making field visible later
            del node.attrib['groups']

    #------------------------------------------------------
    # Postprocessing: translation, groups and modifiers
    #------------------------------------------------------
    # TODO: remove group processing from ir_qweb
    #------------------------------------------------------
    def postprocess_and_fields(self, node, model=None):
        """ Return an architecture and a description of all the fields.

        The field description combines the result of fields_get() and
        postprocess().

        :param self: the view to postprocess
        :param node: the architecture as an etree
        :param model: the view's reference model name
        :return: a tuple (arch, fields) where arch is the given node as a
            string and fields is the description of all the fields.

        """
        self and self.ensure_one()      # self is at most one view

        name_manager = self._postprocess_view(node, model or self.model)

        arch = etree.tostring(node, encoding="unicode").replace('\t', '')
        return arch, dict(name_manager.available_fields)

    def _postprocess_view(self, node, model_name, editable=True):
        """ Process the given architecture, modifying it in-place to add and
        remove stuff.

        :param self: the optional view to postprocess
        :param node: the combined architecture as an etree
        :param model_name: the view's reference model name
        :param editable: whether the view is considered editable
        :return: the processed architecture's NameManager
        """
        root = node

        if model_name not in self.env:
            self._raise_view_error(_('Model not found: %(model)s', model=model_name), root)
        model = self.env[model_name]

        self._postprocess_on_change(root, model)

        name_manager = NameManager(model)

        # use a stack to recursively traverse the tree
        stack = [(root, editable)]
        while stack:
            node, editable = stack.pop()

            # compute default
            tag = node.tag
            parent = node.getparent()
            node_info = {
                'modifiers': {},
                'editable': editable and self._editable_node(node, name_manager),
            }

            # tag-specific postprocessing
            postprocessor = getattr(self, f"_postprocess_tag_{tag}", None)
            if postprocessor is not None:
                postprocessor(node, name_manager, node_info)
                if node.getparent() is not parent:
                    # the node has been removed, stop processing here
                    continue

            self._apply_groups(node, name_manager, node_info)
            transfer_node_to_modifiers(node, node_info['modifiers'], self._context)
            transfer_modifiers_to_node(node_info['modifiers'], node)

            # if present, iterate on node_info['children'] instead of node
            for child in reversed(node_info.get('children', node)):
                stack.append((child, node_info['editable']))

        name_manager.update_available_fields()
        self._postprocess_access_rights(root, model.sudo(False))

        return name_manager

    def _postprocess_on_change(self, arch, model):
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

        collect(arch, model)

        for field, nodes in field_nodes.items():
            # if field should trigger an onchange, add on_change="1" on the
            # nodes referring to field
            model = self.env[field.model_name]
            if model._has_onchange(field, field_nodes):
                for node in nodes:
                    if not node.get('on_change'):
                        node.set('on_change', '1')

    def _postprocess_access_rights(self, node, model):
        """ Compute and set on node access rights based on view type. Specific
        views can add additional specific rights like creating columns for
        many2one-based grouping views. """
        # testing ACL as real user
        is_base_model = self.env.context.get('base_model_name', model._name) == model._name

        if node.tag in ('kanban', 'tree', 'form', 'activity'):
            for action, operation in (('create', 'create'), ('delete', 'unlink'), ('edit', 'write')):
                if (not node.get(action) and
                        not model.check_access_rights(operation, raise_exception=False) or
                        not self._context.get(action, True) and is_base_model):
                    node.set(action, 'false')

        if node.tag == 'kanban':
            group_by_name = node.get('default_group_by')
            group_by_field = model._fields.get(group_by_name)
            if group_by_field and group_by_field.type == 'many2one':
                group_by_model = model.env[group_by_field.comodel_name]
                for action, operation in (('group_create', 'create'), ('group_delete', 'unlink'), ('group_edit', 'write')):
                    if (not node.get(action) and
                            not group_by_model.check_access_rights(operation, raise_exception=False) or
                            not self._context.get(action, True) and is_base_model):
                        node.set(action, 'false')

    #------------------------------------------------------
    # Specific node postprocessors
    #------------------------------------------------------
    def _postprocess_tag_calendar(self, node, name_manager, node_info):
        for additional_field in ('date_start', 'date_delay', 'date_stop', 'color', 'all_day'):
            if node.get(additional_field):
                name_manager.has_field(node.get(additional_field).split('.', 1)[0])
        for f in node:
            if f.tag == 'filter':
                name_manager.has_field(f.get('name'))

    def _postprocess_tag_field(self, node, name_manager, node_info):
        if node.get('name'):
            attrs = {'id': node.get('id'), 'select': node.get('select')}
            field = name_manager.model._fields.get(node.get('name'))
            if field:
                # apply groups (no tested)
                if field.groups and not self.user_has_groups(groups=field.groups):
                    node.getparent().remove(node)
                    # no point processing view-level ``groups`` anymore, return
                    return
                views = {}
                for child in node:
                    if child.tag in ('form', 'tree', 'graph', 'kanban', 'calendar'):
                        node.remove(child)
                        sub_name_manager = self.with_context(
                            base_model_name=name_manager.model._name,
                        )._postprocess_view(
                            child, field.comodel_name, editable=node_info['editable'],
                        )
                        xarch = etree.tostring(child, encoding="unicode").replace('\t', '')
                        views[child.tag] = {
                            'arch': xarch,
                            'fields': dict(sub_name_manager.available_fields),
                        }
                attrs['views'] = views
                if field.type in ('many2one', 'many2many'):
                    comodel = self.env[field.comodel_name].sudo(False)
                    can_create = comodel.check_access_rights('create', raise_exception=False)
                    can_write = comodel.check_access_rights('write', raise_exception=False)
                    node.set('can_create', 'true' if can_create else 'false')
                    node.set('can_write', 'true' if can_write else 'false')

            name_manager.has_field(node.get('name'), attrs)

            field_info = name_manager.field_info.get(node.get('name'))
            if field_info:
                transfer_field_to_modifiers(field_info, node_info['modifiers'])

    def _postprocess_tag_form(self, node, name_manager, node_info):
        result = name_manager.model.view_header_get(False, node.tag)
        if result:
            node.set('string', result)

    def _postprocess_tag_groupby(self, node, name_manager, node_info):
        # groupby nodes should be considered as nested view because they may
        # contain fields on the comodel
        name = node.get('name')
        field = name_manager.model._fields.get(name)
        if not field or not field.comodel_name:
            return
        # move all children nodes into a new node <groupby>
        groupby_node = E.groupby(*node)
        # post-process the node as a nested view, and associate it to the field
        sub_name_manager = self.with_context(
            base_model_name=name_manager.model._name,
        )._postprocess_view(groupby_node, field.comodel_name, editable=False)
        xarch = etree.tostring(groupby_node, encoding="unicode").replace('\t', '')
        name_manager.has_field(name, {'views': {
            'groupby': {
                'arch': xarch,
                'fields': dict(sub_name_manager.available_fields),
            }
        }})

    def _postprocess_tag_label(self, node, name_manager, node_info):
        if node.get('for'):
            field = name_manager.model._fields.get(node.get('for'))
            if field and field.groups and not self.user_has_groups(groups=field.groups):
                node.getparent().remove(node)

    def _postprocess_tag_search(self, node, name_manager, node_info):
        searchpanel = [child for child in node if child.tag == 'searchpanel']
        if searchpanel:
            self.with_context(
                base_model_name=name_manager.model._name,
            )._postprocess_view(
                searchpanel[0], name_manager.model._name, editable=False,
            )
            node_info['children'] = [child for child in node if child.tag != 'searchpanel']

    def _postprocess_tag_tree(self, node, name_manager, node_info):
        # reuse form view post-processing
        self._postprocess_tag_form(node, name_manager, node_info)

    #-------------------------------------------------------------------
    # view editability
    #-------------------------------------------------------------------

    def _editable_node(self, node, name_manager):
        """ Return whether the given node must be considered editable. """
        func = getattr(self, f"_editable_tag_{node.tag}", None)
        if func is not None:
            return func(node, name_manager)
        # by default views are non-editable
        return node.tag not in (item[0] for item in type(self).type.selection)

    def _editable_tag_form(self, node, name_manager):
        return True

    def _editable_tag_tree(self, node, name_manager):
        return node.get('editable')

    def _editable_tag_field(self, node, name_manager):
        field = name_manager.model._fields.get(node.get('name'))
        return field is None or field.is_editable() and (
            node.get('readonly') not in ('1', 'True')
            or get_dict_asts(node.get('attrs') or "{}")
        )

    #-------------------------------------------------------------------
    # view validation
    #-------------------------------------------------------------------

    def _validate_view(self, node, model_name, editable=True, full=False):
        """ Validate the given architecture node, and return its corresponding
        NameManager.

        :param self: the view being validated
        :param node: the combined architecture as an etree
        :param model_name: the reference model name for the given architecture
        :param editable: whether the view is considered editable
        :param full: whether the whole view must be validated
        :return: the combined architecture's NameManager
        """
        self.ensure_one()

        if model_name not in self.env:
            self._raise_view_error(_('Model not found: %(model)s', model=model_name), node)

        # fields_get() optimization: validation does not require translations
        model = self.env[model_name].with_context(lang=None)
        name_manager = NameManager(model)

        # use a stack to recursively traverse the tree
        stack = [(node, editable, full)]
        while stack:
            node, editable, validate = stack.pop()

            # compute default
            tag = node.tag
            validate = validate or node.get('__validate__')
            node_info = {
                'editable': editable and self._editable_node(node, name_manager),
                'validate': validate,
            }

            # tag-specific validation
            validator = getattr(self, f"_validate_tag_{tag}", None)
            if validator is not None:
                validator(node, name_manager, node_info)

            if validate:
                self._validate_attrs(node, name_manager, node_info)

            for child in reversed(node):
                stack.append((child, node_info['editable'], validate))

        name_manager.check(self)

        return name_manager

    #------------------------------------------------------
    # Node validator
    #------------------------------------------------------
    def _validate_tag_form(self, node, name_manager, node_info):
        pass

    def _validate_tag_tree(self, node, name_manager, node_info):
        # reuse form view validation
        self._validate_tag_form(node, name_manager, node_info)
        if not node_info['validate']:
            return
        allowed_tags = ('field', 'button', 'control', 'groupby', 'widget', 'header')
        for child in node.iterchildren(tag=etree.Element):
            if child.tag not in allowed_tags and not isinstance(child, etree._Comment):
                msg = _(
                    'Tree child can only have one of %(tags)s tag (not %(wrong_tag)s)',
                    tags=', '.join(allowed_tags), wrong_tag=child.tag,
                )
                self._raise_view_error(msg, child)

    def _validate_tag_graph(self, node, name_manager, node_info):
        if not node_info['validate']:
            return
        for child in node.iterchildren(tag=etree.Element):
            if child.tag != 'field' and not isinstance(child, etree._Comment):
                msg = _('A <graph> can only contains <field> nodes, found a <%s>', child.tag)
                self._raise_view_error(msg, child)

    def _validate_tag_calendar(self, node, name_manager, node_info):
        for additional_field in ('date_start', 'date_delay', 'date_stop', 'color', 'all_day'):
            if node.get(additional_field):
                name_manager.has_field(node.get(additional_field).split('.', 1)[0])
        for f in node:
            if f.tag == 'filter':
                name_manager.has_field(f.get('name'))

    def _validate_tag_search(self, node, name_manager, node_info):
        if node_info['validate'] and not node.iterdescendants(tag="field"):
            # the field of the search view may be within a group node, which is why we must check
            # for all descendants containing a node with a field tag, if this is not the case
            # then a search is not possible.
            self._log_view_warning('Search tag requires at least one field element', node)

        searchpanels = [child for child in node if child.tag == 'searchpanel']
        if searchpanels:
            if len(searchpanels) > 1:
                self._raise_view_error(_('Search tag can only contain one search panel'), node)
            node.remove(searchpanels[0])
            self._validate_view(searchpanels[0], name_manager.model._name,
                                editable=False, full=node_info['validate'])

    def _validate_tag_field(self, node, name_manager, node_info):
        validate = node_info['validate']

        name = node.get('name')
        if not name:
            self._raise_view_error(_("Field tag must have a \"name\" attribute defined"), node)

        field = name_manager.model._fields.get(name)
        if field:
            if validate and field.relational:
                domain = (
                    node.get('domain')
                    or node_info['editable'] and field._description_domain(self.env)
                )
                if isinstance(domain, str):
                    # dynamic domain: in [('foo', '=', bar)], field 'foo' must
                    # exist on the comodel and field 'bar' must be in the view
                    desc = (f'domain of <field name="{name}">' if node.get('domain')
                            else f"domain of field '{name}'")
                    fnames, vnames = self._get_domain_identifiers(node, domain, desc)
                    self._check_field_paths(node, fnames, field.comodel_name, f"{desc} ({domain})")
                    if vnames:
                        name_manager.must_have_fields(vnames, f"{desc} ({domain})")

            elif validate and node.get('domain'):
                msg = _(
                    'Domain on non-relational field "%(name)s" makes no sense (domain:%(domain)s)',
                    name=name, domain=node.get('domain'),
                )
                self._raise_view_error(msg, node)

            for child in node:
                if child.tag not in ('form', 'tree', 'graph', 'kanban', 'calendar'):
                    continue
                node.remove(child)
                sub_manager = self._validate_view(
                    child, field.comodel_name, editable=node_info['editable'], full=validate,
                )
                for fname, use in sub_manager.mandatory_parent_fields.items():
                    name_manager.must_have_field(fname, use)

        elif validate and name not in name_manager.field_info:
            msg = _(
                'Field "%(field_name)s" does not exist in model "%(model_name)s"',
                field_name=name, model_name=name_manager.model._name,
            )
            self._raise_view_error(msg, node)

        name_manager.has_field(name, {'id': node.get('id'), 'select': node.get('select')})

        if validate:
            for attribute in ('invisible', 'readonly', 'required'):
                val = node.get(attribute)
                if val:
                    res = quick_eval(val, {'context': self._context})
                    if res not in (1, 0, True, False, None):
                        msg = _(
                            'Attribute %(attribute)s evaluation expects a boolean, got %(value)s',
                            attribute=attribute, value=val,
                        )
                        self._raise_view_error(msg, node)

    def _validate_tag_filter(self, node, name_manager, node_info):
        if not node_info['validate']:
            return
        domain = node.get('domain')
        if domain:
            name = node.get('name')
            desc = f'domain of <filter name="{name}">' if name else 'domain of <filter>'
            fnames, vnames = self._get_domain_identifiers(node, domain, desc)
            self._check_field_paths(node, fnames, name_manager.model._name, f"{desc} ({domain})")
            if vnames:
                name_manager.must_have_fields(vnames, f"{desc} ({domain})")

    def _validate_tag_button(self, node, name_manager, node_info):
        if not node_info['validate']:
            return
        name = node.get('name')
        special = node.get('special')
        type_ = node.get('type')
        if special:
            if special not in ('cancel', 'save', 'add'):
                self._raise_view_error(_("Invalid special '%(value)s' in button", value=special), node)
        elif type_:
            if type_ == 'edit': # list_renderer, used in kanban view
                return
            elif not name:
                self._raise_view_error(_("Button must have a name"), node)
            elif type_ == 'object':
                func = getattr(type(name_manager.model), name, None)
                if not func:
                    msg = _(
                        "%(action_name)s is not a valid action on %(model_name)s",
                        action_name=name, model_name=name_manager.model._name,
                    )
                    self._raise_view_error(msg, node)
                try:
                    check_method_name(name)
                except AccessError:
                    msg = _(
                        "%(method)s on %(model)s is private and cannot be called from a button",
                        method=name, model=name_manager.model._name,
                    )
                    self._raise_view_error(msg, node)
                try:
                    inspect.signature(func).bind(self=name_manager.model)
                except TypeError:
                    msg = "%s on %s has parameters and cannot be called from a button"
                    self._log_view_warning(msg % (name, name_manager.model._name), node)
            elif type_ == 'action':
                # logic mimics /web/action/load behaviour
                action = False
                try:
                    action_id = int(name)
                except ValueError:
                    model, action_id = self.env['ir.model.data']._xmlid_to_res_model_res_id(name, raise_if_not_found=False)
                    if not action_id:
                        msg = _("Invalid xmlid %(xmlid)s for button of type action.", xmlid=name)
                        self._raise_view_error(msg, node)
                    if not issubclass(self.pool[model], self.pool['ir.actions.actions']):
                        msg = _(
                            "%(xmlid)s is of type %(xmlid_model)s, expected a subclass of ir.actions.actions",
                            xmlid=name, xmlid_model=model,
                        )
                        self._raise_view_error(msg, node)
                action = self.env['ir.actions.actions'].browse(action_id).exists()
                if not action:
                    msg = _(
                        "Action %(action_reference)s (id: %(action_id)s) does not exist for button of type action.",
                        action_reference=name, action_id=action_id,
                    )
                    self._raise_view_error(msg, node)

            name_manager.has_action(name)
        elif node.get('icon'):
            description = 'A button with icon attribute (%s)' % node.get('icon')
            self._validate_fa_class_accessibility(node, description)

    def _validate_tag_groupby(self, node, name_manager, node_info):
        # groupby nodes should be considered as nested view because they may
        # contain fields on the comodel
        name = node.get('name')
        if not name:
            return
        field = name_manager.model._fields.get(name)
        if field:
            if node_info['validate']:
                if field.type != 'many2one':
                    msg = _(
                        "Field '%(name)s' found in 'groupby' node can only be of type many2one, found %(type)s",
                        name=field.name, type=field.type,
                    )
                    self._raise_view_error(msg, node)
                domain = node_info['editable'] and field._description_domain(self.env)
                if isinstance(domain, str):
                    desc = f"domain of field '{name}'"
                    fnames, vnames = self._get_domain_identifiers(node, domain, desc)
                    self._check_field_paths(node, fnames, field.comodel_name, f"{desc} ({domain})")
                    if vnames:
                        name_manager.must_have_fields(vnames, f"{desc} ({domain})")

            # move all children nodes into a new node <groupby>
            groupby_node = E.groupby(*node)
            # validate the node as a nested view
            sub_manager = self._validate_view(
                groupby_node, field.comodel_name, editable=False, full=node_info['validate'],
            )
            name_manager.has_field(name)
            for fname, use in sub_manager.mandatory_parent_fields.items():
                name_manager.must_have_field(fname, use)

        elif node_info['validate']:
            msg = _(
                "Field '%(field)s' found in 'groupby' node does not exist in model %(model)s",
                field=name, model=name_manager.model._name,
            )
            self._raise_view_error(msg, node)

    def _validate_tag_searchpanel(self, node, name_manager, node_info):
        if not node_info['validate']:
            return
        for child in node.iterchildren(tag=etree.Element):
            if child.get('domain') and child.get('select') != 'multi':
                msg = _('Searchpanel item with select multi cannot have a domain.')
                self._raise_view_error(msg, child)

    def _validate_tag_label(self, node, name_manager, node_info):
        if not node_info['validate']:
            return
        # replace return not arch.xpath('//label[not(@for) and not(descendant::input)]')
        for_ = node.get('for')
        if not for_:
            msg = _('Label tag must contain a "for". To match label style '
                    'without corresponding field or button, use \'class="o_form_label"\'.')
            self._raise_view_error(msg, node)
        else:
            name_manager.must_have_name(for_, '<label for="...">')

    def _validate_tag_page(self, node, name_manager, node_info):
        if not node_info['validate']:
            return
        if node.getparent() is None or node.getparent().tag != 'notebook':
            self._raise_view_error(_('Page direct ancestor must be notebook'), node)

    def _validate_tag_img(self, node, name_manager, node_info):
        if node_info['validate'] and not any(node.get(alt) for alt in att_names('alt')):
            self._log_view_warning('<img> tag must contain an alt attribute', node)

    def _validate_tag_a(self, node, name_manager, node_info):
        #('calendar', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
        if node_info['validate'] and any('btn' in node.get(cl, '') for cl in att_names('class')):
            if node.get('role') != 'button':
                msg = '"<a>" tag with "btn" class must have "button" role'
                self._log_view_warning(msg, node)

    def _validate_tag_ul(self, node, name_manager, node_info):
        if node_info['validate']:
            # was applied to all nodes, but in practice only used on div and ul
            self._check_dropdown_menu(node)

    def _validate_tag_div(self, node, name_manager, node_info):
        if node_info['validate']:
            self._check_dropdown_menu(node)
            self._check_progress_bar(node)

    #------------------------------------------------------
    # Validation tools
    #------------------------------------------------------

    def _check_dropdown_menu(self, node):
        #('calendar', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
        if any('dropdown-menu' in node.get(cl, '') for cl in att_names('class')):
            if node.get('role') != 'menu':
                msg = 'dropdown-menu class must have menu role'
                self._log_view_warning(msg, node)

    def _check_progress_bar(self, node):
        if any('o_progressbar' in node.get(cl, '') for cl in att_names('class')):
            if node.get('role') != 'progressbar':
                msg = 'o_progressbar class must have progressbar role'
                self._log_view_warning(msg, node)
            if not any(node.get(at) for at in att_names('aria-valuenow')):
                msg = 'o_progressbar class must have aria-valuenow attribute'
                self._log_view_warning(msg, node)
            if not any(node.get(at) for at in att_names('aria-valuemin')):
                msg = 'o_progressbar class must have aria-valuemin attribute'
                self._log_view_warning(msg, node)
            if not any(node.get(at) for at in att_names('aria-valuemax')):
                msg = 'o_progressbar class must have aria-valuemaxattribute'
                self._log_view_warning(msg, node)

    def _validate_attrs(self, node, name_manager, node_info):
        """ Generic validation of node attrs. """
        for attr, expr in node.items():
            if attr in ('class', 't-att-class', 't-attf-class'):
                self._validate_classes(node, expr)

            elif attr == 'attrs':
                for key, val_ast in get_dict_asts(expr).items():
                    if isinstance(val_ast, ast.List):
                        # domains in attrs are used for readonly, invisible, ...
                        # and thus are only executed client side
                        fnames, vnames = self._get_domain_identifiers(node, val_ast, attr, expr)
                        name_manager.must_have_fields(fnames | vnames, f"attrs ({expr})")
                    else:
                        vnames = get_variable_names(val_ast)
                        if vnames:
                            name_manager.must_have_fields(vnames, f"attrs ({expr})")

            elif attr == 'context':
                for key, val_ast in get_dict_asts(expr).items():
                    if key == 'group_by':  # only in context
                        if not isinstance(val_ast, ast.Str):
                            msg = _(
                                '"group_by" value must be a string %(attribute)s=%(value)r',
                                attribute=attr, value=expr,
                            )
                            self._raise_view_error(msg, node)
                        group_by = val_ast.s
                        fname = group_by.split(':')[0]
                        if fname not in name_manager.model._fields:
                            msg = _(
                                'Unknown field "%(field)s" in "group_by" value in %(attribute)s=%(value)r',
                                field=fname, attribute=attr, value=expr,
                            )
                            self._raise_view_error(msg, node)
                    else:
                        vnames = get_variable_names(val_ast)
                        if vnames:
                            name_manager.must_have_fields(vnames, f"context ({expr})")

            elif attr == 'groups':
                for group in expr.replace('!', '').split(','):
                    # further improvement: add all groups to name_manager in
                    # order to batch check them at the end
                    if not self.env['ir.model.data']._xmlid_to_res_id(group.strip(), raise_if_not_found=False):
                        msg = "The group %r defined in view does not exist!"
                        self._log_view_warning(msg % group, node)

            elif attr in ('col', 'colspan'):
                # col check is mainly there for the tag 'group', but previous
                # check was generic in view form
                if not expr.isdigit():
                    self._raise_view_error(
                        _('%(attribute)r value must be an integer (%(value)s)',
                          attribute=attr, value=expr),
                        node,
                    )

            elif attr.startswith('decoration-'):
                vnames = get_variable_names(expr)
                if vnames:
                    name_manager.must_have_fields(vnames, f"{attr}={expr}")

            elif attr == 'data-toggle' and expr == 'tab':
                if node.get('role') != 'tab':
                    msg = 'tab link (data-toggle="tab") must have "tab" role'
                    self._log_view_warning(msg, node)
                aria_control = node.get('aria-controls') or node.get('t-att-aria-controls')
                if not aria_control and not node.get('t-attf-aria-controls'):
                    msg = 'tab link (data-toggle="tab") must have "aria_control" defined'
                    self._log_view_warning(msg, node)
                if aria_control and '#' in aria_control:
                    msg = 'aria-controls in tablink cannot contains "#"'
                    self._log_view_warning(msg, node)

            elif attr == "role" and expr in ('presentation', 'none'):
                msg = ("A role cannot be `none` or `presentation`. "
                    "All your elements must be accessible with screen readers, describe it.")
                self._log_view_warning(msg, node)

            elif attr == 'group':
                msg = "attribute 'group' is not valid.  Did you mean 'groups'?"
                self._log_view_warning(msg, node)

    def _validate_classes(self, node, expr):
        """ Validate the classes present on node. """
        classes = set(expr.split(' '))
        # Be careful: not always true if it is an expression
        # example: <div t-attf-class="{{!selection_mode ? 'oe_kanban_color_' + kanban_getcolor(record.color.raw_value) : ''}} oe_kanban_card oe_kanban_global_click oe_applicant_kanban oe_semantic_html_override">
        if 'modal' in classes and node.get('role') != 'dialog':
            msg = '"modal" class should only be used with "dialog" role'
            self._log_view_warning(msg, node)

        if 'modal-header' in classes and node.tag != 'header':
            msg = '"modal-header" class should only be used in "header" tag'
            self._log_view_warning(msg, node)

        if 'modal-body' in classes and node.tag != 'main':
            msg = '"modal-body" class should only be used in "main" tag'
            self._log_view_warning(msg, node)

        if 'modal-footer' in classes and node.tag != 'footer':
            msg = '"modal-footer" class should only be used in "footer" tag'
            self._log_view_warning(msg, node)

        if 'tab-pane' in classes and node.get('role') != 'tabpanel':
            msg = '"tab-pane" class should only be used with "tabpanel" role'
            self._log_view_warning(msg, node)

        if 'nav-tabs' in classes and node.get('role') != 'tablist':
            msg = 'A tab list with class nav-tabs must have role="tablist"'
            self._log_view_warning(msg, node)

        if any(klass.startswith('alert-') for klass in classes):
            if (
                node.get('role') not in ('alert', 'alertdialog', 'status')
                and 'alert-link' not in classes
            ):
                msg = ("An alert (class alert-*) must have an alert, alertdialog or "
                        "status role or an alert-link class. Please use alert and "
                        "alertdialog only for what expects to stop any activity to "
                        "be read immediately.")
                self._log_view_warning(msg, node)

        if any(klass.startswith('fa-') for klass in classes):
            description = 'A <%s> with fa class (%s)' % (node.tag, expr)
            self._validate_fa_class_accessibility(node, description)

        if any(klass.startswith('btn') for klass in classes):
            if node.tag in ('a', 'button', 'select'):
                pass
            elif node.tag == 'input' and node.get('type') in ('button', 'submit', 'reset'):
                pass
            elif any(klass in classes for klass in ('btn-group', 'btn-toolbar', 'btn-ship')):
                pass
            else:
                msg = ("A simili button must be in tag a/button/select or tag `input` "
                        "with type button/submit/reset or have class in "
                        "btn-group/btn-toolbar/btn-ship")
                self._log_view_warning(msg, node)

    def _validate_fa_class_accessibility(self, node, description):
        valid_aria_attrs = {
            *att_names('title'), *att_names('aria-label'), *att_names('aria-labelledby'),
        }
        valid_t_attrs = {'t-value', 't-raw', 't-field', 't-esc'}

        ## Following or preceding text
        if (node.tail or '').strip() or (node.getparent().text or '').strip():
            # text<i class="fa-..."/> or <i class="fa-..."/>text or
            return

        ## Following or preceding text in span
        def has_text(elem):
            if elem is None:
                return False
            if elem.tag == 'span' and elem.text:
                return True
            if elem.tag == 't' and (elem.get('t-esc') or elem.get('t-raw')):
                return True
            return False

        if has_text(node.getnext()) or has_text(node.getprevious()):
            return

        ## Aria label can be on ancestors
        def has_title_or_aria_label(node):
            return any(node.get(attr) for attr in valid_aria_attrs)

        parent = node.getparent()
        while parent is not None:
            if has_title_or_aria_label(parent):
                return
            parent = parent.getparent()

        ## And we ignore all elements with describing in children
        def contains_description(node, depth=0):
            if depth > 2:
                _logger.warning('excessive depth in fa')
            if any(node.get(attr) for attr in valid_t_attrs):
                return True
            if has_title_or_aria_label(node):
                return True
            if node.tag in ('label', 'field'):
                return True
            if node.tag == 'button' and node.get('string'):
                return True
            if node.text:  # not sure, does it match *[text()]
                return True
            return any(contains_description(child, depth+1) for child in node)

        if contains_description(node):
            return

        msg = ('%s must have title in its tag, parents, descendants or have text')
        self._log_view_warning(msg % description, node)

    def _get_domain_identifiers(self, node, domain, use, expr=None):
        try:
            return get_domain_identifiers(domain)
        except ValueError:
            msg = _("Invalid domain format %(expr)s in %(use)s", expr=expr or domain, use=use)
            self._raise_view_error(msg, node)

    def _check_field_paths(self, node, field_paths, model_name, use):
        """ Check whether the given field paths (dot-separated field names)
        correspond to actual sequences of fields on the given model.
        """
        for field_path in field_paths:
            names = field_path.split('.')
            Model = self.pool[model_name]
            for index, name in enumerate(names):
                if Model is None:
                    msg = _(
                        'Non-relational field %(field)r in path %(field_path)r in %(use)s)',
                        field=names[index - 1], field_path=field_path, use=use,
                    )
                    self._raise_view_error(msg, node)
                try:
                    field = Model._fields[name]
                except KeyError:
                    msg = _(
                        'Unknown field "%(model)s.%(field)s" in %(use)s)',
                        model=Model._name, field=name, use=use,
                    )
                    self._raise_view_error(msg, node)
                if not field._description_searchable:
                    msg = _(
                        'Unsearchable field %(field)r in path %(field_path)r in %(use)s)',
                        field=name, field_path=field_path, use=use,
                    )
                    self._raise_view_error(msg, node)
                Model = self.pool.get(field.comodel_name)

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
        arch_tree = self.browse(view_id)._get_combined_arch()
        self.distribute_branding(arch_tree)
        return etree.tostring(arch_tree, encoding='unicode')

    @api.model
    def get_view_id(self, template):
        """ Return the view ID corresponding to ``template``, which may be a
        view ID or an XML ID. Note that this method may be overridden for other
        kinds of template values.

        This method could return the ID of something that is not a view (when
        using fallback to `_xmlid_to_res_id`).
        """
        if isinstance(template, int):
            return template
        if '.' not in template:
            raise ValueError('Invalid template id: %r' % template)
        view = self.sudo().search([('key', '=', template)], limit=1)
        return view and view.id or self.env['ir.model.data']._xmlid_to_res_id(template, raise_if_not_found=True)

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

            # Remove the processing instructions indicating where nodes were
            # removed (see apply_inheritance_specs)
            for descendant in e.iterdescendants(tag=etree.ProcessingInstruction):
                if descendant.target == 'apply-inheritance-specs-node-removal':
                    descendant.getparent().remove(descendant)
            return

        node_path = e.get('data-oe-xpath')
        if node_path is None:
            node_path = "%s/%s[%d]" % (parent_xpath, e.tag, index_map[e.tag])
        if branding:
            if e.get('t-field'):
                e.set('data-oe-xpath', node_path)
            elif not e.get('data-oe-model'):
                e.attrib.update(branding)
                e.set('data-oe-xpath', node_path)
        if not e.get('data-oe-model'):
            return

        if {'t-esc', 't-raw', 't-out'}.intersection(e.attrib):
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
                for child in e.iterchildren(etree.Element, etree.ProcessingInstruction):
                    if child.get('data-oe-xpath'):
                        # injected by view inheritance, skip otherwise
                        # generated xpath is incorrect
                        self.distribute_branding(child)
                    elif child.tag is etree.ProcessingInstruction:
                        # If a node is known to have been replaced during
                        # applying an inheritance, increment its index to
                        # compute an accurate xpath for subsequent nodes
                        if child.target == 'apply-inheritance-specs-node-removal':
                            indexes[child.text] += 1
                            e.remove(child)
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
        ) or (
            node.tag is etree.ProcessingInstruction
            and node.target == 'apply-inheritance-specs-node-removal'
        )

    @tools.ormcache('self.id')
    def get_view_xmlid(self):
        domain = [('model', '=', 'ir.ui.view'), ('res_id', '=', self.id)]
        xmlid = self.env['ir.model.data'].sudo().search_read(domain, ['module', 'name'])[0]
        return '%s.%s' % (xmlid['module'], xmlid['name'])

    @api.model
    def render_public_asset(self, template, values=None):
        template = self.sudo().browse(self.get_view_id(template))
        template._check_view_access()
        return template.sudo()._render(values, engine="ir.qweb")

    def _render_template(self, template, values=None, engine='ir.qweb'):
        return self.browse(self.get_view_id(template))._render(values, engine)

    def _render(self, values=None, engine='ir.qweb', minimal_qcontext=False):
        assert isinstance(self.id, int)

        qcontext = dict() if minimal_qcontext else self._prepare_qcontext()
        qcontext.update(values or {})

        return self.env[engine]._render(self.id, qcontext)

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
            quote_plus=werkzeug.urls.url_quote_plus,
            time=safe_eval.time,
            datetime=safe_eval.datetime,
            relativedelta=relativedelta,
            xmlid=self.sudo().key,
            viewid=self.id,
            to_text=pycompat.to_text,
            image_data_uri=image_data_uri,
            # specific 'math' functions to ease rounding in templates and lessen controller marshmalling
            floor=math.floor,
            ceil=math.ceil,
        )
        return qcontext

    #------------------------------------------------------
    # Misc
    #------------------------------------------------------

    def open_translations(self):
        """ Open a view for editing the translations of field 'arch_db'. """
        return self.env['ir.translation'].translate_fields('ir.ui.view', self.id, 'arch_db')

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
            view._check_xml()

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
    """ A wizard to compare and reset views architecture. """
    _name = "reset.view.arch.wizard"
    _description = "Reset View Architecture Wizard"

    view_id = fields.Many2one('ir.ui.view', string='View')
    view_name = fields.Char(related='view_id.name', string='View Name')
    has_diff = fields.Boolean(compute='_compute_arch_diff')
    arch_diff = fields.Html(string='Architecture Diff', readonly=True,
                            compute='_compute_arch_diff', sanitize_tags=False)
    reset_mode = fields.Selection([
        ('soft', 'Restore previous version (soft reset).'),
        ('hard', 'Reset to file version (hard reset).'),
        ('other_view', 'Reset to another view.')],
        string='Reset Mode', default='soft', required=True)
    compare_view_id = fields.Many2one('ir.ui.view', string='Compare To View')
    arch_to_compare = fields.Text('Arch To Compare To', compute='_compute_arch_diff')

    @api.model
    def default_get(self, fields):
        view_ids = (self._context.get('active_model') == 'ir.ui.view' and
                    self._context.get('active_ids') or [])
        if len(view_ids) > 2:
            raise ValidationError(_("Can't compare more than two views."))

        result = super().default_get(fields)
        result['view_id'] = view_ids and view_ids[0]
        if len(view_ids) == 2:
            result['reset_mode'] = 'other_view'
            result['compare_view_id'] = view_ids[1]
        return result

    @api.depends('reset_mode', 'view_id', 'compare_view_id')
    def _compute_arch_diff(self):
        """ Depending of `reset_mode`, return the differences between the
        current view arch and either its previous arch, its initial arch or
        another view arch.
        """
        def get_table_name(view_id):
            name = view_id.display_name
            if view_id.key or view_id.xml_id:
                span = '<span class="ml-1 font-weight-normal small">(%s)</span>'
                name += span % (view_id.key or view_id.xml_id)
            return name

        for view in self:
            diff_to = False
            diff_to_name = False
            if view.reset_mode == 'soft':
                diff_to = view.view_id.arch_prev
                diff_to_name = _("Previous Arch")
            elif view.reset_mode == 'other_view':
                diff_to = view.compare_view_id.with_context(lang=None).arch
                diff_to_name = get_table_name(view.compare_view_id)
            elif view.reset_mode == 'hard' and view.view_id.arch_fs:
                diff_to = view.view_id.with_context(read_arch_from_file=True, lang=None).arch
                diff_to_name = _("File Arch")

            view.arch_to_compare = diff_to

            if not diff_to:
                view.arch_diff = False
                view.has_diff = False
            else:
                view_arch = view.view_id.with_context(lang=None).arch
                view.arch_diff = get_diff(
                    (view_arch, get_table_name(view.view_id) if view.reset_mode == 'other_view' else _("Current Arch")),
                    (diff_to, diff_to_name),
                )
                view.has_diff = view_arch != diff_to

    def reset_view_button(self):
        self.ensure_one()
        if self.reset_mode == 'other_view':
            self.view_id.write({'arch_db': self.arch_to_compare})
        else:
            self.view_id.reset_arch(self.reset_mode)
        return {'type': 'ir.actions.act_window_close'}


class NameManager:
    """ An object that manages all the named elements in a view. """

    def __init__(self, model):
        self.model = model
        self.available_fields = collections.defaultdict(dict)   # {field_name: field_info}
        self.available_actions = set()
        self.available_names = set()
        self.mandatory_fields = dict()          # {field_name: use}
        self.mandatory_parent_fields = dict()   # {field_name: use}
        self.mandatory_names = dict()           # {name: use}

    @lazy_property
    def field_info(self):
        return self.model.fields_get()

    def has_field(self, name, info=frozendict()):
        self.available_fields[name].update(info)
        self.available_names.add(info.get('id') or name)

    def has_action(self, name):
        self.available_actions.add(name)

    def must_have_field(self, name, use):
        if name.startswith('parent.'):
            self.mandatory_parent_fields[name[7:]] = use
        else:
            self.mandatory_fields[name] = use

    def must_have_fields(self, names, use):
        for name in names:
            self.must_have_field(name, use)

    def must_have_name(self, name, use):
        self.mandatory_names[name] = use

    def check(self, view):
        # context for translations below
        context = view.env.context          # pylint: disable=unused-variable

        for name, use in self.mandatory_names.items():
            if name not in self.available_actions and name not in self.available_names:
                msg = _(
                    "Name or id %(name_or_id)r in %(use)s must be present in view but is missing.",
                    name_or_id=name, use=use,
                )
                view._raise_view_error(msg)

        for name in self.available_fields:
            if name not in self.model._fields and name not in self.field_info:
                message = _("Field `%(name)s` does not exist", name=name)
                view._raise_view_error(message)

        for name, use in self.mandatory_fields.items():
            if name == 'id':  # always available
                continue
            if "." in name:
                msg = _(
                    "Invalid composed field %(definition)s in %(use)s",
                    definition=name, use=use,
                )
                view._raise_view_error(msg)
            info = self.available_fields.get(name)
            if info is None:
                msg = _(
                    "Field %(name)r used in %(use)s must be present in view but is missing.",
                    name=name, use=use,
                )
                view._raise_view_error(msg)
            if info.get('select') == 'multi':  # mainly for searchpanel, but can be a generic behaviour.
                msg = _(
                    "Field %(name)r used in %(use)s is present in view but is in select multi.",
                    name=name, use=use,
                )
                view._raise_view_error(msg)

    def update_available_fields(self):
        for name, info in self.available_fields.items():
            info.update(self.field_info.get(name, ()))
