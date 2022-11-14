# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import warnings
from collections import defaultdict, OrderedDict
from decorator import decorator
from operator import attrgetter
from textwrap import dedent
import io
import logging
import os
import shutil
import threading
import zipfile

import requests
import werkzeug.urls

from docutils import nodes
from docutils.core import publish_string
from docutils.transforms import Transform, writer_aux
from docutils.writers.html4css1 import Writer
import lxml.html
import psycopg2

import odoo
from odoo import api, fields, models, modules, tools, _
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo.osv import expression
from odoo.tools.parse_version import parse_version
from odoo.tools.misc import topological_sort, get_flag
from odoo.tools.translate import TranslationImporter, get_po_paths
from odoo.http import request
from odoo.modules import get_module_path

_logger = logging.getLogger(__name__)

ACTION_DICT = {
    'view_mode': 'form',
    'res_model': 'base.module.upgrade',
    'target': 'new',
    'type': 'ir.actions.act_window',
}

def backup(path, raise_exception=True):
    path = os.path.normpath(path)
    if not os.path.exists(path):
        if not raise_exception:
            return None
        raise OSError('path does not exists')
    cnt = 1
    while True:
        bck = '%s~%d' % (path, cnt)
        if not os.path.exists(bck):
            shutil.move(path, bck)
            return bck
        cnt += 1


def assert_log_admin_access(method):
    """Decorator checking that the calling user is an administrator, and logging the call.

    Raises an AccessDenied error if the user does not have administrator privileges, according
    to `user._is_admin()`.
    """
    def check_and_log(method, self, *args, **kwargs):
        user = self.env.user
        origin = request.httprequest.remote_addr if request else 'n/a'
        log_data = (method.__name__, self.sudo().mapped('display_name'), user.login, user.id, origin)
        if not self.env.is_admin():
            _logger.warning('DENY access to module.%s on %s to user %s ID #%s via %s', *log_data)
            raise AccessDenied()
        _logger.info('ALLOW access to module.%s on %s to user %s #%s via %s', *log_data)
        return method(self, *args, **kwargs)
    return decorator(check_and_log, method)

class ModuleCategory(models.Model):
    _name = "ir.module.category"
    _description = "Application"
    _order = 'name'
    _allow_sudo_commands = False

    name = fields.Char(string='Name', required=True, translate=True, index=True)
    parent_id = fields.Many2one('ir.module.category', string='Parent Application', index=True)
    child_ids = fields.One2many('ir.module.category', 'parent_id', string='Child Applications')
    module_ids = fields.One2many('ir.module.module', 'category_id', string='Modules')
    description = fields.Text(string='Description', translate=True)
    sequence = fields.Integer(string='Sequence')
    visible = fields.Boolean(string='Visible', default=True)
    exclusive = fields.Boolean(string='Exclusive')
    xml_id = fields.Char(string='External ID', compute='_compute_xml_id')

    def _compute_xml_id(self):
        xml_ids = defaultdict(list)
        domain = [('model', '=', self._name), ('res_id', 'in', self.ids)]
        for data in self.env['ir.model.data'].sudo().search_read(domain, ['module', 'name', 'res_id']):
            xml_ids[data['res_id']].append("%s.%s" % (data['module'], data['name']))
        for cat in self:
            cat.xml_id = xml_ids.get(cat.id, [''])[0]

    @api.constrains('parent_id')
    def _check_parent_not_circular(self):
        if not self._check_recursion():
            raise ValidationError(_("Error ! You cannot create recursive categories."))


class MyFilterMessages(Transform):
    """
    Custom docutils transform to remove `system message` for a document and
    generate warnings.

    (The standard filter removes them based on some `report_level` passed in
    the `settings_override` dictionary, but if we use it, we can't see them
    and generate warnings.)
    """
    default_priority = 870

    def apply(self):
        for node in self.document.traverse(nodes.system_message):
            _logger.warning("docutils' system message present: %s", str(node))
            node.parent.remove(node)


class MyWriter(Writer):
    """
    Custom docutils html4ccs1 writer that doesn't add the warnings to the
    output document.
    """
    def get_transforms(self):
        return [MyFilterMessages, writer_aux.Admonitions]


STATES = [
    ('uninstallable', 'Uninstallable'),
    ('uninstalled', 'Not Installed'),
    ('installed', 'Installed'),
    ('to upgrade', 'To be upgraded'),
    ('to remove', 'To be removed'),
    ('to install', 'To be installed'),
]


XML_DECLARATION = (
    '<?xml version='.encode('utf-8'),
    '<?xml version='.encode('utf-16-be'),
    '<?xml version='.encode('utf-16-le'),
)


