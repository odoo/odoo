# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import collections
import datetime
import functools
import inspect
import json
import logging
import math
import pprint
import re
import time
import uuid
import warnings

from lxml import etree
from lxml.etree import LxmlError
from lxml.builder import E

import odoo
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, AccessError, UserError
from odoo.http import request
from odoo.modules.module import get_resource_from_path, get_resource_path
from odoo.tools import config, ConstantMapping, get_diff, pycompat, apply_inheritance_specs, locate_node, str2bool
from odoo.tools.convert import _fix_multiple_roots
from odoo.tools import safe_eval, lazy, lazy_property, frozendict
from odoo.tools.view_validation import valid_view, get_variable_names, get_domain_identifiers, get_dict_asts
from odoo.tools.translate import xml_translate, TRANSLATED_ATTRS
from odoo.models import check_method_name
from odoo.osv.expression import expression

_logger = logging.getLogger(__name__)

MOVABLE_BRANDING = ['data-oe-model', 'data-oe-id', 'data-oe-field', 'data-oe-xpath', 'data-oe-source-id']

ref_re = re.compile(r"""
# first match 'form_view_ref' key, backrefs are used to handle single or
# double quoting of the value
(['"])(?P<view_type>\w+_view_ref)\1
# colon separator (with optional spaces around)
\s*:\s*
# open quote for value
(['"])
(?P<view_id>
    # we'll just match stuff which is normally part of an xid:
    # word and "." characters
    [.\w]+
)
# close with same quote as opening
\3
""", re.VERBOSE)


def att_names(name):
    yield name
    yield f"t-att-{name}"
    yield f"t-attf-{name}"


def transfer_field_to_modifiers(field, modifiers, attributes):
    default_values = {}
    state_exceptions = {}
    for attr in attributes:
        state_exceptions[attr] = []
        default_values[attr] = bool(field.get(attr))
    for state, modifs in field.get("states", {}).items():
        for modif in modifs:
            if modif[0] in attributes and default_values[modif[0]] != modif[1]:
                state_exceptions[modif[0]].append(state)

    for attr, default_value in default_values.items():
        if state_exceptions[attr]:
            modifiers[attr] = [("state", "not in" if default_value else "in", state_exceptions[attr])]
        else:
            modifiers[attr] = default_value


def transfer_node_to_modifiers(node, modifiers):
    # Don't deal with groups, it is done by check_group().
    attrs = node.attrib.pop('attrs', None)
    if attrs:
        modifiers.update(ast.literal_eval(attrs.strip()))
        for a in ('invisible', 'readonly', 'required'):
            if a in modifiers and isinstance(modifiers[a], int):
                modifiers[a] = bool(modifiers[a])

    states = node.attrib.pop('states', None)
    if states:
        states = states.split(',')
        if 'invisible' in modifiers and isinstance(modifiers['invisible'], list):
            # TODO combine with AND or OR, use implicit AND for now.
            modifiers['invisible'].append(('state', 'not in', states))
        else:
            modifiers['invisible'] = [('state', 'not in', states)]

    context_dependent_modifiers = {}
    for attr in ('invisible', 'readonly', 'required'):
        value_str = node.attrib.pop(attr, None)
        if value_str:

            if (attr == 'invisible'
                    and any(parent.tag == 'tree' for parent in node.iterancestors())
                    and not any(parent.tag == 'header' for parent in node.iterancestors())):
                # Invisible in a tree view has a specific meaning, make it a
                # new key in the modifiers attribute.
                attr = 'column_invisible'

            # TODO: for invisible="context.get('...')", delegate to the web client.
            try:
                # most (~95%) elements are 1/True/0/False
                value = str2bool(value_str)
            except ValueError:
                # if str2bool fails, it means it's something else than 1/True/0/False,
                # meaning most-likely `context.get('...')`,
                # which should be evaluated after retrieving the view arch from the cache
                context_dependent_modifiers[attr] = value_str
                continue

            if value or (attr not in modifiers or not isinstance(modifiers[attr], list)):
                # Don't set the attribute to False if a dynamic value was
                # provided (i.e. a domain from attrs or states).
                modifiers[attr] = value

    if context_dependent_modifiers:
        node.set('context-dependent-modifiers', json.dumps(context_dependent_modifiers))


def simplify_modifiers(modifiers):
    for a in ('column_invisible', 'invisible', 'readonly', 'required'):
        if a in modifiers and not modifiers[a]:
            del modifiers[a]


def transfer_modifiers_to_node(modifiers, node):
    if modifiers:
        simplify_modifiers(modifiers)
        if modifiers:
            node.set('modifiers', json.dumps(modifiers))


@lazy
def keep_query():
    mod = odoo.addons.base.models.ir_qweb
    warnings.warn(f"keep_query has been moved to {mod}", DeprecationWarning)
    return mod.keep_query


