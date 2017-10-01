# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from operator import attrgetter
import importlib
import logging
import os
import shutil
import tempfile
import urllib2
import urlparse
import zipfile

from docutils import nodes
from docutils.core import publish_string
from docutils.transforms import Transform, writer_aux
from docutils.writers.html4css1 import Writer
import lxml.html

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO   # NOQA

import odoo
from odoo import api, fields, models, modules, tools, _
from odoo.exceptions import AccessDenied, UserError
from odoo.tools.parse_version import parse_version
from odoo.tools.misc import topological_sort

_logger = logging.getLogger(__name__)

ACTION_DICT = {
    'view_type': 'form',
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


class ModuleCategory(models.Model):
    _name = "ir.module.category"
    _description = "Application"
    _order = 'name'

    @api.depends('module_ids')
    def _compute_module_nr(self):
        cr = self._cr
        cr.execute('SELECT category_id, COUNT(*) \
                      FROM ir_module_module \
                     WHERE category_id IN %(ids)s \
                        OR category_id IN (SELECT id \
                                             FROM ir_module_category \
                                            WHERE parent_id IN %(ids)s) \
                     GROUP BY category_id', {'ids': tuple(self.ids)}
                   )
        result = dict(cr.fetchall())
        for cat in self.filtered('id'):
            cr.execute('SELECT id FROM ir_module_category WHERE parent_id=%s', (cat.id,))
            cat.module_nr = sum([result.get(c, 0) for (c,) in cr.fetchall()], result.get(cat.id, 0))

    name = fields.Char(string='Name', required=True, translate=True, index=True)
    parent_id = fields.Many2one('ir.module.category', string='Parent Application', index=True)
    child_ids = fields.One2many('ir.module.category', 'parent_id', string='Child Applications')
    module_nr = fields.Integer(string='Number of Apps', compute='_compute_module_nr')
    module_ids = fields.One2many('ir.module.module', 'category_id', string='Modules')
    description = fields.Text(string='Description', translate=True)
    sequence = fields.Integer(string='Sequence')
    visible = fields.Boolean(string='Visible', default=True)
    xml_id = fields.Char(string='External ID', compute='_compute_xml_id')

    def _compute_xml_id(self):
        xml_ids = defaultdict(list)
        domain = [('model', '=', self._name), ('res_id', 'in', self.ids)]
        for data in self.env['ir.model.data'].search_read(domain, ['module', 'name', 'res_id']):
            xml_ids[data['res_id']].append("%s.%s" % (data['module'], data['name']))
        for cat in self:
            cat.xml_id = xml_ids.get(cat.id, [''])[0]


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

class Module(models.Model):
    _name = "ir.module.module"
    _rec_name = "shortdesc"
    _description = "Module"
    _order = 'sequence,name'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(Module, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=False)
        if view_type == 'form' and res.get('toolbar',False):
            install_id = self.env.ref('base.action_server_module_immediate_install').id
            action = [rec for rec in res['toolbar']['action'] if rec.get('id', False) != install_id]
            res['toolbar'] = {'action': action}
        return res

    @classmethod
    def get_module_info(cls, name):
        try:
            return modules.load_information_from_description_file(name)
        except Exception:
            _logger.debug('Error when trying to fetch information for module %s', name, exc_info=True)
            return {}

    @api.depends('name', 'description')
    def _get_desc(self):
        for module in self:
            path = modules.get_module_resource(module.name, 'static/description/index.html')
            if path:
                with tools.file_open(path, 'rb') as desc_file:
                    doc = desc_file.read()
                    html = lxml.html.document_fromstring(doc)
                    for element, attribute, link, pos in html.iterlinks():
                        if element.get('src') and not '//' in element.get('src') and not 'static/' in element.get('src'):
                            element.set('src', "/%s/static/description/%s" % (module.name, element.get('src')))
                    module.description_html = tools.html_sanitize(lxml.html.tostring(html))
            else:
                overrides = {
                    'embed_stylesheet': False,
                    'doctitle_xform': False,
                    'output_encoding': 'unicode',
                    'xml_declaration': False,
                }
                output = publish_string(source=module.description or '', settings_overrides=overrides, writer=MyWriter())
                module.description_html = tools.html_sanitize(output)

    @api.depends('name')
    def _get_latest_version(self):
        default_version = modules.adapt_version('1.0')
        for module in self:
            module.installed_version = self.get_module_info(module.name).get('version', default_version)

    @api.depends('name', 'state')
    def _get_views(self):
        IrModelData = self.env['ir.model.data'].with_context(active_test=True)
        dmodels = ['ir.ui.view', 'ir.actions.report.xml', 'ir.ui.menu']

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
            for data in IrModelData.search(imd_domain):
                imd_models[data.model].append(data.res_id)

            def browse(model):
                # as this method is called before the module update, some xmlid
                # may be invalid at this stage; explictly filter records before
                # reading them
                return self.env[model].browse(imd_models[model]).exists()

            def format_view(v):
                return '%s%s (%s)' % (v.inherit_id and '* INHERIT ' or '', v.name, v.type)

            module.views_by_module = "\n".join(sorted(map(format_view, browse('ir.ui.view'))))
            module.reports_by_module = "\n".join(sorted(map(attrgetter('name'), browse('ir.actions.report.xml'))))
            module.menus_by_module = "\n".join(sorted(map(attrgetter('complete_name'), browse('ir.ui.menu'))))

    @api.depends('icon')
    def _get_icon_image(self):
        for module in self:
            module.icon_image = ''
            if module.icon:
                path_parts = module.icon.split('/')
                path = modules.get_module_resource(path_parts[1], *path_parts[2:])
            else:
                path = modules.module.get_module_icon(module.name)
            if path:
                with tools.file_open(path, 'rb') as image_file:
                    module.icon_image = image_file.read().encode('base64')

    name = fields.Char('Technical Name', readonly=True, required=True, index=True)
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
    auto_install = fields.Boolean('Automatic Installation',
                                   help='An auto-installable module is automatically installed by the '
                                        'system when all its dependencies are satisfied. '
                                        'If the module has no dependency, it is always installed.')
    state = fields.Selection(STATES, string='Status', default='uninstalled', readonly=True, index=True)
    demo = fields.Boolean('Demo Data', default=False, readonly=True)
    license = fields.Selection([
        ('GPL-2', 'GPL Version 2'),
        ('GPL-2 or any later version', 'GPL-2 or later version'),
        ('GPL-3', 'GPL Version 3'),
        ('GPL-3 or any later version', 'GPL-3 or later version'),
        ('AGPL-3', 'Affero GPL-3'),
        ('LGPL-3', 'LGPL Version 3'),
        ('Other OSI approved licence', 'Other OSI Approved Licence'),
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

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)', 'The name of the module must be unique!'),
    ]

    @api.multi
    def unlink(self):
        if not self:
            return True
        for module in self:
            if module.state in ('installed', 'to upgrade', 'to remove', 'to install'):
                raise UserError(_('You try to remove a module that is installed or will be installed'))
        self.clear_caches()
        return super(Module, self).unlink()

    @staticmethod
    def _check_external_dependencies(terp):
        depends = terp.get('external_dependencies')
        if not depends:
            return
        for pydep in depends.get('python', []):
            try:
                importlib.import_module(pydep)
            except ImportError:
                raise ImportError('No module named %s' % (pydep,))

        for binary in depends.get('bin', []):
            try:
                tools.find_in_path(binary)
            except IOError:
                raise Exception('Unable to find %r in path' % (binary,))

    @classmethod
    def check_external_dependencies(cls, module_name, newstate='to install'):
        terp = cls.get_module_info(module_name)
        try:
            cls._check_external_dependencies(terp)
        except Exception, e:
            if newstate == 'to install':
                msg = _('Unable to install module "%s" because an external dependency is not met: %s')
            elif newstate == 'to upgrade':
                msg = _('Unable to upgrade module "%s" because an external dependency is not met: %s')
            else:
                msg = _('Unable to process module "%s" because an external dependency is not met: %s')
            raise UserError(msg % (module_name, e.args[0]))

    @api.multi
    def state_update(self, newstate, states_to_update, level=100):
        if level < 1:
            raise UserError(_('Recursion error in modules dependencies !'))

        # whether some modules are installed with demo data
        demo = False

        for module in self:
            # determine dependency modules to update/others
            update_mods, ready_mods = self.browse(), self.browse()
            for dep in module.dependencies_id:
                if dep.state == 'unknown':
                    raise UserError(_("You try to install module '%s' that depends on module '%s'.\nBut the latter module is not available in your system.") % (module.name, dep.name,))
                if dep.depend_id.state == newstate:
                    ready_mods += dep.depend_id
                else:
                    update_mods += dep.depend_id

            # update dependency modules that require it, and determine demo for module
            update_demo = update_mods.state_update(newstate, states_to_update, level=level-1)
            module_demo = module.demo or update_demo or any(mod.demo for mod in ready_mods)
            demo = demo or module_demo

            # check dependencies and update module itself
            self.check_external_dependencies(module.name, newstate)
            if module.state in states_to_update:
                module.write({'state': newstate, 'demo': module_demo})

        return demo

    @api.multi
    def button_install(self):
        # domain to select auto-installable (but not yet installed) modules
        auto_domain = [('state', '=', 'uninstalled'), ('auto_install', '=', True)]

        # determine whether an auto-install module must be installed:
        #  - all its dependencies are installed or to be installed,
        #  - at least one dependency is 'to install'
        install_states = frozenset(('installed', 'to install', 'to upgrade'))
        def must_install(module):
            states = set(dep.state for dep in module.dependencies_id)
            return states <= install_states and 'to install' in states

        modules = self
        while modules:
            # Mark the given modules and their dependencies to be installed.
            modules.state_update('to install', ['uninstalled'])

            # Determine which auto-installable modules must be installed.
            modules = self.search(auto_domain).filtered(must_install)

        # retrieve the installed (or to be installed) theme modules
        theme_category = self.env.ref('base.module_category_theme')
        theme_modules = self.search([
            ('state', 'in', list(install_states)),
            ('category_id', 'child_of', [theme_category.id]),
        ])

        # determine all theme modules that mods depends on, including mods
        def theme_deps(mods):
            deps = mods.mapped('dependencies_id.depend_id')
            while deps:
                mods |= deps
                deps = deps.mapped('dependencies_id.depend_id')
            return mods & theme_modules

        if any(module.state == 'to install' for module in theme_modules):
            # check: the installation is valid if all installed theme modules
            # correspond to one theme module and all its theme dependencies
            if not any(theme_deps(module) == theme_modules for module in theme_modules):
                state_labels = dict(self.fields_get(['state'])['state']['selection'])
                themes_list = [
                    "- %s (%s)" % (module.shortdesc, state_labels[module.state])
                    for module in theme_modules
                ]
                raise UserError(_(
                    "You are trying to install incompatible themes:\n%s\n\n" \
                    "Please uninstall your current theme before installing another one.\n"
                    "Warning: switching themes may significantly alter the look of your current website pages!"
                ) % ("\n".join(themes_list)))
        return dict(ACTION_DICT, name=_('Install'))

    @api.multi
    def button_immediate_install(self):
        """ Installs the selected module(s) immediately and fully,
        returns the next res.config action to execute

        :returns: next res.config item to execute
        :rtype: dict[str, object]
        """
        return self._button_immediate_function(type(self).button_install)

    @api.multi
    def button_install_cancel(self):
        self.write({'state': 'uninstalled', 'demo': False})
        return True

    @api.multi
    def module_uninstall(self):
        """ Perform the various steps required to uninstall a module completely
        including the deletion of all database structures created by the module:
        tables, columns, constraints, etc.
        """
        modules_to_remove = self.mapped('name')
        self.env['ir.model.data']._module_data_uninstall(modules_to_remove)
        self.write({'state': 'uninstalled', 'latest_version': False})
        return True

    @api.multi
    @api.returns('self')
    def downstream_dependencies(self, known_deps=None,
                                exclude_states=('uninstalled', 'uninstallable', 'to remove')):
        """ Return the modules that directly or indirectly depend on the modules
        in `self`, and that satisfy the `exclude_states` filter.
        """
        if not self:
            return self
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

    @api.multi
    @api.returns('self')
    def upstream_dependencies(self, known_deps=None,
                              exclude_states=('installed', 'uninstallable', 'to remove')):
        """ Return the dependency tree of modules of the modules in `self`, and
        that satisfy the `exclude_states` filter.
        """
        if not self:
            return self
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

    @api.multi
    def _button_immediate_function(self, function):
        function(self)

        self._cr.commit()
        api.Environment.reset()
        modules.registry.Registry.new(self._cr.dbname, update_module=True)

        self._cr.commit()
        env = api.Environment(self._cr, self._uid, self._context)
        config = env['res.config'].next() or {}
        if config.get('type') not in ('ir.actions.act_window_close',):
            return config

        # reload the client; open the first available root menu
        menu = env['ir.ui.menu'].search([('parent_id', '=', False)])[:1]
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'menu_id': menu.id},
        }

    @api.multi
    def button_immediate_uninstall(self):
        """
        Uninstall the selected module(s) immediately and fully,
        returns the next res.config action to execute
        """
        return self._button_immediate_function(type(self).button_uninstall)

    @api.multi
    def button_uninstall(self):
        if 'base' in self.mapped('name'):
            raise UserError(_("The `base` module cannot be uninstalled"))
        deps = self.downstream_dependencies()
        (self + deps).write({'state': 'to remove'})
        return dict(ACTION_DICT, name=_('Uninstall'))

    @api.multi
    def button_uninstall_cancel(self):
        self.write({'state': 'installed'})
        return True

    @api.multi
    def button_immediate_upgrade(self):
        """
        Upgrade the selected module(s) immediately and fully,
        return the next res.config action to execute
        """
        return self._button_immediate_function(type(self).button_upgrade)

    @api.multi
    def button_upgrade(self):
        Dependency = self.env['ir.module.module.dependency']
        self.update_list()

        todo = list(self)
        i = 0
        while i < len(todo):
            module = todo[i]
            i += 1
            if module.state not in ('installed', 'to upgrade'):
                raise UserError(_("Can not upgrade module '%s'. It is not installed.") % (module.name,))
            self.check_external_dependencies(module.name, 'to upgrade')
            for dep in Dependency.search([('name', '=', module.name)]):
                if dep.module_id.state == 'installed' and dep.module_id not in todo:
                    todo.append(dep.module_id)

        self.browse(module.id for module in todo).write({'state': 'to upgrade'})

        to_install = []
        for module in todo:
            for dep in module.dependencies_id:
                if dep.state == 'unknown':
                    raise UserError(_('You try to upgrade the module %s that depends on the module: %s.\nBut this module is not available in your system.') % (module.name, dep.name,))
                if dep.state == 'uninstalled':
                    to_install += self.search([('name', '=', dep.name)]).ids

        self.browse(to_install).button_install()
        return dict(ACTION_DICT, name=_('Apply Schedule Upgrade'))

    @api.multi
    def button_upgrade_cancel(self):
        self.write({'state': 'installed'})
        return True

    @staticmethod
    def get_values_from_terp(terp):
        return {
            'description': terp.get('description', ''),
            'shortdesc': terp.get('name', ''),
            'author': terp.get('author', 'Unknown'),
            'maintainer': terp.get('maintainer', False),
            'contributors': ', '.join(terp.get('contributors', [])) or False,
            'website': terp.get('website', ''),
            'license': terp.get('license', 'LGPL-3'),
            'sequence': terp.get('sequence', 100),
            'application': terp.get('application', False),
            'auto_install': terp.get('auto_install', False),
            'icon': terp.get('icon', False),
            'summary': terp.get('summary', ''),
            'url': terp.get('url') or terp.get('live_test_url', ''),
        }

    @api.model
    def create(self, vals):
        new = super(Module, self).create(vals)
        module_metadata = {
            'name': 'module_%s' % vals['name'],
            'model': 'ir.module.module',
            'module': 'base',
            'res_id': new.id,
            'noupdate': True,
        }
        self.env['ir.model.data'].create(module_metadata)
        return new

    # update the list of available packages
    @api.model
    def update_list(self):
        res = [0, 0]    # [update, add]

        default_version = modules.adapt_version('1.0')
        known_mods = self.search([])
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
                    updated = tools.ustr(values[key]) if isinstance(values[key], basestring) else values[key]
                    if (old or updated) and updated != old:
                        updated_values[key] = values[key]
                if terp.get('installable', True) and mod.state == 'uninstallable':
                    updated_values['state'] = 'uninstalled'
                if parse_version(terp.get('version', default_version)) > parse_version(mod.latest_version or default_version):
                    res[0] += 1
                if updated_values:
                    mod.write(updated_values)
            else:
                mod_path = modules.get_module_path(mod_name)
                if not mod_path:
                    continue
                if not terp or not terp.get('installable', True):
                    continue
                mod = self.create(dict(name=mod_name, state='uninstalled', **values))
                res[1] += 1

            mod._update_dependencies(terp.get('depends', []))
            mod._update_category(terp.get('category', 'Uncategorized'))

        return res

    @api.multi
    def download(self, download=True):
        return []

    @api.model
    def install_from_urls(self, urls):
        if not self.env.user.has_group('base.group_system'):
            raise AccessDenied()

        # One-click install is opt-in - cfr Issue #15225
        ad_dir = tools.config.addons_data_dir
        if not os.access(ad_dir, os.W_OK):
            msg = (_("Automatic install of downloaded Apps is currently disabled.") + "\n\n" +
                   _("To enable it, make sure this directory exists and is writable on the server:") +
                   "\n%s" % ad_dir)
            _logger.warning(msg)
            raise UserError(msg)

        apps_server = urlparse.urlparse(self.get_apps_server())

        OPENERP = odoo.release.product_name.lower()
        tmp = tempfile.mkdtemp()
        _logger.debug('Install from url: %r', urls)
        try:
            # 1. Download & unzip missing modules
            for module_name, url in urls.iteritems():
                if not url:
                    continue    # nothing to download, local version is already the last one

                up = urlparse.urlparse(url)
                if up.scheme != apps_server.scheme or up.netloc != apps_server.netloc:
                    raise AccessDenied()

                try:
                    _logger.info('Downloading module `%s` from OpenERP Apps', module_name)
                    content = urllib2.urlopen(url).read()
                except Exception:
                    _logger.exception('Failed to fetch module %s', module_name)
                    raise UserError(_('The `%s` module appears to be unavailable at the moment, please try again later.') % module_name)
                else:
                    zipfile.ZipFile(StringIO(content)).extractall(tmp)
                    assert os.path.isdir(os.path.join(tmp, module_name))

            # 2a. Copy/Replace module source in addons path
            for module_name, url in urls.iteritems():
                if module_name == OPENERP or not url:
                    continue    # OPENERP is special case, handled below, and no URL means local module
                module_path = modules.get_module_path(module_name, downloaded=True, display_warning=False)
                bck = backup(module_path, False)
                _logger.info('Copy downloaded module `%s` to `%s`', module_name, module_path)
                shutil.move(os.path.join(tmp, module_name), module_path)
                if bck:
                    shutil.rmtree(bck)

            # 2b.  Copy/Replace server+base module source if downloaded
            if urls.get(OPENERP):
                # special case. it contains the server and the base module.
                # extract path is not the same
                base_path = os.path.dirname(modules.get_module_path('base'))

                # copy all modules in the SERVER/odoo/addons directory to the new "odoo" module (except base itself)
                for d in os.listdir(base_path):
                    if d != 'base' and os.path.isdir(os.path.join(base_path, d)):
                        destdir = os.path.join(tmp, OPENERP, 'addons', d)    # XXX 'odoo' subdirectory ?
                        shutil.copytree(os.path.join(base_path, d), destdir)

                # then replace the server by the new "base" module
                server_dir = tools.config['root_path']      # XXX or dirname()
                bck = backup(server_dir)
                _logger.info('Copy downloaded module `odoo` to `%s`', server_dir)
                shutil.move(os.path.join(tmp, OPENERP), server_dir)
                #if bck:
                #    shutil.rmtree(bck)

            self.update_list()

            with_urls = [module_name for module_name, url in urls.iteritems() if url]
            downloaded = self.search([('name', 'in', with_urls)])
            installed = self.search([('id', 'in', downloaded.ids), ('state', '=', 'installed')])

            to_install = self.search([('name', 'in', urls.keys()), ('state', '=', 'uninstalled')])
            post_install_action = to_install.button_immediate_install()

            if installed or to_install:
                # in this case, force server restart to reload python code...
                self._cr.commit()
                odoo.service.server.restart()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'home',
                    'params': {'wait': True},
                }
            return post_install_action

        finally:
            shutil.rmtree(tmp)

    @api.model
    def get_apps_server(self):
        return tools.config.get('apps_server', 'https://apps.odoo.com/apps')

    def _update_dependencies(self, depends=None):
        existing = set(dep.name for dep in self.dependencies_id)
        needed = set(depends or [])
        for dep in (needed - existing):
            self._cr.execute('INSERT INTO ir_module_module_dependency (module_id, name) values (%s, %s)', (self.id, dep))
        for dep in (existing - needed):
            self._cr.execute('DELETE FROM ir_module_module_dependency WHERE module_id = %s and name = %s', (self.id, dep))
        self.invalidate_cache(['dependencies_id'], self.ids)

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

    @api.multi
    def update_translations(self, filter_lang=None):
        if not filter_lang:
            langs = self.env['res.lang'].search([('translatable', '=', True)])
            filter_lang = [lang.code for lang in langs]
        elif not isinstance(filter_lang, (list, tuple)):
            filter_lang = [filter_lang]

        update_mods = self.filtered(lambda r: r.state in ('installed', 'to install', 'to upgrade'))
        mod_dict = {
            mod.name: mod.dependencies_id.mapped('name')
            for mod in update_mods
        }
        mod_names = topological_sort(mod_dict)
        self.env['ir.translation'].load_module_terms(mod_names, filter_lang)

    @api.multi
    def check(self):
        for module in self:
            if not module.description:
                _logger.warning('module %s: description is empty !', module.name)

    @api.model
    @tools.ormcache()
    def _installed(self):
        """ Return the set of installed modules as a dictionary {name: id} """
        return {
            module.name: module.id
            for module in self.sudo().search([('state', '=', 'installed')])
        }


DEP_STATES = STATES + [('unknown', 'Unknown')]

class ModuleDependency(models.Model):
    _name = "ir.module.module.dependency"
    _description = "Module dependency"

    # the dependency name
    name = fields.Char(index=True)

    # the module that depends on it
    module_id = fields.Many2one('ir.module.module', 'Module', ondelete='cascade')

    # the module corresponding to the dependency, and its status
    depend_id = fields.Many2one('ir.module.module', 'Dependency', compute='_compute_depend')
    state = fields.Selection(DEP_STATES, string='Status', compute='_compute_state')

    @api.multi
    @api.depends('name')
    def _compute_depend(self):
        # retrieve all modules corresponding to the dependency names
        names = list(set(dep.name for dep in self))
        mods = self.env['ir.module.module'].search([('name', 'in', names)])

        # index modules by name, and assign dependencies
        name_mod = dict((mod.name, mod) for mod in mods)
        for dep in self:
            dep.depend_id = name_mod.get(dep.name)

    @api.one
    @api.depends('depend_id.state')
    def _compute_state(self):
        self.state = self.depend_id.state or 'unknown'