class Module(models.Model):
    _name = "ir.module.module"
    _rec_name = "shortdesc"
    _rec_names_search = ['name', 'shortdesc', 'summary']
    _description = "Module"
    _order = 'application desc,sequence,name'
    _allow_sudo_commands = False

    @classmethod
    def get_module_info(cls, name):
        try:
            return modules.get_manifest(name)
        except Exception:
            _logger.debug('Error when trying to fetch information for module %s', name, exc_info=True)
            return {}

    @api.depends('name', 'description')
    def _get_desc(self):
        for module in self:
            if not module.name:
                module.description_html = False
                continue
            path = os.path.join(module.name, 'static/description/index.html')
            try:
                with tools.file_open(path, 'rb') as desc_file:
                    doc = desc_file.read()
                    if doc.startswith(XML_DECLARATION):
                        warnings.warn(
                            f"XML declarations in HTML module descriptions are "
                            f"deprecated since Odoo 17, {module.name} can just "
                            f"have a UTF8 description with not need for a "
                            f"declaration.",
                            category=DeprecationWarning,
                        )
                    else:
                        try:
                            doc = doc.decode()
                        except UnicodeDecodeError:
                            warnings.warn(
                                f"Non-UTF8 module descriptions are deprecated "
                                f"since Odoo 17 ({module.name}'s description "
                                f"is not utf-8)",
                                category=DeprecationWarning,
                            )
                    html = lxml.html.document_fromstring(doc)
                    for element, attribute, link, pos in html.iterlinks():
                        if element.get('src') and not '//' in element.get('src') and not 'static/' in element.get('src'):
                            element.set('src', "/%s/static/description/%s" % (module.name, element.get('src')))
                    module.description_html = tools.html_sanitize(lxml.html.tostring(html))
            except FileNotFoundError:
                overrides = {
                    'embed_stylesheet': False,
                    'doctitle_xform': False,
                    'output_encoding': 'unicode',
                    'xml_declaration': False,
                    'file_insertion_enabled': False,
                }
                output = publish_string(source=module.description if not module.application and module.description else '', settings_overrides=overrides, writer=MyWriter())
                module.description_html = tools.html_sanitize(output)

    @api.depends('name')
    def _get_latest_version(self):
        default_version = modules.adapt_version('1.0')
        for module in self:
            module.installed_version = self.get_module_info(module.name).get('version', default_version)

    @api.depends('name', 'state')
    def _get_views(self):
        IrModelData = self.env['ir.model.data'].with_context(active_test=True)
        dmodels = ['ir.ui.view', 'ir.actions.report', 'ir.ui.menu']

        for module in self:
            # Skip uninstalled modules below, no data to find anyway.
            if module.state not in ('installed', 'to upgrade', 'to remove'):
                module.views_by_module = ""
                module.reports_by_module = ""
                module.menus_by_module = ""
                continue

            # then, search and group ir.model.data records
            imd_models = defaultdict(list)
            imd_domain = [('module', '=', module.name), ('model', 'in', tuple(dmodels))]
            for data in IrModelData.sudo().search(imd_domain):
                imd_models[data.model].append(data.res_id)

            def browse(model):
                # as this method is called before the module update, some xmlid
                # may be invalid at this stage; explictly filter records before
                # reading them
                return self.env[model].browse(imd_models[model]).exists()

            def format_view(v):
                return '%s%s (%s)' % (v.inherit_id and '* INHERIT ' or '', v.name, v.type)

            module.views_by_module = "\n".join(sorted(format_view(v) for v in browse('ir.ui.view')))
            module.reports_by_module = "\n".join(sorted(r.name for r in browse('ir.actions.report')))
            module.menus_by_module = "\n".join(sorted(m.complete_name for m in browse('ir.ui.menu')))

    @api.depends('icon')
    def _get_icon_image(self):
        self.icon_image = ''
        for module in self:
            if not module.id:
                continue
            if module.icon:
                path = os.path.join(module.icon.lstrip("/"))
            else:
                path = modules.module.get_module_icon_path(module)
            if path:
                try:
                    with tools.file_open(path, 'rb') as image_file:
                        module.icon_image = base64.b64encode(image_file.read())
                except FileNotFoundError:
                    module.icon_image = ''
            countries = self.get_module_info(module.name).get('countries', [])
            country_code = len(countries) == 1 and countries[0]
            module.icon_flag = get_flag(country_code.upper()) if country_code else ''

    name = fields.Char('Technical Name', readonly=True, required=True)
    category_id = fields.Many2one('ir.module.category', string='Category', readonly=True, index=True)
    shortdesc = fields.Char('Module Name', readonly=True, translate=True)
    summary = fields.Char('Summary', readonly=True, translate=True)
    description = fields.Text('Description', readonly=True, translate=True)
    description_html = fields.Html('Description HTML', compute='_get_desc')
    author = fields.Char("Author", readonly=True)
    maintainer = fields.Char('Maintainer', readonly=True)
    contributors = fields.Text('Contributors', readonly=True)
    website = fields.Char("Website", readonly=True)

    # attention: Incorrect field names !!
    #   installed_version refers the latest version (the one on disk)
    #   latest_version refers the installed version (the one in database)
    #   published_version refers the version available on the repository
    installed_version = fields.Char('Latest Version', compute='_get_latest_version')
    latest_version = fields.Char('Installed Version', readonly=True)
    published_version = fields.Char('Published Version', readonly=True)

    url = fields.Char('URL', readonly=True)
    sequence = fields.Integer('Sequence', default=100)
    dependencies_id = fields.One2many('ir.module.module.dependency', 'module_id',
                                       string='Dependencies', readonly=True)
    exclusion_ids = fields.One2many('ir.module.module.exclusion', 'module_id',
                                    string='Exclusions', readonly=True)
    auto_install = fields.Boolean('Automatic Installation',
                                   help='An auto-installable module is automatically installed by the '
                                        'system when all its dependencies are satisfied. '
                                        'If the module has no dependency, it is always installed.')
    state = fields.Selection(STATES, string='Status', default='uninstallable', readonly=True, index=True)
    demo = fields.Boolean('Demo Data', default=False, readonly=True)
    license = fields.Selection([
        ('GPL-2', 'GPL Version 2'),
        ('GPL-2 or any later version', 'GPL-2 or later version'),
        ('GPL-3', 'GPL Version 3'),
        ('GPL-3 or any later version', 'GPL-3 or later version'),
        ('AGPL-3', 'Affero GPL-3'),
        ('LGPL-3', 'LGPL Version 3'),
        ('Other OSI approved licence', 'Other OSI Approved License'),
        ('OEEL-1', 'Odoo Enterprise Edition License v1.0'),
        ('OPL-1', 'Odoo Proprietary License v1.0'),
        ('Other proprietary', 'Other Proprietary')
    ], string='License', default='LGPL-3', readonly=True)
    menus_by_module = fields.Text(string='Menus', compute='_get_views', store=True)
    reports_by_module = fields.Text(string='Reports', compute='_get_views', store=True)
    views_by_module = fields.Text(string='Views', compute='_get_views', store=True)
    application = fields.Boolean('Application', readonly=True)
    icon = fields.Char('Icon URL')
    icon_image = fields.Binary(string='Icon', compute='_get_icon_image')
    icon_flag = fields.Char(string='Flag', compute='_get_icon_image')
    to_buy = fields.Boolean('Odoo Enterprise Module', default=False)
    has_iap = fields.Boolean(compute='_compute_has_iap')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)', 'The name of the module must be unique!'),
    ]

    def _compute_has_iap(self):
        for module in self:
            module.has_iap = bool(module.id) and 'iap' in module.upstream_dependencies(exclude_states=('',)).mapped('name')

    @api.ondelete(at_uninstall=False)
    def _unlink_except_installed(self):
        for module in self:
            if module.state in ('installed', 'to upgrade', 'to remove', 'to install'):
                raise UserError(_('You are trying to remove a module that is installed or will be installed.'))

    def unlink(self):
        self.env.registry.clear_cache()
        return super(Module, self).unlink()

    def _get_modules_to_load_domain(self):
        """ Domain to retrieve the modules that should be loaded by the registry. """
        return [('state', '=', 'installed')]

    @classmethod
    def check_external_dependencies(cls, module_name, newstate='to install'):
        terp = cls.get_module_info(module_name)
        try:
            modules.check_manifest_dependencies(terp)
        except Exception as e:
            if newstate == 'to install':
                msg = _('Unable to install module "%s" because an external dependency is not met: %s', module_name, e.args[0])
            elif newstate == 'to upgrade':
                msg = _('Unable to upgrade module "%s" because an external dependency is not met: %s', module_name, e.args[0])
            else:
                msg = _('Unable to process module "%s" because an external dependency is not met: %s', module_name, e.args[0])
            raise UserError(msg)

    def _state_update(self, newstate, states_to_update, level=100):
        if level < 1:
            raise UserError(_('Recursion error in modules dependencies!'))

        # whether some modules are installed with demo data
        demo = False

        for module in self:
            if module.state not in states_to_update:
                demo = demo or module.demo
                continue

            # determine dependency modules to update/others
            update_mods, ready_mods = self.browse(), self.browse()
            for dep in module.dependencies_id:
                if dep.state == 'unknown':
                    raise UserError(_("You try to install module %r that depends on module %r.\nBut the latter module is not available in your system.", module.name, dep.name))
                if dep.depend_id.state == newstate:
                    ready_mods += dep.depend_id
                else:
                    update_mods += dep.depend_id

            # update dependency modules that require it, and determine demo for module
            update_demo = update_mods._state_update(newstate, states_to_update, level=level-1)
            module_demo = module.demo or update_demo or any(mod.demo for mod in ready_mods)
            demo = demo or module_demo

            if module.state in states_to_update:
                # check dependencies and update module itself
                self.check_external_dependencies(module.name, newstate)
                module.write({'state': newstate, 'demo': module_demo})

        return demo

    @assert_log_admin_access
    def button_install(self):
        # domain to select auto-installable (but not yet installed) modules
        auto_domain = [('state', '=', 'uninstalled'), ('auto_install', '=', True)]

        # determine whether an auto-install module must be installed:
        #  - all its dependencies are installed or to be installed,
        #  - at least one dependency is 'to install'
        install_states = frozenset(('installed', 'to install', 'to upgrade'))
        def must_install(module):
            states = {dep.state for dep in module.dependencies_id if dep.auto_install_required}
            return states <= install_states and 'to install' in states

        modules = self
        while modules:
            # Mark the given modules and their dependencies to be installed.
            modules._state_update('to install', ['uninstalled'])

            # Determine which auto-installable modules must be installed.
            modules = self.search(auto_domain).filtered(must_install)

        # the modules that are installed/to install/to upgrade
        install_mods = self.search([('state', 'in', list(install_states))])

        # check individual exclusions
        install_names = {module.name for module in install_mods}
        for module in install_mods:
            for exclusion in module.exclusion_ids:
                if exclusion.name in install_names:
                    raise UserError(_('Modules %r and %r are incompatible.', module.shortdesc, exclusion.exclusion_id.shortdesc))

        # check category exclusions
        def closure(module):
            todo = result = module
            while todo:
                result |= todo
                todo = todo.dependencies_id.depend_id
            return result

        exclusives = self.env['ir.module.category'].search([('exclusive', '=', True)])
        for category in exclusives:
            # retrieve installed modules in category and sub-categories
            categories = category.search([('id', 'child_of', category.ids)])
            modules = install_mods.filtered(lambda mod: mod.category_id in categories)
            # the installation is valid if all installed modules in categories
            # belong to the transitive dependencies of one of them
            if modules and not any(modules <= closure(module) for module in modules):
                labels = dict(self.fields_get(['state'])['state']['selection'])
                raise UserError(
                    _('You are trying to install incompatible modules in category %r:%s', category.name, ''.join(
                        f"\n- {module.shortdesc} ({labels[module.state]})"
                        for module in modules
                    ))
                )

        return dict(ACTION_DICT, name=_('Install'))

    @assert_log_admin_access
    def button_immediate_install(self):
        """ Installs the selected module(s) immediately and fully,
        returns the next res.config action to execute

        :returns: next res.config item to execute
        :rtype: dict[str, object]
        """
        _logger.info('User #%d triggered module installation', self.env.uid)
        # We use here the request object (which is thread-local) as a kind of
        # "global" env because the env is not usable in the following use case.
        # When installing a Chart of Account, I would like to send the
        # allowed companies to configure it on the correct company.
        # Otherwise, the SUPERUSER won't be aware of that and will try to
        # configure the CoA on his own company, which makes no sense.
        if request:
            request.allowed_company_ids = self.env.companies.ids
        return self._button_immediate_function(self.env.registry[self._name].button_install)

    @assert_log_admin_access
    def button_install_cancel(self):
        self.write({'state': 'uninstalled', 'demo': False})
        return True

    @assert_log_admin_access
    def module_uninstall(self):
        """ Perform the various steps required to uninstall a module completely
        including the deletion of all database structures created by the module:
        tables, columns, constraints, etc.
        """
        modules_to_remove = self.mapped('name')
        self.env['ir.model.data']._module_data_uninstall(modules_to_remove)
        # we deactivate prefetching to not try to read a column that has been deleted
        self.with_context(prefetch_fields=False).write({'state': 'uninstalled', 'latest_version': False})
        return True

    def _remove_copied_views(self):
        """ Remove the copies of the views installed by the modules in `self`.

        Those copies do not have an external id so they will not be cleaned by
        `_module_data_uninstall`. This is why we rely on `key` instead.

        It is important to remove these copies because using them will crash if
        they rely on data that don't exist anymore if the module is removed.
        """
        domain = expression.OR([[('key', '=like', m.name + '.%')] for m in self])
        orphans = self.env['ir.ui.view'].with_context(**{'active_test': False, MODULE_UNINSTALL_FLAG: True}).search(domain)
        orphans.unlink()

    @api.returns('self')
    def downstream_dependencies(self, known_deps=None,
                                exclude_states=('uninstalled', 'uninstallable', 'to remove')):
        """ Return the modules that directly or indirectly depend on the modules
        in `self`, and that satisfy the `exclude_states` filter.
        """
        if not self:
            return self
        self.flush_model(['name', 'state'])
        self.env['ir.module.module.dependency'].flush_model(['module_id', 'name'])
        known_deps = known_deps or self.browse()
        query = """ SELECT DISTINCT m.id
                    FROM ir_module_module_dependency d
                    JOIN ir_module_module m ON (d.module_id=m.id)
                    WHERE
                        d.name IN (SELECT name from ir_module_module where id in %s) AND
                        m.state NOT IN %s AND
                        m.id NOT IN %s """
        self._cr.execute(query, (tuple(self.ids), tuple(exclude_states), tuple(known_deps.ids or self.ids)))
        new_deps = self.browse([row[0] for row in self._cr.fetchall()])
        missing_mods = new_deps - known_deps
        known_deps |= new_deps
        if missing_mods:
            known_deps |= missing_mods.downstream_dependencies(known_deps, exclude_states)
        return known_deps

    @api.returns('self')
    def upstream_dependencies(self, known_deps=None,
                              exclude_states=('installed', 'uninstallable', 'to remove')):
        """ Return the dependency tree of modules of the modules in `self`, and
        that satisfy the `exclude_states` filter.
        """
        if not self:
            return self
        self.flush_model(['name', 'state'])
        self.env['ir.module.module.dependency'].flush_model(['module_id', 'name'])
        known_deps = known_deps or self.browse()
        query = """ SELECT DISTINCT m.id
                    FROM ir_module_module_dependency d
                    JOIN ir_module_module m ON (d.module_id=m.id)
                    WHERE
                        m.name IN (SELECT name from ir_module_module_dependency where module_id in %s) AND
                        m.state NOT IN %s AND
                        m.id NOT IN %s """
        self._cr.execute(query, (tuple(self.ids), tuple(exclude_states), tuple(known_deps.ids or self.ids)))
        new_deps = self.browse([row[0] for row in self._cr.fetchall()])
        missing_mods = new_deps - known_deps
        known_deps |= new_deps
        if missing_mods:
            known_deps |= missing_mods.upstream_dependencies(known_deps, exclude_states)
        return known_deps

    def next(self):
        """
        Return the action linked to an ir.actions.todo is there exists one that
        should be executed. Otherwise, redirect to /web
        """
        Todos = self.env['ir.actions.todo']
        _logger.info('getting next %s', Todos)
        active_todo = Todos.search([('state', '=', 'open')], limit=1)
        if active_todo:
            _logger.info('next action is "%s"', active_todo.name)
            return active_todo.action_launch()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/web',
        }

    def _button_immediate_function(self, function):
        if not self.env.registry.ready or self.env.registry._init:
            raise UserError(_('The method _button_immediate_install cannot be called on init or non loaded registries. Please use button_install instead.'))

        if getattr(threading.current_thread(), 'testing', False):
            raise RuntimeError(
                "Module operations inside tests are not transactional and thus forbidden.\n"
                "If you really need to perform module operations to test a specific behavior, it "
                "is best to write it as a standalone script, and ask the runbot/metastorm team "
                "for help."
            )
        try:
            # This is done because the installation/uninstallation/upgrade can modify a currently
            # running cron job and prevent it from finishing, and since the ir_cron table is locked
            # during execution, the lock won't be released until timeout.
            self._cr.execute("SELECT * FROM ir_cron FOR UPDATE NOWAIT")
        except psycopg2.OperationalError:
            raise UserError(_("Odoo is currently processing a scheduled action.\n"
                              "Module operations are not possible at this time, "
                              "please try again later or contact your system administrator."))
        function(self)

        self._cr.commit()
        registry = modules.registry.Registry.new(self._cr.dbname, update_module=True)
        self._cr.commit()
        if request and request.registry is self.env.registry:
            request.env.cr.reset()
            request.registry = request.env.registry
            assert request.env.registry is registry
        self._cr.reset()
        assert self.env.registry is registry

        # pylint: disable=next-method-called
        config = self.env['ir.module.module'].next() or {}
        if config.get('type') not in ('ir.actions.act_window_close',):
            return config

        # reload the client; open the first available root menu
        menu = self.env['ir.ui.menu'].search([('parent_id', '=', False)])[:1]
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'menu_id': menu.id},
        }

    @assert_log_admin_access
    def button_immediate_uninstall(self):
        """
        Uninstall the selected module(s) immediately and fully,
        returns the next res.config action to execute
        """
        _logger.info('User #%d triggered module uninstallation', self.env.uid)
        return self._button_immediate_function(self.env.registry[self._name].button_uninstall)

    @assert_log_admin_access
    def button_uninstall(self):
        un_installable_modules = set(odoo.conf.server_wide_modules) & set(self.mapped('name'))
        if un_installable_modules:
            raise UserError(_("Those modules cannot be uninstalled: %s", ', '.join(un_installable_modules)))
        if any(state not in ('installed', 'to upgrade') for state in self.mapped('state')):
            raise UserError(_(
                "One or more of the selected modules have already been uninstalled, if you "
                "believe this to be an error, you may try again later or contact support."
            ))
        deps = self.downstream_dependencies()
        (self + deps).write({'state': 'to remove'})
        return dict(ACTION_DICT, name=_('Uninstall'))

    @assert_log_admin_access
    def button_uninstall_wizard(self):
        """ Launch the wizard to uninstall the given module. """
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': _('Uninstall module'),
            'view_mode': 'form',
            'res_model': 'base.module.uninstall',
            'context': {'default_module_id': self.id},
        }

    def button_uninstall_cancel(self):
        self.write({'state': 'installed'})
        return True

    @assert_log_admin_access
    def button_immediate_upgrade(self):
        """
        Upgrade the selected module(s) immediately and fully,
        return the next res.config action to execute
        """
        return self._button_immediate_function(self.env.registry[self._name].button_upgrade)

    @assert_log_admin_access
    def button_upgrade(self):
        if not self:
            return
        Dependency = self.env['ir.module.module.dependency']
        self.update_list()

        todo = list(self)
        if 'base' in self.mapped('name'):
            # If an installed module is only present in the dependency graph through
            # a new, uninstalled dependency, it will not have been selected yet.
            # An update of 'base' should also update these modules, and as a consequence,
            # install the new dependency.
            todo.extend(self.search([
                ('state', '=', 'installed'),
                ('name', '!=', 'studio_customization'),
                ('id', 'not in', self.ids),
            ]))
        i = 0
        while i < len(todo):
            module = todo[i]
            i += 1
            if module.state not in ('installed', 'to upgrade'):
                raise UserError(_("Can not upgrade module %r. It is not installed.", module.name))
            if self.get_module_info(module.name).get("installable", True):
                self.check_external_dependencies(module.name, 'to upgrade')
            for dep in Dependency.search([('name', '=', module.name)]):
                if (
                    dep.module_id.state == 'installed'
                    and dep.module_id not in todo
                    and dep.module_id.name != 'studio_customization'
                ):
                    todo.append(dep.module_id)

        self.browse(module.id for module in todo).write({'state': 'to upgrade'})

        to_install = []
        for module in todo:
            if not self.get_module_info(module.name).get("installable", True):
                continue
            for dep in module.dependencies_id:
                if dep.state == 'unknown':
                    raise UserError(_('You try to upgrade the module %s that depends on the module: %s.\nBut this module is not available in your system.', module.name, dep.name))
                if dep.state == 'uninstalled':
                    to_install += self.search([('name', '=', dep.name)]).ids

        self.browse(to_install).button_install()
        return dict(ACTION_DICT, name=_('Apply Schedule Upgrade'))

    @assert_log_admin_access
    def button_upgrade_cancel(self):
        self.write({'state': 'installed'})
        return True

    @staticmethod
    def get_values_from_terp(terp):
        return {
            'description': dedent(terp.get('description', '')),
            'shortdesc': terp.get('name', ''),
            'author': terp.get('author', 'Unknown'),
            'maintainer': terp.get('maintainer', False),
            'contributors': ', '.join(terp.get('contributors', [])) or False,
            'website': terp.get('website', ''),
            'license': terp.get('license', 'LGPL-3'),
            'sequence': terp.get('sequence', 100),
            'application': terp.get('application', False),
            'auto_install': terp.get('auto_install', False) is not False,
            'icon': terp.get('icon', False),
            'summary': terp.get('summary', ''),
            'url': terp.get('url') or terp.get('live_test_url', ''),
            'to_buy': False
        }

    @api.model_create_multi
    def create(self, vals_list):
        modules = super().create(vals_list)
        module_metadata_list = [{
            'name': 'module_%s' % module.name,
            'model': 'ir.module.module',
            'module': 'base',
            'res_id': module.id,
            'noupdate': True,
        } for module in modules]
        self.env['ir.model.data'].create(module_metadata_list)
        return modules

    # update the list of available packages
    @assert_log_admin_access
    @api.model
    def update_list(self):
        res = [0, 0]    # [update, add]

        default_version = modules.adapt_version('1.0')
        known_mods = self.with_context(lang=None).search([])
        known_mods_names = {mod.name: mod for mod in known_mods}

        # iterate through detected modules and update/create them in db
        for mod_name in modules.get_modules():
            mod = known_mods_names.get(mod_name)
            terp = self.get_module_info(mod_name)
            values = self.get_values_from_terp(terp)

            if mod:
                updated_values = {}
                for key in values:
                    old = getattr(mod, key)
                    if (old or values[key]) and values[key] != old:
                        updated_values[key] = values[key]
                if terp.get('installable', True) and mod.state == 'uninstallable':
                    updated_values['state'] = 'uninstalled'
                if parse_version(terp.get('version', default_version)) > parse_version(mod.latest_version or default_version):
                    res[0] += 1
                if updated_values:
                    mod.write(updated_values)
            else:
                mod_path = modules.get_module_path(mod_name)
                if not mod_path or not terp:
                    continue
                state = "uninstalled" if terp.get('installable', True) else "uninstallable"
                mod = self.create(dict(name=mod_name, state=state, **values))
                res[1] += 1

            mod._update_from_terp(terp)

        return res

    def _update_from_terp(self, terp):
        self._update_dependencies(terp.get('depends', []), terp.get('auto_install'))
        self._update_exclusions(terp.get('excludes', []))
        self._update_category(terp.get('category', 'Uncategorized'))

    def _update_dependencies(self, depends=None, auto_install_requirements=()):
        self.env['ir.module.module.dependency'].flush_model()
        existing = set(dep.name for dep in self.dependencies_id)
        needed = set(depends or [])
        for dep in (needed - existing):
            self._cr.execute('INSERT INTO ir_module_module_dependency (module_id, name) values (%s, %s)', (self.id, dep))
        for dep in (existing - needed):
            self._cr.execute('DELETE FROM ir_module_module_dependency WHERE module_id = %s and name = %s', (self.id, dep))
        self._cr.execute('UPDATE ir_module_module_dependency SET auto_install_required = (name = any(%s)) WHERE module_id = %s',
                         (list(auto_install_requirements or ()), self.id))
        self.env['ir.module.module.dependency'].invalidate_model(['auto_install_required'])
        self.invalidate_recordset(['dependencies_id'])

    def _update_exclusions(self, excludes=None):
        self.env['ir.module.module.exclusion'].flush_model()
        existing = set(excl.name for excl in self.exclusion_ids)
        needed = set(excludes or [])
        for name in (needed - existing):
            self._cr.execute('INSERT INTO ir_module_module_exclusion (module_id, name) VALUES (%s, %s)', (self.id, name))
        for name in (existing - needed):
            self._cr.execute('DELETE FROM ir_module_module_exclusion WHERE module_id=%s AND name=%s', (self.id, name))
        self.invalidate_recordset(['exclusion_ids'])

    def _update_category(self, category='Uncategorized'):
        current_category = self.category_id
        current_category_path = []
        while current_category:
            current_category_path.insert(0, current_category.name)
            current_category = current_category.parent_id

        categs = category.split('/')
        if categs != current_category_path:
            cat_id = modules.db.create_categories(self._cr, categs)
            self.write({'category_id': cat_id})

    def _update_translations(self, filter_lang=None, overwrite=False):
        if not filter_lang:
            langs = self.env['res.lang'].get_installed()
            filter_lang = [code for code, _ in langs]
        elif not isinstance(filter_lang, (list, tuple)):
            filter_lang = [filter_lang]

        update_mods = self.filtered(lambda r: r.state in ('installed', 'to install', 'to upgrade'))
        mod_dict = {
            mod.name: mod.dependencies_id.mapped('name')
            for mod in update_mods
        }
        mod_names = topological_sort(mod_dict)
        self.env['ir.module.module']._load_module_terms(mod_names, filter_lang, overwrite)

    def _check(self):
        for module in self:
            if not module.description_html:
                _logger.warning('module %s: description is empty!', module.name)

    def _get(self, name):
        """ Return the (sudoed) `ir.module.module` record with the given name.
        The result may be an empty recordset if the module is not found.
        """
        model_id = self._get_id(name) if name else False
        return self.browse(model_id).sudo()

    @tools.ormcache('name')
    def _get_id(self, name):
        self.flush_model(['name'])
        self.env.cr.execute("SELECT id FROM ir_module_module WHERE name=%s", (name,))
        return self.env.cr.fetchone()

    @api.model
    @tools.ormcache()
    def _installed(self):
        """ Return the set of installed modules as a dictionary {name: id} """
        return {
            module.name: module.id
            for module in self.sudo().search([('state', '=', 'installed')])
        }

    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        if field_name == 'category_id':
            enable_counters = kwargs.get('enable_counters', False)
            domain = [('parent_id', '=', False), ('child_ids.module_ids', '!=', False)]

            excluded_xmlids = [
                'base.module_category_website_theme',
                'base.module_category_theme',
            ]
            if not self.user_has_groups('base.group_no_one'):
                excluded_xmlids.append('base.module_category_hidden')

            excluded_category_ids = []
            for excluded_xmlid in excluded_xmlids:
                categ = self.env.ref(excluded_xmlid, False)
                if not categ:
                    continue
                excluded_category_ids.append(categ.id)

            if excluded_category_ids:
                domain = expression.AND([
                    domain,
                    [('id', 'not in', excluded_category_ids)],
                ])

            records = self.env['ir.module.category'].search_read(domain, ['display_name'], order="sequence")

            values_range = OrderedDict()
            for record in records:
                record_id = record['id']
                if enable_counters:
                    model_domain = expression.AND([
                        kwargs.get('search_domain', []),
                        kwargs.get('category_domain', []),
                        kwargs.get('filter_domain', []),
                        [('category_id', 'child_of', record_id), ('category_id', 'not in', excluded_category_ids)]
                    ])
                    record['__count'] = self.env['ir.module.module'].search_count(model_domain)
                values_range[record_id] = record

            return {
                'parent_field': 'parent_id',
                'values': list(values_range.values()),
            }

        return super(Module, self).search_panel_select_range(field_name, **kwargs)

    @api.model
    def _load_module_terms(self, modules, langs, overwrite=False):
        """ Load PO files of the given modules for the given languages. """
        # load i18n files
        translation_importer = TranslationImporter(self.env.cr, verbose=False)

        for module_name in modules:
            modpath = get_module_path(module_name)
            if not modpath:
                continue
            for lang in langs:
                po_paths = get_po_paths(module_name, lang)
                for po_path in po_paths:
                    _logger.info('module %s: loading translation file %s for language %s', module_name, po_path, lang)
                    translation_importer.load_file(po_path, lang)
                if lang != 'en_US' and not po_paths:
                    _logger.info('module %s: no translation for language %s', module_name, lang)

        translation_importer.save(overwrite=overwrite)