class ViewCustom(models.Model):
    _name = 'ir.ui.view.custom'
    _description = 'Custom View'
    _order = 'create_date desc'  # search(limit=1) should return the last customization
    _rec_name = 'user_id'

    ref_id = fields.Many2one('ir.ui.view', string='Original View', index=True, required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', index=True, required=True, ondelete='cascade')
    arch = fields.Text(string='View Architecture', required=True)

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
    key = fields.Char(index='btree_not_null')
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

    # The "active" field is not updated during updates if <template> is used
    # instead of <record> to define the view in XML, see _tag_template. For
    # qweb views, you should not rely on the active field being updated anyway
    # as those views, if used in frontend layouts, can be duplicated (see COW)
    # and will thus always require upgrade scripts if you really want to change
    # the default value of their "active" field.
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

        lang = self.env.lang or 'en_US'
        env_en = self.with_context(edit_translations=None, lang='en_US').env
        env_lang = self.with_context(lang=lang).env
        field_arch_db = self._fields['arch_db']
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
                        translation_dictionary = field_arch_db.get_translation_dictionary(
                            view.with_env(env_en).arch_db, {lang: view.with_env(env_lang).arch_db}
                        )
                        arch_fs = field_arch_db.translate(
                            lambda term: translation_dictionary[term][lang],
                            arch_fs
                        )
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
            # the xml_translate will clean the arch_db when write (e.g. ('<div>') -> ('<div></div>'))
            # view.arch should be reassigned here
            view.arch = view.arch_db
        # the field 'arch' depends on the context and has been implicitly
        # modified in all languages; the invalidation below ensures that the
        # field does not keep an old value in another environment
        self.invalidate_recordset(['arch'])

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
            if (view.groups_id and
                view.inherit_id and
                view.mode != 'primary'):
                raise ValidationError(_("Inherited view cannot have 'Groups' define on the record. Use 'groups' attributes inside the view definition"))

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
            if 'arch_db' in values and not values['arch_db']:
                # delete empty arch_db to avoid triggering _check_xml before _inverse_arch_base is called
                del values['arch_db']

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

    def _update_field_translations(self, fname, translations, digest=None):
        res = super()._update_field_translations(fname, translations, digest)
        if fname == 'arch_db' and 'install_filename' not in self._context:
            self.write({'arch_updated': True})
        return res

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
                v.id, v.inherit_id, v.mode
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

    def _get_view_refs(self, node):
        """ Extract the `[view_type]_view_ref` keys and values from the node context attribute,
        giving the views to use for a field node.

        :param node: the field node as an etree
        :return: a dictonary mapping the `[view_type]_view_ref` key to the xmlid of the view to use for that view type.
        """
        if not node.get('context'):
            return {}
        return {
            m.group('view_type'): m.group('view_id')
            for m in ref_re.finditer(node.get('context'))
        }

    #------------------------------------------------------
    # Postprocessing: translation, groups and modifiers
    #------------------------------------------------------
    # TODO: remove group processing from ir_qweb
    #------------------------------------------------------
    def postprocess_and_fields(self, node, model=None, **options):
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

        name_manager = self._postprocess_view(node, model or self.model, **options)

        arch = etree.tostring(node, encoding="unicode").replace('\t', '')

        models = {}
        name_managers = [name_manager]
        for name_manager in name_managers:
            models.setdefault(name_manager.model._name, set()).update(name_manager.available_fields)
            name_managers.extend(name_manager.children)
        return arch, models

    def _postprocess_access_rights(self, tree):
        """
        Apply group restrictions: elements with a 'groups' attribute should
        be removed from the view to people who are not members.

        Compute and set on node access rights based on view type. Specific
        views can add additional specific rights like creating columns for
        many2one-based grouping views.
        """

        for node in tree.xpath('//*[@groups]'):
            attrib_groups = node.attrib.pop('groups')
            if attrib_groups and not self.user_has_groups(attrib_groups):
                node.getparent().remove(node)
            elif node.tag == 't' and (not node.attrib or node.get('postprocess_added')):
                # Move content of <t groups=""> blocks
                # and remove the <t> node.
                # This is to keep the structure
                # <group>
                #   <field name="foo"/>
                #   <field name="bar"/>
                # <group>
                # so the web client adds the label as expected.
                # This is also to avoid having <t> nodes in tree views
                # e.g.
                # <tree>
                #   <field name="foo"/>
                #   <t groups="foo">
                #     <field name="bar" groups="bar"/>
                #   </t>
                # </tree>
                for child in reversed(node):
                    node.addnext(child)
                node.getparent().remove(node)

        base_model = tree.get('model_access_rights')
        for node in tree.xpath('//*[@model_access_rights]'):
            model = self.env[node.attrib.pop('model_access_rights')]
            if node.tag == 'field':
                can_create = model.check_access_rights('create', raise_exception=False)
                can_write = model.check_access_rights('write', raise_exception=False)
                node.set('can_create', 'true' if can_create else 'false')
                node.set('can_write', 'true' if can_write else 'false')
            else:
                is_base_model = base_model == model._name
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

        return tree

    def _postprocess_context_dependent(self, tree):
        """
        Evaluate the modifiers which depends on the context after retrieving the view from the cache.

        e.g.
        <field name="date_approve" invisible="context.get('quotation_only', False)"

        For such modifiers, which cannot be cached, the modifier has been stored under it's non-evaluated expression,
        along with a temporary technical attribute `context-dependent-modifiers`
        to tell which modifier should be evaluated after retrieving the view from the cache.
        e.g.
        <field
            name="date_approve"
            modifiers="{&quot;invisible&quot;: &quot;context.get('quotation_only')&quot;}"
            context-dependent-modifiers="invisible"/>
        """
        for node in tree.xpath('//*[@context-dependent-modifiers]'):
            modifiers = json.loads(node.attrib.pop('modifiers', '{}'))
            for attr, value in json.loads(node.attrib.pop('context-dependent-modifiers')).items():
                value = bool(safe_eval.safe_eval(value, {'context': self._context}))
                if value or (attr not in modifiers or not isinstance(modifiers[attr], list)):
                    modifiers[attr] = value
            transfer_modifiers_to_node(modifiers, node)
        return tree

    def _postprocess_view(self, node, model_name, editable=True, parent_name_manager=None, **options):
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

        if self._onchange_able_view(root):
            self._postprocess_on_change(root, model)

        name_manager = NameManager(model, parent=parent_name_manager)

        root_info = {
            'view_type': root.tag,
            'view_editable': editable and self._editable_node(root, name_manager),
            'view_modifiers_from_model': self._modifiers_from_model(root),
            'mobile': options.get('mobile'),
        }

        # use a stack to recursively traverse the tree
        stack = [(root, editable)]
        while stack:
            node, editable = stack.pop()

            # compute default
            tag = node.tag
            had_parent = node.getparent() is not None
            node_info = dict(root_info, modifiers={}, editable=editable and self._editable_node(node, name_manager))

            # tag-specific postprocessing
            postprocessor = getattr(self, f"_postprocess_tag_{tag}", None)
            if postprocessor is not None:
                postprocessor(node, name_manager, node_info)
                if had_parent and node.getparent() is None:
                    # the node has been removed, stop processing here
                    continue

            transfer_node_to_modifiers(node, node_info['modifiers'])
            transfer_modifiers_to_node(node_info['modifiers'], node)

            # if present, iterate on node_info['children'] instead of node
            for child in reversed(node_info.get('children', node)):
                stack.append((child, node_info['editable']))

        name_manager.update_available_fields()
        root.set('model_access_rights', model._name)

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

    def _get_x2many_missing_view_archs(self, field, field_node, node_info):
        """
        For x2many fields that require to have some multi-record arch (kanban or list) to display the records
        be available, this function fetches all arch that are needed and return them.
        The caller function is responsible to do what it needs with them.
        """
        current_view_types = [el.tag for el in field_node.xpath("./*[descendant::field]")]
        missing_view_types = []
        if not any(view_type in current_view_types for view_type in field_node.get('mode', 'kanban,tree').split(',')):
            missing_view_types.append(
                field_node.get('mode', 'kanban' if node_info.get('mobile') else 'tree').split(',')[0]
            )

        if not missing_view_types:
            return []

        comodel = self.env[field.comodel_name].sudo(False)
        refs = self._get_view_refs(field_node)
        # Do not propagate <view_type>_view_ref of parent call to `_get_view`
        comodel = comodel.with_context(**{
            f'{view_type}_view_ref': refs.get(f'{view_type}_view_ref')
            for view_type in missing_view_types
        })

        return [comodel._get_view(view_type=view_type) for view_type in missing_view_types]

    #------------------------------------------------------
    # Specific node postprocessors
    #------------------------------------------------------
    def _postprocess_tag_calendar(self, node, name_manager, node_info):
        for additional_field in ('date_start', 'date_delay', 'date_stop', 'color', 'all_day'):
            if node.get(additional_field):
                name_manager.has_field(node, node.get(additional_field).split('.', 1)[0])
        for f in node:
            if f.tag == 'filter':
                name_manager.has_field(node, f.get('name'))

    def _postprocess_tag_field(self, node, name_manager, node_info):
        if node.get('name'):
            attrs = {'id': node.get('id'), 'select': node.get('select')}
            field = name_manager.model._fields.get(node.get('name'))
            if field:
                if field.groups:
                    if node.get('groups'):
                        # if the node has a group (e.g. "base.group_no_one")
                        # and the field in the Python model has a group as well (e.g. "base.group_system")
                        # the user must have both group to see the field.
                        # groups="base.group_no_one,base.group_system" directly on the node
                        # would be one of the two groups, not both (OR instead of AND).
                        # To make mandatory to have both groups, wrap the field node in a <t> node with the group
                        # set on the field in the Python model
                        # e.g. <t groups="base.group_system"><field name="foo" groups="base.group_no_one"/></t>
                        # The <t> node will be removed later, in _postprocess_access_rights.
                        node_t = E.t(groups=field.groups, postprocess_added='1')
                        node.getparent().replace(node, node_t)
                        node_t.append(node)
                    else:
                        node.set('groups', field.groups)
                if (
                    node_info.get('view_type') == 'form'
                    and field.type in ('one2many', 'many2many')
                    and not node.get('widget')
                    and not node.get('invisible')
                    and not name_manager.parent
                ):
                    # Embed kanban/tree/form views for visible x2many fields in form views
                    # if no widget or the widget requires it.
                    # So the web client doesn't have to call `get_views` for x2many fields not embedding their view
                    # in the main form view.
                    for arch, _view in self._get_x2many_missing_view_archs(field, node, node_info):
                        node.append(arch)

                for child in node:
                    if child.tag in ('form', 'tree', 'graph', 'kanban', 'calendar'):
                        node_info['children'] = []
                        self._postprocess_view(
                            child, field.comodel_name, editable=node_info['editable'], parent_name_manager=name_manager,
                        )
                if node_info['editable'] and field.type in ('many2one', 'many2many'):
                    node.set('model_access_rights', field.comodel_name)

            name_manager.has_field(node, node.get('name'), attrs)

            field_info = name_manager.field_info.get(node.get('name'))
            if field_info:
                transfer_field_to_modifiers(field_info, node_info['modifiers'], node_info['view_modifiers_from_model'])

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
        # post-process the node as a nested view, and associate it to the field
        self._postprocess_view(node, field.comodel_name, editable=False, parent_name_manager=name_manager)
        name_manager.has_field(node, name)

    def _postprocess_tag_label(self, node, name_manager, node_info):
        if node.get('for'):
            field = name_manager.model._fields.get(node.get('for'))
            if field and field.groups:
                if node.get('groups'):
                    # See the comment for this in `_postprocess_tag_field`
                    node_t = E.t(groups=field.groups, postprocess_added="1")
                    node.getparent().replace(node, node_t)
                    node_t.append(node)
                else:
                    node.set('groups', field.groups)

    def _postprocess_tag_search(self, node, name_manager, node_info):
        searchpanel = [child for child in node if child.tag == 'searchpanel']
        if searchpanel:
            self._postprocess_view(
                searchpanel[0], name_manager.model._name, editable=False, parent_name_manager=name_manager
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
        return node.get('editable') or node.get('multi_edit')

    def _editable_tag_field(self, node, name_manager):
        field = name_manager.model._fields.get(node.get('name'))
        return field is None or field.is_editable() and (
            node.get('readonly') not in ('1', 'True')
            or get_dict_asts(node.get('attrs') or "{}")
        )

    def _onchange_able_view(self, node):
        func = getattr(self, f"_onchange_able_view_{node.tag}", None)
        if func is not None:
            return func(node)

    def _onchange_able_view_form(self, node):
        return True

    def _onchange_able_view_tree(self, node):
        return True

    def _onchange_able_view_kanban(self, node):
        return True

    def _modifiers_from_model(self, node):
        modifier_names = ['invisible']
        if node.tag in ('kanban', 'tree', 'form'):
            modifier_names += ['readonly', 'required']
        return modifier_names

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
                name_manager.has_field(node, node.get(additional_field).split('.', 1)[0])
        for f in node:
            if f.tag == 'filter':
                name_manager.has_field(node, f.get('name'))

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
                        name_manager.must_have_fields(node, vnames, f"{desc} ({domain})")

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
                for fname, groups_uses in sub_manager.mandatory_parent_fields.items():
                    for groups, use in groups_uses.items():
                        name_manager.must_have_field(node, fname, use, groups=groups)

        elif validate and name not in name_manager.field_info:
            msg = _(
                'Field "%(field_name)s" does not exist in model "%(model_name)s"',
                field_name=name, model_name=name_manager.model._name,
            )
            self._raise_view_error(msg, node)

        name_manager.has_field(node, name, {'id': node.get('id'), 'select': node.get('select')})

        if validate:
            for attribute in ('invisible', 'readonly', 'required'):
                val = node.get(attribute)
                if val:
                    try:
                        # most (~95%) elements are 1/True/0/False
                        res = str2bool(val)
                    except ValueError:
                        res = safe_eval.safe_eval(val, {'context': self._context})
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
                name_manager.must_have_fields(node, vnames, f"{desc} ({domain})")

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

        if node.get('icon'):
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
                        name_manager.must_have_fields(node, vnames, f"{desc} ({domain})")

            # move all children nodes into a new node <groupby>
            groupby_node = E.groupby(*node)
            # validate the node as a nested view
            sub_manager = self._validate_view(
                groupby_node, field.comodel_name, editable=False, full=node_info['validate'],
            )
            name_manager.has_field(node, name)
            for fname, groups_uses in sub_manager.mandatory_parent_fields.items():
                for groups, use in groups_uses.items():
                    name_manager.must_have_field(node, fname, use, groups=groups)

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
                        name_manager.must_have_fields(node, fnames | vnames, f"attrs ({expr})")
                    else:
                        vnames = get_variable_names(val_ast)
                        if vnames:
                            name_manager.must_have_fields(node, vnames, f"attrs ({expr})")

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
                            name_manager.must_have_fields(node, vnames, f"context ({expr})")

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
                    name_manager.must_have_fields(node, vnames, f"{attr}={expr}")

            elif attr == 'data-bs-toggle' and expr == 'tab':
                if node.get('role') != 'tab':
                    msg = 'tab link (data-bs-toggle="tab") must have "tab" role'
                    self._log_view_warning(msg, node)
                aria_control = node.get('aria-controls') or node.get('t-att-aria-controls')
                if not aria_control and not node.get('t-attf-aria-controls'):
                    msg = 'tab link (data-bs-toggle="tab") must have "aria_control" defined'
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
        valid_t_attrs = {'t-value', 't-raw', 't-field', 't-esc', 't-out'}

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

        def has_title_or_aria_label(node):
            return any(node.get(attr) for attr in valid_aria_attrs)

        ## Aria label can be on ancestors
        if any(map(has_title_or_aria_label, node.iterancestors())):
            return

        if node.get('string'):
            return

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
            if node.text:  # not sure, does it match *[text()]
                return True
            return any(contains_description(child, depth+1) for child in node)

        if contains_description(node):
            return

        msg = '%s must have title in its tag, parents, descendants or have text'
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
        return ['lang', 'inherit_branding', 'edit_translations']

    # apply ormcache_context decorator unless in dev mode...
    @api.model
    def _read_template(self, view_id):
        arch_tree = self.browse(view_id)._get_combined_arch()
        self.distribute_branding(arch_tree)
        return etree.tostring(arch_tree, encoding='unicode')

    @api.model
    def _get_view_id(self, template):
        """ Return the view ID corresponding to ``template``, which may be a
        view ID or an XML ID. Note that this method may be overridden for other
        kinds of template values.
        """
        if isinstance(template, int):
            return template
        if '.' not in template:
            raise ValueError('Invalid template id: %r' % template)
        view = self.sudo().search([('key', '=', template)], limit=1)
        if view:
            return view.id
        res_model, res_id = self.env['ir.model.data']._xmlid_to_res_model_res_id(template, raise_if_not_found=True)
        assert res_model == self._name, "Call _get_view_id, expected %r, got %r" % (self._name, res_model)
        return res_id

    @api.model
    def _get(self, view_ref):
        """ Return the view corresponding to ``view_ref``, which may be a
        view ID or an XML ID.
        """
        return self.browse(self._get_view_id(view_ref))

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

    @api.model
    def render_public_asset(self, template, values=None):
        template_sudo = self._get(template).sudo()
        template_sudo._check_view_access()
        return self.env['ir.qweb'].sudo()._render(template, values)

    def _render_template(self, template, values=None):
        return self.env['ir.qweb']._render(template, values)

    #------------------------------------------------------
    # Misc
    #------------------------------------------------------

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


class Model(models.AbstractModel):
    _inherit = 'base'

    _date_name = 'date'         #: field to use for default calendar view

    def _get_access_action(self, access_uid=None, force_website=False):
        """ Return an action to open the document. This method is meant to be
        overridden in addons that want to give specific access to the document.
        By default, it opens the formview of the document.

        :param integer access_uid: optional access_uid being the user that
            accesses the document. May be different from the current user as we
            may compute an access for someone else.
        :param integer force_website: force frontend redirection if available
            on self. Used in overrides, notably with portal / website addons.
        """
        self.ensure_one()
        return self.get_formview_action(access_uid=access_uid)

    @api.model
    def get_empty_list_help(self, help_message):
        """ Hook method to customize the help message in empty list/kanban views.

        By default, it returns the help received as parameter.

        :param str help: ir.actions.act_window help content
        :return: help message displayed when there is no result to display
          in a list/kanban view (by default, it returns the action help)
        :rtype: str
        """
        return help_message

    #
    # Override this method if you need a window title that depends on the context
    #
    @api.model
    def view_header_get(self, view_id=None, view_type='form'):
        return False

    @api.model
    def _get_default_form_view(self):
        """ Generates a default single-line form view using all fields
        of the current model.

        :returns: a form view as an lxml document
        :rtype: etree._Element
        """
        group = E.group(col="4")
        for fname, field in self._fields.items():
            if field.automatic:
                continue
            elif field.type in ('one2many', 'many2many', 'text', 'html'):
                group.append(E.newline())
                group.append(E.field(name=fname, colspan="4"))
                group.append(E.newline())
            else:
                group.append(E.field(name=fname))
        group.append(E.separator())
        return E.form(E.sheet(group, string=self._description))

    @api.model
    def _get_default_search_view(self):
        """ Generates a single-field search view, based on _rec_name.

        :returns: a tree view as an lxml document
        :rtype: etree._Element
        """
        element = E.field(name=self._rec_name_fallback())
        return E.search(element, string=self._description)

    @api.model
    def _get_default_tree_view(self):
        """ Generates a single-field tree view, based on _rec_name.

        :returns: a tree view as an lxml document
        :rtype: etree._Element
        """
        element = E.field(name=self._rec_name_fallback())
        return E.tree(element, string=self._description)

    @api.model
    def _get_default_pivot_view(self):
        """ Generates an empty pivot view.

        :returns: a pivot view as an lxml document
        :rtype: etree._Element
        """
        return E.pivot(string=self._description)

    @api.model
    def _get_default_kanban_view(self):
        """ Generates a single-field kanban view, based on _rec_name.

        :returns: a kanban view as an lxml document
        :rtype: etree._Element
        """

        field = E.field(name=self._rec_name_fallback())
        content_div = E.div(field, {'class': "o_kanban_card_content"})
        card_div = E.div(content_div, {'t-attf-class': "oe_kanban_card oe_kanban_global_click"})
        kanban_box = E.t(card_div, {'t-name': "kanban-box"})
        templates = E.templates(kanban_box)
        return E.kanban(templates, string=self._description)

    @api.model
    def _get_default_graph_view(self):
        """ Generates a single-field graph view, based on _rec_name.

        :returns: a graph view as an lxml document
        :rtype: etree._Element
        """
        element = E.field(name=self._rec_name_fallback())
        return E.graph(element, string=self._description)

    @api.model
    def _get_default_calendar_view(self):
        """ Generates a default calendar view by trying to infer
        calendar fields from a number of pre-set attribute names

        :returns: a calendar view
        :rtype: etree._Element
        """
        def set_first_of(seq, in_, to):
            """Sets the first value of ``seq`` also found in ``in_`` to
            the ``to`` attribute of the ``view`` being closed over.

            Returns whether it's found a suitable value (and set it on
            the attribute) or not
            """
            for item in seq:
                if item in in_:
                    view.set(to, item)
                    return True
            return False

        view = E.calendar(string=self._description)
        view.append(E.field(name=self._rec_name_fallback()))

        if not set_first_of([self._date_name, 'date', 'date_start', 'x_date', 'x_date_start'],
                            self._fields, 'date_start'):
            raise UserError(_("Insufficient fields for Calendar View!"))

        set_first_of(["user_id", "partner_id", "x_user_id", "x_partner_id"],
                     self._fields, 'color')

        if not set_first_of(["date_stop", "date_end", "x_date_stop", "x_date_end"],
                            self._fields, 'date_stop'):
            if not set_first_of(["date_delay", "planned_hours", "x_date_delay", "x_planned_hours"],
                                self._fields, 'date_delay'):
                raise UserError(_(
                    "Insufficient fields to generate a Calendar View for %s, missing a date_stop or a date_delay",
                    self._name
                ))

        return view

    @api.model
    def get_views(self, views, options=None):
        """ Returns the fields_views of given views, along with the fields of
        the current model, and optionally its filters for the given action.

        :param views: list of [view_id, view_type]
        :param dict options: a dict optional boolean flags, set to enable:

            ``toolbar``
                includes contextual actions when loading fields_views
            ``load_filters``
                returns the model's filters
            ``action_id``
                id of the action to get the filters, otherwise loads the global
                filters or the model

        :return: dictionary with fields_views, fields and optionally filters
        """
        options = options or {}
        result = {}

        result['views'] = {
            v_type: self.get_view(
                v_id, v_type if v_type != 'list' else 'tree',
                **options
            )
            for [v_id, v_type] in views
        }

        models = {}
        for view in result['views'].values():
            for model, model_fields in view.pop('models').items():
                models.setdefault(model, set()).update(model_fields)

        result['models'] = {}

        for model, model_fields in models.items():
            result['models'][model] = self.env[model].fields_get(
                allfields=model_fields, attributes=self._get_view_field_attributes()
            )

        # Add related action information if asked
        if options.get('toolbar'):
            for view in result['views'].values():
                view['toolbar'] = {}

            bindings = self.env['ir.actions.actions'].get_bindings(self._name)
            for action_type, key in (('report', 'print'), ('action', 'action')):
                for action in bindings.get(action_type, []):
                    view_types = (
                        action['binding_view_types'].split(',')
                        if action.get('binding_view_types')
                        else result['views'].keys()
                    )
                    for view_type in view_types:
                        view_type = view_type if view_type != 'tree' else 'list'
                        if view_type in result['views']:
                            result['views'][view_type]['toolbar'].setdefault(key, []).append(action)

        if options.get('load_filters') and 'search' in result['views']:
            result['views']['search']['filters'] = self.env['ir.filters'].get_filters(
                self._name, options.get('action_id')
            )

        return result

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        """_get_view([view_id | view_type='form'])

        Get the model view combined architecture (the view along all its inheriting views).

        :param int view_id: id of the view or None
        :param str view_type: type of the view to return if view_id is None ('form', 'tree', ...)
        :param dict options: bool options to return additional features:
            - bool mobile: true if the web client is currently using the responsive mobile view
              (to use kanban views instead of list views for x2many fields)
        :return: architecture of the view as an etree node, and the browse record of the view used
        :rtype: tuple
        :raise AttributeError:

            * if no view exists for that model, and no method `_get_default_[view_type]_view` exists for the view type

        """
        View = self.env['ir.ui.view'].sudo()

        # try to find a view_id if none provided
        if not view_id:
            # <view_type>_view_ref in context can be used to override the default view
            view_ref_key = view_type + '_view_ref'
            view_ref = self._context.get(view_ref_key)
            if view_ref:
                if '.' in view_ref:
                    module, view_ref = view_ref.split('.', 1)
                    query = "SELECT res_id FROM ir_model_data WHERE model='ir.ui.view' AND module=%s AND name=%s"
                    self._cr.execute(query, (module, view_ref))
                    view_ref_res = self._cr.fetchone()
                    if view_ref_res:
                        view_id = view_ref_res[0]
                else:
                    _logger.warning(
                        '%r requires a fully-qualified external id (got: %r for model %s). '
                        'Please use the complete `module.view_id` form instead.', view_ref_key, view_ref,
                        self._name
                    )

            if not view_id:
                # otherwise try to find the lowest priority matching ir.ui.view
                view_id = View.default_view(self._name, view_type)

        if view_id:
            # read the view with inherited views applied
            view = View.browse(view_id)
            arch = view._get_combined_arch()
        else:
            # fallback on default views methods if no ir.ui.view could be found
            view = View.browse()
            try:
                arch = getattr(self, '_get_default_%s_view' % view_type)()
            except AttributeError:
                raise UserError(_("No default view of type '%s' could be found !", view_type))
        return arch, view

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """ Get the key to use for caching `_get_view_cache`.

        This method is meant to be overriden by models needing additional keys.

        :param int view_id: id of the view or None
        :param str view_type: type of the view to return if view_id is None ('form', 'tree', ...)
        :param dict options: bool options to return additional features:
            - bool mobile: true if the web client is currently using the responsive mobile view
              (to use kanban views instead of list views for x2many fields)
        :return: a cache key
        :rtype: tuple
        """
        return (view_id, view_type, options.get('mobile'), self.env.lang) + tuple(
            (key, value) for key, value in self.env.context.items() if key.endswith('_view_ref')
        )

    @api.model
    @tools.conditional(
        'xml' not in config['dev_mode'],
        tools.ormcache('self._get_view_cache_key(view_id, view_type, **options)'),
    )
    def _get_view_cache(self, view_id=None, view_type='form', **options):
        """ Get the view information ready to be cached

        The cached view includes the postprocessed view, including inherited views, for all groups.
        The blocks restricted to groups must therefore be removed after calling this method
        for users not part of the given groups.

        :param int view_id: id of the view or None
        :param str view_type: type of the view to return if view_id is None ('form', 'tree', ...)
        :param dict options: boolean options to return additional features:
            - bool mobile: true if the web client is currently using the responsive mobile view
              (to use kanban views instead of list views for x2many fields)
        :return: a dictionnary including
            - string arch: the architecture of the view (including inherited views, postprocessed, for all groups)
            - int id: the view id
            - string model: the view model
            - dict models: the fields of the models used in the view (including sub-views)
        :rtype: dict
        """
        # Get the view arch and all other attributes describing the composition of the view
        arch, view = self._get_view(view_id, view_type, **options)

        # Apply post processing, groups and modifiers etc...
        arch, models = view.postprocess_and_fields(arch, model=self._name, **options)
        models = self._get_view_fields(view_type or view.type, models)
        result = {
            'arch': arch,
            # TODO: only `web_studio` seems to require this. I guess this is acceptable to keep it.
            'id': view.id,
            # TODO: only `web_studio` seems to require this. But this one on the other hand should be eliminated:
            # you just called `get_views` for that model, so obviously the web client already knows the model.
            'model': self._name,
            # Set a frozendict and tuple for the field list to make sure the value in cache cannot be updated.
            'models': frozendict({model: tuple(fields) for model, fields in models.items()}),
        }

        return frozendict(result)

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        """ get_view([view_id | view_type='form'])

        Get the detailed composition of the requested view like model, view architecture

        :param int view_id: id of the view or None
        :param str view_type: type of the view to return if view_id is None ('form', 'tree', ...)
        :param dict options: boolean options to return additional features:
            - bool mobile: true if the web client is currently using the responsive mobile view
            (to use kanban views instead of list views for x2many fields)
        :return: composition of the requested view (including inherited views and extensions)
        :rtype: dict
        :raise AttributeError:

            * if the inherited view has unknown position to work with other than 'before', 'after', 'inside', 'replace'
            * if some tag other than 'position' is found in parent view

        :raise Invalid ArchitectureError: if there is view type other than form, tree, calendar, search etc... defined on the structure
        """
        self.check_access_rights('read')

        result = dict(self._get_view_cache(view_id, view_type, **options))

        node = etree.fromstring(result['arch'])
        node = self.env['ir.ui.view']._postprocess_access_rights(node)
        node = self.env['ir.ui.view']._postprocess_context_dependent(node)
        result['arch'] = etree.tostring(node, encoding="unicode").replace('\t', '')

        return result

    @api.model
    def _get_view_fields(self, view_type, models):
        """ Returns the field names required by the web client to load the views according to the view type.

        The method is meant to be overridden by modules extending web client features and requiring additional
        fields.

        :param string view_type: type of the view
        :param dict models: dict holding the models and fields used in the view architecture.
        :return: dict holding the models and field required by the web client given the view type.
        :rtype: list
        """
        if view_type in ('kanban', 'tree', 'form'):
            for model_fields in models.values():
                model_fields.update({'id', self.CONCURRENCY_CHECK_FIELD})
        elif view_type == 'search':
            models[self._name] = list(self._fields.keys())
        elif view_type == 'graph':
            models[self._name].union(fname for fname, field in self._fields.items() if field.type in ('integer', 'float'))
        elif view_type == 'pivot':
            models[self._name].union(fname for fname, field in self._fields.items() if field.groupable)
        return models

    @api.model
    def _get_view_field_attributes(self):
        """ Returns the field attributes required by the web client to load the views.

        The method is meant to be overridden by modules extending web client features and requiring additional
        field attributes.

        :return: string list of field attribute names
        :rtype: list
        """
        return [
            'change_default', 'context', 'currency_field', 'definition_record', 'digits', 'domain', 'group_operator', 'groups',
            'help', 'name', 'readonly', 'related', 'relation', 'relation_field', 'required', 'searchable', 'selection', 'size',
            'sortable', 'store', 'string', 'translate', 'trim', 'type',
        ]

    @api.model
    def load_views(self, views, options=None):
        warnings.warn(
            '`load_views` method is deprecated, use `get_views` instead',
            DeprecationWarning, stacklevel=2,
        )
        return self.get_views(views, options=options)

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        warnings.warn(
            'Method `_fields_view_get` is deprecated, use `_get_view` instead',
            DeprecationWarning, stacklevel=2,
        )
        arch, view = self._get_view(view_id, view_type, toolbar=toolbar, submenu=submenu)
        result = {
            'arch': etree.tostring(arch, encoding='unicode'),
            'model': self._name,
            'field_parent': False,
        }
        if view:
            result['name'] = view.name
            result['type'] = view.type
            result['view_id'] = view.id
            result['field_parent'] = view.field_parent
            result['base_model'] = view.model
        else:
            result['type'] = view_type
            result['name'] = 'default'
        return result

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
        .. deprecated:: saas-15.4

            Use :meth:`~odoo.models.Model.get_view()` instead.
        """
        warnings.warn(
            'Method `fields_view_get` is deprecated, use `get_view` instead',
            DeprecationWarning, stacklevel=2,
        )
        result = self.get_views([(view_id, view_type)], {'toolbar': toolbar, 'submenu': submenu})['views'][view_type]
        node = etree.fromstring(result['arch'])
        view_fields = set(el.get('name') for el in node.xpath('.//field[not(ancestor::field)]'))
        result['fields'] = self.fields_get(view_fields)
        result.pop('models', None)
        if 'id' in result:
            view = self.env['ir.ui.view'].sudo().browse(result.pop('id'))
            result['name'] = view.name
            result['type'] = view.type
            result['view_id'] = view.id
            result['field_parent'] = view.field_parent
            result['base_model'] = view.model
        else:
            result['type'] = view_type
            result['name'] = 'default'
            result['field_parent'] = False
        return result

    def get_formview_id(self, access_uid=None):
        """ Return a view id to open the document ``self`` with. This method is
            meant to be overridden in addons that want to give specific view ids
            for example.

            Optional access_uid holds the user that would access the form view
            id different from the current environment user.
        """
        return False

    def get_formview_action(self, access_uid=None):
        """ Return an action to open the document ``self``. This method is meant
            to be overridden in addons that want to give specific view ids for
            example.

        An optional access_uid holds the user that will access the document
        that could be different from the current user. """
        view_id = self.sudo().get_formview_id(access_uid=access_uid)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'target': 'current',
            'res_id': self.id,
            'context': dict(self._context),
        }

    @api.model
    def _onchange_spec(self, view_info=None):
        """ Return the onchange spec from a view description; if not given, the
            result of ``self.get_view()`` is used.
        """
        result = {}

        # for traversing the XML arch and populating result
        def process(node, info, prefix):
            if node.tag == 'field':
                name = node.attrib['name']
                names = "%s.%s" % (prefix, name) if prefix else name
                if not result.get(names):
                    result[names] = node.attrib.get('on_change')
                # traverse the subviews included in relational fields
                for child_view in node.xpath("./*[descendant::field]"):
                    process(child_view, None, names)
            else:
                for child in node:
                    process(child, info, prefix)

        if view_info is None:
            view_info = self.get_view()
        process(etree.fromstring(view_info['arch']), view_info, '')
        return result


class NameManager:
    """ An object that manages all the named elements in a view. """

    def __init__(self, model, parent=None):
        self.model = model
        self.available_fields = collections.defaultdict(dict)  # {field_name: {'groups': groups, 'info': field_info}}
        self.available_actions = set()
        self.available_names = set()
        self.mandatory_fields = collections.defaultdict(dict)  # {field_name: {'groups': 'use}}
        self.mandatory_parent_fields = collections.defaultdict(dict)  # {field_name: {'groups': use}}
        self.mandatory_names = dict()           # {name: use}
        self.parent = parent
        self.children = []
        if self.parent:
            self.parent.children.append(self)

    @lazy_property
    def field_info(self):
        field_info = self.model.fields_get(attributes=['invisible', 'states', 'readonly', 'required'])
        has_access = functools.partial(self.model.check_access_rights, raise_exception=False)
        if not (has_access('write') or has_access('create')):
            for info in field_info.values():
                info['readonly'] = True
                info['states'] = {}
        return field_info

    def has_field(self, node, name, info=frozendict()):
        groups = self._get_node_groups(node)
        self.available_fields[name].setdefault('info', {}).update(info)
        self.available_fields[name].setdefault('groups', []).append(groups)
        self.available_names.add(info.get('id') or name)

    def has_action(self, name):
        self.available_actions.add(name)

    def must_have_field(self, node, name, use, groups=None):
        node_groups = self._get_node_groups(node)
        if groups:
            groups = groups + node_groups
        else:
            groups = node_groups
        if name.startswith('parent.'):
            self.mandatory_parent_fields[name[7:]][groups] = use
        else:
            self.mandatory_fields[name][groups] = use

    def must_have_fields(self, node, names, use, groups=None):
        for name in names:
            self.must_have_field(node, name, use, groups=groups)

    def must_have_name(self, name, use):
        self.mandatory_names[name] = use

    def _get_node_groups(self, node):
        return tuple(tuple(n.get('groups').split(',')) for n in node.xpath('ancestor-or-self::*[@groups]'))

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

        for name, groups_uses in self.mandatory_fields.items():
            use = next(iter(groups_uses.values()))
            if name == 'id':  # always available
                continue
            if "." in name:
                msg = _(
                    "Invalid composed field %(definition)s in %(use)s",
                    definition=name, use=use,
                )
                view._raise_view_error(msg)
            info = self.available_fields[name].get('info')
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

            def combinate(groups):
                # [['A'], ['B', 'C'], ['D', 'E']]
                # returns
                # [['A', 'B', 'D'], ['A', 'C', 'D'], ['A', 'B', 'E'], ['A', 'C', 'E']]

                # [['!A', '!B'], ['C', 'D']]
                # returns
                # [['!A', '!B', 'C'], ['!A', '!B', 'D']]

                # [['A', 'B'], ['!C', '!D']]
                # returns
                # [['A', '!C', '!D'], ['B', '!C', '!D']]

                # [['!A', '!B', 'C', 'D'], ['E', 'F']]
                # returns
                # [['!A', '!B', 'C', 'E'], ['!A', '!B', 'D', 'E'], ['!A', '!B', 'C', 'F'], ['!A', '!B', 'D', 'F']]
                if not groups:
                    return []
                positive = [(group,) for group in groups[0] if not group or not group.startswith('!')]
                negative = tuple(group for group in groups[0] if group and group.startswith('!'))
                combinations = [negative + p for p in positive] if positive else [negative]
                if len(groups) > 1:
                    combinations = [group + tuple(c) for c in combinate(groups[1:]) for group in combinations]
                return [set(combination) for combination in set(tuple(combination) for combination in combinations)]

            for mandatory_for_groups, use in groups_uses.items():
                mandatory_combinations = combinate(mandatory_for_groups or [(None,)])
                available_combinations = [
                    combination
                    for available_for_groups in self.available_fields[name]['groups']
                    for combination in combinate(available_for_groups or [(None,)])
                ]
                if (
                    # If (None,) is in available_combinations,
                    # it means the field is in the view without any group restriction,
                    # and is therefore available for anyone / any group
                    {None} not in available_combinations
                    # If there are two mutually exclusive combinations,
                    # it means the field is available for anyone / any group
                    and not any(
                        {group[1:] if group.startswith('!') else '!' + group for group in combination}
                        in available_combinations
                        for combination in available_combinations
                    )
                    # For all mandatory combinations, find an available combination
                    # which is included in the mandatory combination
                    # e.g.
                    # mandatory combination: A B C
                    # available combination: A B
                    # The above is valid, the field will be available for users having both A and B groups
                    # and the field is mandatory only for users having A B and C groups.
                    and not all(
                        any(
                            available_combination.issubset(mandatory_combination)
                            for available_combination in available_combinations
                        ) for mandatory_combination in mandatory_combinations
                    )
                    # Same than above but take into account implied groups (e.g. group_system includes group_erp_manager and group_user)
                    # for positive groups
                    and not all(
                        any(
                            available_combination.issubset(combination)
                            for available_combination in available_combinations
                            for combination in
                            (
                                mandatory_combination - {group} | {trans_group}
                                for group in mandatory_combination if group and not group.startswith('!')
                                for trans_group in view.env.ref(group).trans_implied_ids.get_external_id().values()
                            )
                        )
                        for mandatory_combination in mandatory_combinations
                    )
                    # Same than above but take into account implied groups (e.g. group_system includes group_erp_manager and group_user)
                    # for negative groups
                    and not all(
                        any(
                            combination.issubset(mandatory_combination)
                            for available_combination in available_combinations
                            for combination in
                            (
                                available_combination - {group} | {'!' + trans_group}
                                for group in available_combination if group and group.startswith('!')
                                for trans_group in view.env.ref(group[1:]).trans_implied_ids.get_external_id().values()
                            )
                        ) for mandatory_combination in mandatory_combinations
                    )
                ):
                    msg = _(
                        "Field %(name)r used in %(use)s is restricted to the group(s) %(groups)s.",
                        name=name, use=use, groups=','.join(
                            group
                            for availability in self.available_fields[name]['groups']
                            for combination in availability
                            for group in combination
                        )
                    )
                    view._raise_view_error(msg)

    def update_available_fields(self):
        for name, info in self.available_fields.items():
            info.update(self.field_info.get(name, ()))
