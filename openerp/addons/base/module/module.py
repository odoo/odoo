# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from docutils import nodes
from docutils.core import publish_string
from docutils.transforms import Transform, writer_aux
from docutils.writers.html4css1 import Writer
import importlib
import logging
from operator import attrgetter
import os
import re
import shutil
import tempfile
import urllib
import urllib2
import urlparse
import zipfile
import zipimport
import lxml.html
from openerp.exceptions import UserError

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO   # NOQA

import openerp
import openerp.exceptions
from openerp import modules, tools
from openerp.modules.db import create_categories
from openerp.modules import get_module_resource
from openerp.tools import ormcache
from openerp.tools.parse_version import parse_version
from openerp.tools.translate import _
from openerp.tools import html_sanitize
from openerp.osv import osv, orm, fields
from openerp import api, fields as fields2

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


class module_category(osv.osv):
    _name = "ir.module.category"
    _description = "Application"

    def _module_nbr(self, cr, uid, ids, prop, unknow_none, context):
        cr.execute('SELECT category_id, COUNT(*) \
                      FROM ir_module_module \
                     WHERE category_id IN %(ids)s \
                        OR category_id IN (SELECT id \
                                             FROM ir_module_category \
                                            WHERE parent_id IN %(ids)s) \
                     GROUP BY category_id', {'ids': tuple(ids)}
                   )
        result = dict(cr.fetchall())
        for id in ids:
            cr.execute('select id from ir_module_category where parent_id=%s', (id,))
            result[id] = sum([result.get(c, 0) for (c,) in cr.fetchall()],
                             result.get(id, 0))
        return result

    _columns = {
        'name': fields.char("Name", required=True, translate=True, select=True),
        'parent_id': fields.many2one('ir.module.category', 'Parent Application', select=True),
        'child_ids': fields.one2many('ir.module.category', 'parent_id', 'Child Applications'),
        'module_nr': fields.function(_module_nbr, string='Number of Apps', type='integer'),
        'module_ids': fields.one2many('ir.module.module', 'category_id', 'Modules'),
        'description': fields.text("Description", translate=True),
        'sequence': fields.integer('Sequence'),
        'visible': fields.boolean('Visible'),
        'xml_id': fields.function(osv.osv.get_external_id, type='char', string="External ID"),
    }
    _order = 'name'

    _defaults = {
        'visible': 1,
    }

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