DEP_STATES = STATES + [('unknown', 'Unknown')]

class ModuleDependency(models.Model):
    _name = "ir.module.module.dependency"
    _description = "Module dependency"
    _log_access = False  # inserts are done manually, create and write uid, dates are always null
    _allow_sudo_commands = False

    # the dependency name
    name = fields.Char(index=True)

    # the module that depends on it
    module_id = fields.Many2one('ir.module.module', 'Module', ondelete='cascade')

    # the module corresponding to the dependency, and its status
    depend_id = fields.Many2one('ir.module.module', 'Dependency',
                                compute='_compute_depend', search='_search_depend')
    state = fields.Selection(DEP_STATES, string='Status', compute='_compute_state')

    auto_install_required = fields.Boolean(
        default=True,
        help="Whether this dependency blocks automatic installation "
             "of the dependent")

    @api.depends('name')
    def _compute_depend(self):
        # retrieve all modules corresponding to the dependency names
        names = list(set(dep.name for dep in self))
        mods = self.env['ir.module.module'].search([('name', 'in', names)])

        # index modules by name, and assign dependencies
        name_mod = dict((mod.name, mod) for mod in mods)
        for dep in self:
            dep.depend_id = name_mod.get(dep.name)

    def _search_depend(self, operator, value):
        assert operator == 'in'
        modules = self.env['ir.module.module'].browse(set(value))
        return [('name', 'in', modules.mapped('name'))]

    @api.depends('depend_id.state')
    def _compute_state(self):
        for dependency in self:
            dependency.state = dependency.depend_id.state or 'unknown'


class ModuleExclusion(models.Model):
    _name = "ir.module.module.exclusion"
    _description = "Module exclusion"
    _allow_sudo_commands = False

    # the exclusion name
    name = fields.Char(index=True)

    # the module that excludes it
    module_id = fields.Many2one('ir.module.module', 'Module', ondelete='cascade')

    # the module corresponding to the exclusion, and its status
    exclusion_id = fields.Many2one('ir.module.module', 'Exclusion Module',
                                   compute='_compute_exclusion', search='_search_exclusion')
    state = fields.Selection(DEP_STATES, string='Status', compute='_compute_state')

    @api.depends('name')
    def _compute_exclusion(self):
        # retrieve all modules corresponding to the exclusion names
        names = list(set(excl.name for excl in self))
        mods = self.env['ir.module.module'].search([('name', 'in', names)])

        # index modules by name, and assign dependencies
        name_mod = {mod.name: mod for mod in mods}
        for excl in self:
            excl.exclusion_id = name_mod.get(excl.name)

    def _search_exclusion(self, operator, value):
        assert operator == 'in'
        modules = self.env['ir.module.module'].browse(set(value))
        return [('name', 'in', modules.mapped('name'))]

    @api.depends('exclusion_id.state')
    def _compute_state(self):
        for exclusion in self:
            exclusion.state = exclusion.exclusion_id.state or 'unknown'