class module(osv.osv):
    _name = "ir.module.module"
    _rec_name = "shortdesc"
    _description = "Module"

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
         res = super(module, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
         result = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'action_server_module_immediate_install')[1]
         if view_type == 'form':
             if res.get('toolbar',False):
                 list = [rec for rec in res['toolbar']['action'] if rec.get('id', False) != result]
                 res['toolbar'] = {'action': list}
         return res

    @classmethod
    def get_module_info(cls, name):
        info = {}
        try:
            info = modules.load_information_from_description_file(name)
        except Exception:
            _logger.debug('Error when trying to fetch informations for '
                          'module %s', name, exc_info=True)
        return info

    def _get_desc(self, cr, uid, ids, field_name=None, arg=None, context=None):
        res = dict.fromkeys(ids, '')
        for module in self.browse(cr, uid, ids, context=context):
            path = get_module_resource(module.name, 'static/description/index.html')
            if path:
                with tools.file_open(path, 'rb') as desc_file:
                    doc = desc_file.read()
                    html = lxml.html.document_fromstring(doc)
                    for element, attribute, link, pos in html.iterlinks():
                        if element.get('src') and not '//' in element.get('src') and not 'static/' in element.get('src'):
                            element.set('src', "/%s/static/description/%s" % (module.name, element.get('src')))
                    res[module.id] = html_sanitize(lxml.html.tostring(html))
            else:
                overrides = {
                    'embed_stylesheet': False,
                    'doctitle_xform': False,
                    'output_encoding': 'unicode',
                    'xml_declaration': False,
                }
                output = publish_string(source=module.description or '', settings_overrides=overrides, writer=MyWriter())
                res[module.id] = html_sanitize(output)
        return res

    def _get_latest_version(self, cr, uid, ids, field_name=None, arg=None, context=None):
        default_version = modules.adapt_version('1.0')
        res = dict.fromkeys(ids, default_version)
        for m in self.browse(cr, uid, ids):
            res[m.id] = self.get_module_info(m.name).get('version', default_version)
        return res

    def _get_views(self, cr, uid, ids, field_name=None, arg=None, context=None):
        res = {}
        model_data_obj = self.pool.get('ir.model.data')

        dmodels = []
        if field_name is None or 'views_by_module' in field_name:
            dmodels.append('ir.ui.view')
        if field_name is None or 'reports_by_module' in field_name:
            dmodels.append('ir.actions.report.xml')
        if field_name is None or 'menus_by_module' in field_name:
            dmodels.append('ir.ui.menu')
        assert dmodels, "no models for %s" % field_name

        for module_rec in self.browse(cr, uid, ids, context=context):
            res_mod_dic = res[module_rec.id] = {
                'menus_by_module': [],
                'reports_by_module': [],
                'views_by_module': []
            }

            # Skip uninstalled modules below, no data to find anyway.
            if module_rec.state not in ('installed', 'to upgrade', 'to remove'):
                continue

            # then, search and group ir.model.data records
            imd_models = dict([(m, []) for m in dmodels])
            imd_ids = model_data_obj.search(cr, uid, [
                ('module', '=', module_rec.name),
                ('model', 'in', tuple(dmodels))
            ])

            for imd_res in model_data_obj.read(cr, uid, imd_ids, ['model', 'res_id'], context=context):
                imd_models[imd_res['model']].append(imd_res['res_id'])

            def browse(model):
                M = self.pool[model]
                # as this method is called before the module update, some xmlid may be invalid at this stage
                # explictly filter records before reading them
                ids = M.exists(cr, uid, imd_models.get(model, []), context)
                return M.browse(cr, uid, ids, context)

            def format_view(v):
                aa = v.inherit_id and '* INHERIT ' or ''
                return '%s%s (%s)' % (aa, v.name, v.type)

            res_mod_dic['views_by_module'] = map(format_view, browse('ir.ui.view'))
            res_mod_dic['reports_by_module'] = map(attrgetter('name'), browse('ir.actions.report.xml'))
            res_mod_dic['menus_by_module'] = map(attrgetter('complete_name'), browse('ir.ui.menu'))

        for key in res.iterkeys():
            for k, v in res[key].iteritems():
                res[key][k] = "\n".join(sorted(v))
        return res

    def _get_icon_image(self, cr, uid, ids, field_name=None, arg=None, context=None):
        res = dict.fromkeys(ids, '')
        for module in self.browse(cr, uid, ids, context=context):
            path = get_module_resource(module.name, 'static', 'description', 'icon.png')
            if path:
                image_file = tools.file_open(path, 'rb')
                try:
                    res[module.id] = image_file.read().encode('base64')
                finally:
                    image_file.close()
        return res

    _columns = {
        'name': fields.char("Technical Name", readonly=True, required=True, select=True),
        'category_id': fields.many2one('ir.module.category', 'Category', readonly=True, select=True),
        'shortdesc': fields.char('Module Name', readonly=True, translate=True),
        'summary': fields.char('Summary', readonly=True, translate=True),
        'description': fields.text("Description", readonly=True, translate=True),
        'description_html': fields.function(_get_desc, string='Description HTML', type='html', method=True, readonly=True),
        'author': fields.char("Author", readonly=True),
        'maintainer': fields.char('Maintainer', readonly=True),
        'contributors': fields.text('Contributors', readonly=True),
        'website': fields.char("Website", readonly=True),

        # attention: Incorrect field names !!
        #   installed_version refers the latest version (the one on disk)
        #   latest_version refers the installed version (the one in database)
        #   published_version refers the version available on the repository
        'installed_version': fields.function(_get_latest_version, string='Latest Version', type='char'),
        'latest_version': fields.char('Installed Version', readonly=True),
        'published_version': fields.char('Published Version', readonly=True),

        'url': fields.char('URL', readonly=True),
        'sequence': fields.integer('Sequence'),
        'dependencies_id': fields.one2many('ir.module.module.dependency', 'module_id', 'Dependencies', readonly=True),
        'auto_install': fields.boolean('Automatic Installation',
                                       help='An auto-installable module is automatically installed by the '
                                            'system when all its dependencies are satisfied. '
                                            'If the module has no dependency, it is always installed.'),
        'state': fields.selection([
            ('uninstallable', 'Not Installable'),
            ('uninstalled', 'Not Installed'),
            ('installed', 'Installed'),
            ('to upgrade', 'To be upgraded'),
            ('to remove', 'To be removed'),
            ('to install', 'To be installed')
        ], string='Status', readonly=True, select=True),
        'demo': fields.boolean('Demo Data', readonly=True),
        'license': fields.selection([
            ('GPL-2', 'GPL Version 2'),
            ('GPL-2 or any later version', 'GPL-2 or later version'),
            ('GPL-3', 'GPL Version 3'),
            ('GPL-3 or any later version', 'GPL-3 or later version'),
            ('AGPL-3', 'Affero GPL-3'),
            ('LGPL-3', 'LGPL Version 3'),
            ('Other OSI approved licence', 'Other OSI Approved Licence'),
            ('OEEL-1', 'Odoo Enterprise Edition License v1.0'),
            ('Other proprietary', 'Other Proprietary')
        ], string='License', readonly=True),
        'menus_by_module': fields.function(_get_views, string='Menus', type='text', multi="meta", store=True),
        'reports_by_module': fields.function(_get_views, string='Reports', type='text', multi="meta", store=True),
        'views_by_module': fields.function(_get_views, string='Views', type='text', multi="meta", store=True),
        'application': fields.boolean('Application', readonly=True),
        'icon': fields.char('Icon URL'),
        'icon_image': fields.function(_get_icon_image, string='Icon', type="binary"),
    }

    _defaults = {
        'state': 'uninstalled',
        'sequence': 100,
        'demo': False,
        'license': 'LGPL-3',
    }
    _order = 'sequence,name'

    def _name_uniq_msg(self, cr, uid, ids, context=None):
        return _('The name of the module must be unique !')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)', _name_uniq_msg),
    ]

    def unlink(self, cr, uid, ids, context=None):
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]
        mod_names = []
        for mod in self.read(cr, uid, ids, ['state', 'name'], context):
            if mod['state'] in ('installed', 'to upgrade', 'to remove', 'to install'):
                raise UserError(_('You try to remove a module that is installed or will be installed'))
            mod_names.append(mod['name'])
        #Removing the entry from ir_model_data
        #ids_meta = self.pool.get('ir.model.data').search(cr, uid, [('name', '=', 'module_meta_information'), ('module', 'in', mod_names)])

        #if ids_meta:
        #    self.pool.get('ir.model.data').unlink(cr, uid, ids_meta, context)

        self.clear_caches()
        return super(module, self).unlink(cr, uid, ids, context=context)

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

    def button_immediate_install(self, cr, uid, ids, context=None):
        """ Installs the selected module(s) immediately and fully,
        returns the next res.config action to execute

        :param ids: identifiers of the modules to install
        :returns: next res.config item to execute
        :rtype: dict[str, object]
        """
        return self._button_immediate_function(cr, uid, ids, self.button_install, context=context)

    def button_install_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'uninstalled', 'demo': False})
        return True

    def module_uninstall(self, cr, uid, ids, context=None):
        """Perform the various steps required to uninstall a module completely
        including the deletion of all database structures created by the module:
        tables, columns, constraints, etc."""
        ir_model_data = self.pool.get('ir.model.data')
        modules_to_remove = [m.name for m in self.browse(cr, uid, ids, context)]
        ir_model_data._module_data_uninstall(cr, uid, modules_to_remove, context)
        self.write(cr, uid, ids, {'state': 'uninstalled', 'latest_version': False})
        return True

    def downstream_dependencies(self, cr, uid, ids, known_dep_ids=None,
                                exclude_states=['uninstalled', 'uninstallable', 'to remove'],
                                context=None):
        """Return the ids of all modules that directly or indirectly depend
        on the given module `ids`, and that satisfy the `exclude_states`
        filter"""
        if not ids:
            return []
        known_dep_ids = set(known_dep_ids or [])
        cr.execute('''SELECT DISTINCT m.id
                        FROM
                            ir_module_module_dependency d
                        JOIN
                            ir_module_module m ON (d.module_id=m.id)
                        WHERE
                            d.name IN (SELECT name from ir_module_module where id in %s) AND
                            m.state NOT IN %s AND
                            m.id NOT IN %s ''',
                   (tuple(ids), tuple(exclude_states), tuple(known_dep_ids or ids)))
        new_dep_ids = set([m[0] for m in cr.fetchall()])
        missing_mod_ids = new_dep_ids - known_dep_ids
        known_dep_ids |= new_dep_ids
        if missing_mod_ids:
            known_dep_ids |= set(self.downstream_dependencies(cr, uid, list(missing_mod_ids),
                                                              known_dep_ids, exclude_states, context))
        return list(known_dep_ids)

    def upstream_dependencies(self, cr, uid, ids, known_dep_ids=None,
                                exclude_states=['installed', 'uninstallable', 'to remove'],
                                context=None):
        """ Return the dependency tree of modules of the given `ids`, and that
            satisfy the `exclude_states` filter """
        if not ids:
            return []
        known_dep_ids = set(known_dep_ids or [])
        cr.execute('''SELECT DISTINCT m.id
                        FROM
                            ir_module_module_dependency d
                        JOIN
                            ir_module_module m ON (d.module_id=m.id)
                        WHERE
                            m.name IN (SELECT name from ir_module_module_dependency where module_id in %s) AND
                            m.state NOT IN %s AND
                            m.id NOT IN %s ''',
                   (tuple(ids), tuple(exclude_states), tuple(known_dep_ids or ids)))
        new_dep_ids = set([m[0] for m in cr.fetchall()])
        missing_mod_ids = new_dep_ids - known_dep_ids
        known_dep_ids |= new_dep_ids
        if missing_mod_ids:
            known_dep_ids |= set(self.upstream_dependencies(cr, uid, list(missing_mod_ids),
                                                              known_dep_ids, exclude_states, context))
        return list(known_dep_ids)

    def _button_immediate_function(self, cr, uid, ids, function, context=None):
        function(cr, uid, ids, context=context)

        cr.commit()
        api.Environment.reset()
        registry = openerp.modules.registry.RegistryManager.new(cr.dbname, update_module=True)

        cr.commit()
        config = registry['res.config'].next(cr, uid, [], context=context) or {}
        if config.get('type') not in ('ir.actions.act_window_close',):
            return config

        # reload the client; open the first available root menu
        menu_obj = registry['ir.ui.menu']
        menu_ids = menu_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'menu_id': menu_ids and menu_ids[0] or False}
        }

    def button_immediate_uninstall(self, cr, uid, ids, context=None):
        """
        Uninstall the selected module(s) immediately and fully,
        returns the next res.config action to execute
        """
        return self._button_immediate_function(cr, uid, ids, self.button_uninstall, context=context)

    def button_uninstall(self, cr, uid, ids, context=None):
        if any(m.name == 'base' for m in self.browse(cr, uid, ids, context=context)):
            raise UserError(_("The `base` module cannot be uninstalled"))
        dep_ids = self.downstream_dependencies(cr, uid, ids, context=context)
        self.write(cr, uid, ids + dep_ids, {'state': 'to remove'})
        return dict(ACTION_DICT, name=_('Uninstall'))

    def button_uninstall_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'installed'})
        return True

    def button_immediate_upgrade(self, cr, uid, ids, context=None):
        """
        Upgrade the selected module(s) immediately and fully,
        return the next res.config action to execute
        """
        return self._button_immediate_function(cr, uid, ids, self.button_upgrade, context=context)

    def button_upgrade(self, cr, uid, ids, context=None):
        depobj = self.pool.get('ir.module.module.dependency')
        todo = list(self.browse(cr, uid, ids, context=context))
        self.update_list(cr, uid)

        i = 0
        while i < len(todo):
            mod = todo[i]
            i += 1
            if mod.state not in ('installed', 'to upgrade'):
                raise UserError(_("Can not upgrade module '%s'. It is not installed.") % (mod.name,))
            self.check_external_dependencies(mod.name, 'to upgrade')
            iids = depobj.search(cr, uid, [('name', '=', mod.name)], context=context)
            for dep in depobj.browse(cr, uid, iids, context=context):
                if dep.module_id.state == 'installed' and dep.module_id not in todo:
                    todo.append(dep.module_id)

        ids = map(lambda x: x.id, todo)
        self.write(cr, uid, ids, {'state': 'to upgrade'}, context=context)

        to_install = []
        for mod in todo:
            for dep in mod.dependencies_id:
                if dep.state == 'unknown':
                    raise UserError(_('You try to upgrade a module that depends on the module: %s.\nBut this module is not available in your system.') % (dep.name,))
                if dep.state == 'uninstalled':
                    ids2 = self.search(cr, uid, [('name', '=', dep.name)])
                    to_install.extend(ids2)

        self.button_install(cr, uid, to_install, context=context)
        return dict(ACTION_DICT, name=_('Apply Schedule Upgrade'))

    def button_upgrade_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'installed'})
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

    def create(self, cr, uid, vals, context=None):
        new_id = super(module, self).create(cr, uid, vals, context=context)
        module_metadata = {
            'name': 'module_%s' % vals['name'],
            'model': 'ir.module.module',
            'module': 'base',
            'res_id': new_id,
            'noupdate': True,
        }
        self.pool['ir.model.data'].create(cr, uid, module_metadata)
        return new_id

    # update the list of available packages
    def update_list(self, cr, uid, context=None):
        res = [0, 0]    # [update, add]

        default_version = modules.adapt_version('1.0')
        known_mods = self.browse(cr, uid, self.search(cr, uid, []))
        known_mods_names = dict([(m.name, m) for m in known_mods])

        # iterate through detected modules and update/create them in db
        for mod_name in modules.get_modules():
            mod = known_mods_names.get(mod_name)
            terp = self.get_module_info(mod_name)
            values = self.get_values_from_terp(terp)

            if mod:
                updated_values = {}
                for key in values:
                    old = getattr(mod, key)
                    updated = isinstance(values[key], basestring) and tools.ustr(values[key]) or values[key]
                    if (old or updated) and updated != old:
                        updated_values[key] = values[key]
                if terp.get('installable', True) and mod.state == 'uninstallable':
                    updated_values['state'] = 'uninstalled'
                if parse_version(terp.get('version', default_version)) > parse_version(mod.latest_version or default_version):
                    res[0] += 1
                if updated_values:
                    self.write(cr, uid, mod.id, updated_values)
            else:
                mod_path = modules.get_module_path(mod_name)
                if not mod_path:
                    continue
                if not terp or not terp.get('installable', True):
                    continue
                id = self.create(cr, uid, dict(name=mod_name, state='uninstalled', **values))
                mod = self.browse(cr, uid, id)
                res[1] += 1

            self._update_dependencies(cr, uid, mod, terp.get('depends', []))
            self._update_category(cr, uid, mod, terp.get('category', 'Uncategorized'))

        return res

    def download(self, cr, uid, ids, download=True, context=None):
        return []

    def install_from_urls(self, cr, uid, urls, context=None):
        if not self.pool['res.users'].has_group(cr, uid, 'base.group_system'):
            raise openerp.exceptions.AccessDenied()

        apps_server = urlparse.urlparse(self.get_apps_server(cr, uid, context=context))

        OPENERP = openerp.release.product_name.lower()
        tmp = tempfile.mkdtemp()
        _logger.debug('Install from url: %r', urls)
        try:
            # 1. Download & unzip missing modules
            for module_name, url in urls.items():
                if not url:
                    continue    # nothing to download, local version is already the last one

                up = urlparse.urlparse(url)
                if up.scheme != apps_server.scheme or up.netloc != apps_server.netloc:
                    raise openerp.exceptions.AccessDenied()

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
            for module_name, url in urls.items():
                if module_name == OPENERP or not url:
                    continue    # OPENERP is special case, handled below, and no URL means local module
                module_path = modules.get_module_path(module_name, downloaded=True, display_warning=False)
                bck = backup(module_path, False)
                _logger.info('Copy downloaded module `%s` to `%s`', module_name, module_path)
                shutil.move(os.path.join(tmp, module_name), module_path)
                if bck:
                    shutil.rmtree(bck)

            # 2b.  Copy/Replace server+base module source if downloaded
            if urls.get(OPENERP, None):
                # special case. it contains the server and the base module.
                # extract path is not the same
                base_path = os.path.dirname(modules.get_module_path('base'))

                # copy all modules in the SERVER/openerp/addons directory to the new "openerp" module (except base itself)
                for d in os.listdir(base_path):
                    if d != 'base' and os.path.isdir(os.path.join(base_path, d)):
                        destdir = os.path.join(tmp, OPENERP, 'addons', d)    # XXX 'openerp' subdirectory ?
                        shutil.copytree(os.path.join(base_path, d), destdir)

                # then replace the server by the new "base" module
                server_dir = openerp.tools.config['root_path']      # XXX or dirname()
                bck = backup(server_dir)
                _logger.info('Copy downloaded module `openerp` to `%s`', server_dir)
                shutil.move(os.path.join(tmp, OPENERP), server_dir)
                #if bck:
                #    shutil.rmtree(bck)

            self.update_list(cr, uid, context=context)

            with_urls = [m for m, u in urls.items() if u]
            downloaded_ids = self.search(cr, uid, [('name', 'in', with_urls)], context=context)
            already_installed = self.search(cr, uid, [('id', 'in', downloaded_ids), ('state', '=', 'installed')], context=context)

            to_install_ids = self.search(cr, uid, [('name', 'in', urls.keys()), ('state', '=', 'uninstalled')], context=context)
            post_install_action = self.button_immediate_install(cr, uid, to_install_ids, context=context)

            if already_installed:
                # in this case, force server restart to reload python code...
                cr.commit()
                openerp.service.server.restart()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'home',
                    'params': {'wait': True},
                }
            return post_install_action
        finally:
            shutil.rmtree(tmp)

    def get_apps_server(self, cr, uid, context=None):
        return tools.config.get('apps_server', 'https://apps.openerp.com/apps')

    def _update_dependencies(self, cr, uid, mod_browse, depends=None):
        if depends is None:
            depends = []
        existing = set(x.name for x in mod_browse.dependencies_id)
        needed = set(depends)
        for dep in (needed - existing):
            cr.execute('INSERT INTO ir_module_module_dependency (module_id, name) values (%s, %s)', (mod_browse.id, dep))
        for dep in (existing - needed):
            cr.execute('DELETE FROM ir_module_module_dependency WHERE module_id = %s and name = %s', (mod_browse.id, dep))
        self.invalidate_cache(cr, uid, ['dependencies_id'], [mod_browse.id])

    def _update_category(self, cr, uid, mod_browse, category='Uncategorized'):
        current_category = mod_browse.category_id
        current_category_path = []
        while current_category:
            current_category_path.insert(0, current_category.name)
            current_category = current_category.parent_id

        categs = category.split('/')
        if categs != current_category_path:
            cat_id = create_categories(cr, categs)
            mod_browse.write({'category_id': cat_id})

    def update_translations(self, cr, uid, ids, filter_lang=None, context=None):
        if not filter_lang:
            res_lang = self.pool.get('res.lang')
            lang_ids = res_lang.search(cr, uid, [('translatable', '=', True)])
            filter_lang = [lang.code for lang in res_lang.browse(cr, uid, lang_ids)]
        elif not isinstance(filter_lang, (list, tuple)):
            filter_lang = [filter_lang]
        modules = [m.name for m in self.browse(cr, uid, ids) if m.state in ('installed', 'to install', 'to upgrade')]
        self.pool.get('ir.translation').load_module_terms(cr, modules, filter_lang, context=context)

    def check(self, cr, uid, ids, context=None):
        for mod in self.browse(cr, uid, ids, context=context):
            if not mod.description:
                _logger.warning('module %s: description is empty !', mod.name)

    @api.model
    @ormcache()
    def _installed(self):
        """ Return the set of installed modules as a dictionary {name: id} """
        return {
            module.name: module.id
            for module in self.sudo().search([('state', '=', 'installed')])
        }


DEP_STATES = [
    ('uninstallable', 'Uninstallable'),
    ('uninstalled', 'Not Installed'),
    ('installed', 'Installed'),
    ('to upgrade', 'To be upgraded'),
    ('to remove', 'To be removed'),
    ('to install', 'To be installed'),
    ('unknown', 'Unknown'),
]

class module_dependency(osv.Model):
    _name = "ir.module.module.dependency"
    _description = "Module dependency"

    # the dependency name
    name = fields2.Char(index=True)

    # the module that depends on it
    module_id = fields2.Many2one('ir.module.module', 'Module', ondelete='cascade')

    # the module corresponding to the dependency, and its status
    depend_id = fields2.Many2one('ir.module.module', 'Dependency', compute='_compute_depend')
    state = fields2.Selection(DEP_STATES, string='Status', compute='_compute_state')

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
