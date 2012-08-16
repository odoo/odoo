# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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
import imp
import logging
import re
import urllib
import zipimport
import base64

from openerp import modules, pooler, release, tools, addons
from openerp.tools.parse_version import parse_version
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

_logger = logging.getLogger(__name__)

ACTION_DICT = {
    'view_type': 'form',
    'view_mode': 'form',
    'res_model': 'base.module.upgrade',
    'target': 'new',
    'type': 'ir.actions.act_window',
    'nodestroy':True,
}

class module_category(osv.osv):
    _name = "ir.module.category"
    _description = "Application"

    def _module_nbr(self,cr,uid, ids, prop, unknow_none, context):
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
        'name': fields.char("Name", size=128, required=True, translate=True, select=True),
        'parent_id': fields.many2one('ir.module.category', 'Parent Application', select=True),
        'child_ids': fields.one2many('ir.module.category', 'parent_id', 'Child Applications'),
        'module_nr': fields.function(_module_nbr, string='Number of Modules', type='integer'),
        'module_ids' : fields.one2many('ir.module.module', 'category_id', 'Modules'),
        'description' : fields.text("Description", translate=True),
        'sequence' : fields.integer('Sequence'),
        'visible' : fields.boolean('Visible'),
        'xml_id': fields.function(osv.osv.get_external_id, type='char', size=128, string="External ID"),
    }
    _order = 'name'

    _defaults = {
        'visible' : 1,
    }

class module(osv.osv):
    _name = "ir.module.module"
    _rec_name = "shortdesc"
    _description = "Module"

    @classmethod
    def get_module_info(cls, name):
        info = {}
        try:
            info = modules.load_information_from_description_file(name)
            info['version'] = release.major_version + '.' + info['version']
        except Exception:
            _logger.debug('Error when trying to fetch informations for '
                          'module %s', name, exc_info=True)
        return info

    def _get_latest_version(self, cr, uid, ids, field_name=None, arg=None, context=None):
        res = dict.fromkeys(ids, '')
        for m in self.browse(cr, uid, ids):
            res[m.id] = self.get_module_info(m.name).get('version', '')
        return res

    def _get_views(self, cr, uid, ids, field_name=None, arg=None, context=None):
        res = {}
        model_data_obj = self.pool.get('ir.model.data')
        view_obj = self.pool.get('ir.ui.view')
        report_obj = self.pool.get('ir.actions.report.xml')
        menu_obj = self.pool.get('ir.ui.menu')

        dmodels = []
        if field_name is None or 'views_by_module' in field_name:
            dmodels.append('ir.ui.view')
        if field_name is None or 'reports_by_module' in field_name:
            dmodels.append('ir.actions.report.xml')
        if field_name is None or 'menus_by_module' in field_name:
            dmodels.append('ir.ui.menu')
        assert dmodels, "no models for %s" % field_name

        for module_rec in self.browse(cr, uid, ids, context=context):
            res[module_rec.id] = {
                'menus_by_module': [],
                'reports_by_module': [],
                'views_by_module': []
            }

            # Skip uninstalled modules below, no data to find anyway.
            if module_rec.state not in ('installed', 'to upgrade', 'to remove'):
                continue

            # then, search and group ir.model.data records
            imd_models = dict( [(m,[]) for m in dmodels])
            imd_ids = model_data_obj.search(cr,uid,[('module','=', module_rec.name),
                ('model','in',tuple(dmodels))])

            for imd_res in model_data_obj.read(cr, uid, imd_ids, ['model', 'res_id'], context=context):
                imd_models[imd_res['model']].append(imd_res['res_id'])

            # For each one of the models, get the names of these ids.
            # We use try except, because views or menus may not exist.
            try:
                res_mod_dic = res[module_rec.id]
                view_ids = imd_models.get('ir.ui.view', [])
                for v in view_obj.browse(cr, uid, view_ids, context=context):
                    aa = v.inherit_id and '* INHERIT ' or ''
                    res_mod_dic['views_by_module'].append(aa + v.name + '('+v.type+')')

                report_ids = imd_models.get('ir.actions.report.xml', [])
                for rx in report_obj.browse(cr, uid, report_ids, context=context):
                    res_mod_dic['reports_by_module'].append(rx.name)

                menu_ids = imd_models.get('ir.ui.menu', [])
                for um in menu_obj.browse(cr, uid, menu_ids, context=context):
                    res_mod_dic['menus_by_module'].append(um.complete_name)
            except KeyError, e:
                _logger.warning(
                      'Data not found for items of %s', module_rec.name)
            except AttributeError, e:
                _logger.warning(
                      'Data not found for items of %s %s', module_rec.name, str(e))
            except Exception, e:
                _logger.warning('Unknown error while fetching data of %s',
                      module_rec.name, exc_info=True)
        for key, _ in res.iteritems():
            for k, v in res[key].iteritems():
                res[key][k] = "\n".join(sorted(v))
        return res

    def _get_icon_image(self, cr, uid, ids, field_name=None, arg=None, context=None):
        res = dict.fromkeys(ids, '')
        for module in self.browse(cr, uid, ids, context=context):
            path = addons.get_module_resource(module.name, 'static', 'src', 'img', 'icon.png')
            if path:
                image_file = tools.file_open(path, 'rb')
                try:
                    res[module.id] = image_file.read().encode('base64')
                finally:
                    image_file.close()
        return res

    _columns = {
        'name': fields.char("Technical Name", size=128, readonly=True, required=True, select=True),
        'category_id': fields.many2one('ir.module.category', 'Category', readonly=True, select=True),
        'shortdesc': fields.char('Module Name', size=64, readonly=True, translate=True),
        'summary': fields.char('Summary', size=64, readonly=True, translate=True),
        'description': fields.text("Description", readonly=True, translate=True),
        'author': fields.char("Author", size=128, readonly=True),
        'maintainer': fields.char('Maintainer', size=128, readonly=True),
        'contributors': fields.text('Contributors', readonly=True),
        'website': fields.char("Website", size=256, readonly=True),

        # attention: Incorrect field names !!
        #   installed_version refer the latest version (the one on disk)
        #   latest_version refer the installed version (the one in database)
        #   published_version refer the version available on the repository
        'installed_version': fields.function(_get_latest_version,
            string='Latest Version', type='char'),
        'latest_version': fields.char('Installed Version', size=64, readonly=True),
        'published_version': fields.char('Published Version', size=64, readonly=True),

        'url': fields.char('URL', size=128, readonly=True),
        'sequence': fields.integer('Sequence'),
        'dependencies_id': fields.one2many('ir.module.module.dependency',
            'module_id', 'Dependencies', readonly=True),
        'auto_install': fields.boolean('Automatic Installation',
            help='An auto-installable module is automatically installed by the '
            'system when all its dependencies are satisfied. '
            'If the module has no dependency, it is always installed.'),
        'state': fields.selection([
            ('uninstallable','Not Installable'),
            ('uninstalled','Not Installed'),
            ('installed','Installed'),
            ('to upgrade','To be upgraded'),
            ('to remove','To be removed'),
            ('to install','To be installed')
        ], string='State', readonly=True, select=True),
        'demo': fields.boolean('Demo Data', readonly=True),
        'license': fields.selection([
                ('GPL-2', 'GPL Version 2'),
                ('GPL-2 or any later version', 'GPL-2 or later version'),
                ('GPL-3', 'GPL Version 3'),
                ('GPL-3 or any later version', 'GPL-3 or later version'),
                ('AGPL-3', 'Affero GPL-3'),
                ('Other OSI approved licence', 'Other OSI Approved Licence'),
                ('Other proprietary', 'Other Proprietary')
            ], string='License', readonly=True),
        'menus_by_module': fields.function(_get_views, string='Menus', type='text', multi="meta", store=True),
        'reports_by_module': fields.function(_get_views, string='Reports', type='text', multi="meta", store=True),
        'views_by_module': fields.function(_get_views, string='Views', type='text', multi="meta", store=True),
        'certificate' : fields.char('Quality Certificate', size=64, readonly=True),
        'application': fields.boolean('Application', readonly=True),
        'icon': fields.char('Icon URL', size=128),
        'icon_image': fields.function(_get_icon_image, string='Icon', type="binary"),
    }

    _defaults = {
        'state': 'uninstalled',
        'sequence': 100,
        'demo': False,
        'license': 'AGPL-3',
    }
    _order = 'sequence,name'

    def _name_uniq_msg(self, cr, uid, ids, context=None):
        return _('The name of the module must be unique !')
    def _certificate_uniq_msg(self, cr, uid, ids, context=None):
        return _('The certificate ID of the module must be unique !')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)',_name_uniq_msg ),
        ('certificate_uniq', 'UNIQUE (certificate)',_certificate_uniq_msg )
    ]

    def unlink(self, cr, uid, ids, context=None):
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]
        mod_names = []
        for mod in self.read(cr, uid, ids, ['state','name'], context):
            if mod['state'] in ('installed', 'to upgrade', 'to remove', 'to install'):
                raise orm.except_orm(_('Error'),
                        _('You try to remove a module that is installed or will be installed'))
            mod_names.append(mod['name'])
        #Removing the entry from ir_model_data
        #ids_meta = self.pool.get('ir.model.data').search(cr, uid, [('name', '=', 'module_meta_information'), ('module', 'in', mod_names)])

        #if ids_meta:
        #    self.pool.get('ir.model.data').unlink(cr, uid, ids_meta, context)

        return super(module, self).unlink(cr, uid, ids, context=context)

    @staticmethod
    def _check_external_dependencies(terp):
        depends = terp.get('external_dependencies')
        if not depends:
            return
        for pydep in depends.get('python', []):
            parts = pydep.split('.')
            parts.reverse()
            path = None
            while parts:
                part = parts.pop()
                try:
                    _, path, _ = imp.find_module(part, path and [path] or None)
                except ImportError:
                    raise ImportError('No module named %s' % (pydep,))

        for binary in depends.get('bin', []):
            if tools.find_in_path(binary) is None:
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
            raise orm.except_orm(_('Error'), msg % (module_name, e.args[0]))

    def state_update(self, cr, uid, ids, newstate, states_to_update, context=None, level=100):
        if level<1:
            raise orm.except_orm(_('Error'), _('Recursion error in modules dependencies !'))
        demo = False
        for module in self.browse(cr, uid, ids, context=context):
            mdemo = False
            for dep in module.dependencies_id:
                if dep.state == 'unknown':
                    raise orm.except_orm(_('Error'), _("You try to install module '%s' that depends on module '%s'.\nBut the latter module is not available in your system.") % (module.name, dep.name,))
                ids2 = self.search(cr, uid, [('name','=',dep.name)])
                if dep.state != newstate:
                    mdemo = self.state_update(cr, uid, ids2, newstate, states_to_update, context, level-1,) or mdemo
                else:
                    od = self.browse(cr, uid, ids2)[0]
                    mdemo = od.demo or mdemo

            self.check_external_dependencies(module.name, newstate)
            if not module.dependencies_id:
                mdemo = module.demo
            if module.state in states_to_update:
                self.write(cr, uid, [module.id], {'state': newstate, 'demo':mdemo})
            demo = demo or mdemo
        return demo

    def button_install(self, cr, uid, ids, context=None):

        # Mark the given modules to be installed.
        self.state_update(cr, uid, ids, 'to install', ['uninstalled'], context)

        # Mark (recursively) the newly satisfied modules to also be installed:

        # Select all auto-installable (but not yet installed) modules.
        domain = [('state', '=', 'uninstalled'), ('auto_install', '=', True),]
        uninstalled_ids = self.search(cr, uid, domain, context=context)
        uninstalled_modules = self.browse(cr, uid, uninstalled_ids, context=context)

        # Keep those with all their dependencies satisfied.
        def all_depencies_satisfied(m):
            return all(x.state in ('to install', 'installed', 'to upgrade') for x in m.dependencies_id)
        to_install_modules = filter(all_depencies_satisfied, uninstalled_modules)
        to_install_ids = map(lambda m: m.id, to_install_modules)

        # Mark them to be installed.
        if to_install_ids:
            self.button_install(cr, uid, to_install_ids, context=context)
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
        self.write(cr, uid, ids, {'state': 'uninstalled', 'demo':False})
        return True

    def module_uninstall(self, cr, uid, ids, context=None):
        """Perform the various steps required to uninstall a module completely
        including the deletion of all database structures created by the module:
        tables, columns, constraints, etc."""
        ir_model_data = self.pool.get('ir.model.data')
        ir_model_constraint = self.pool.get('ir.model.constraint')
        modules_to_remove = [m.name for m in self.browse(cr, uid, ids, context)]
        constraint_ids = ir_model_constraint.search(cr, uid, [('module', 'in', modules_to_remove)])
        ir_model_constraint._module_data_uninstall(cr, uid, constraint_ids, context)
        ir_model_data._module_data_uninstall(cr, uid, modules_to_remove, context)
        self.write(cr, uid, ids, {'state': 'uninstalled'})
        return True

    def downstream_dependencies(self, cr, uid, ids, known_dep_ids=None,
                                exclude_states=['uninstalled','uninstallable','to remove'],
                                context=None):
        """Return the ids of all modules that directly or indirectly depend
        on the given module `ids`, and that satisfy the `exclude_states`
        filter"""
        if not ids: return []
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
                   (tuple(ids),tuple(exclude_states), tuple(known_dep_ids or ids)))
        new_dep_ids = set([m[0] for m in cr.fetchall()])
        missing_mod_ids = new_dep_ids - known_dep_ids
        known_dep_ids |= new_dep_ids
        if missing_mod_ids:
            known_dep_ids |= set(self.downstream_dependencies(cr, uid, list(missing_mod_ids),
                                                          known_dep_ids, exclude_states,context))
        return list(known_dep_ids)

    def _button_immediate_function(self, cr, uid, ids, function, context=None):
        function(cr, uid, ids, context=context)

        cr.commit()
        _, pool = pooler.restart_pool(cr.dbname, update_module=True)

        config = pool.get('res.config').next(cr, uid, [], context=context) or {}
        if config.get('type') not in ('ir.actions.reload', 'ir.actions.act_window_close'):
            return config

        # reload the client; open the first available root menu
        menu_obj = self.pool.get('ir.ui.menu')
        menu_ids = menu_obj.search(cr, uid, [('parent_id', '=', False)], context=context)

        return {
            'type' : 'ir.actions.client',
            'tag' : 'reload',
            'params' : {'menu_id' : menu_ids and menu_ids[0] or False}
        }

    def button_immediate_uninstall(self, cr, uid, ids, context=None):
        """
        Uninstall the selected module(s) immediately and fully,
        returns the next res.config action to execute
        """
        return self._button_immediate_function(cr, uid, ids, self.button_uninstall, context=context)

    def button_uninstall(self, cr, uid, ids, context=None):
        if any(m.name == 'base' for m in self.browse(cr, uid, ids, context=context)):
            raise orm.except_orm(_('Error'), _("The `base` module cannot be uninstalled"))
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
        todo = self.browse(cr, uid, ids, context=context)
        self.update_list(cr, uid)

        i = 0
        while i<len(todo):
            mod = todo[i]
            i += 1
            if mod.state not in ('installed','to upgrade'):
                raise orm.except_orm(_('Error'),
                        _("Can not upgrade module '%s'. It is not installed.") % (mod.name,))
            self.check_external_dependencies(mod.name, 'to upgrade')
            iids = depobj.search(cr, uid, [('name', '=', mod.name)], context=context)
            for dep in depobj.browse(cr, uid, iids, context=context):
                if dep.module_id.state=='installed' and dep.module_id not in todo:
                    todo.append(dep.module_id)

        ids = map(lambda x: x.id, todo)
        self.write(cr, uid, ids, {'state':'to upgrade'}, context=context)

        to_install = []
        for mod in todo:
            for dep in mod.dependencies_id:
                if dep.state == 'unknown':
                    raise orm.except_orm(_('Error'), _('You try to upgrade a module that depends on the module: %s.\nBut this module is not available in your system.') % (dep.name,))
                if dep.state == 'uninstalled':
                    ids2 = self.search(cr, uid, [('name','=',dep.name)])
                    to_install.extend(ids2)

        self.button_install(cr, uid, to_install, context=context)
        return dict(ACTION_DICT, name=_('Apply Schedule Upgrade'))

    def button_upgrade_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'installed'})
        return True

    def button_update_translations(self, cr, uid, ids, context=None):
        self.update_translations(cr, uid, ids)
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
            'license': terp.get('license', 'AGPL-3'),
            'certificate': terp.get('certificate') or False,
            'sequence': terp.get('sequence', 100),
            'application': terp.get('application', False),
            'auto_install': terp.get('auto_install', False),
            'icon': terp.get('icon', False),
            'summary': terp.get('summary', ''),
        }

    # update the list of available packages
    def update_list(self, cr, uid, context=None):
        res = [0, 0] # [update, add]

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
                    if not old == updated:
                        updated_values[key] = values[key]
                if terp.get('installable', True) and mod.state == 'uninstallable':
                    updated_values['state'] = 'uninstalled'
                if parse_version(terp.get('version', '')) > parse_version(mod.latest_version or ''):
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
        res = []
        for mod in self.browse(cr, uid, ids, context=context):
            if not mod.url:
                continue
            match = re.search('-([a-zA-Z0-9\._-]+)(\.zip)', mod.url, re.I)
            version = '0'
            if match:
                version = match.group(1)
            if parse_version(mod.installed_version or '0') >= parse_version(version):
                continue
            res.append(mod.url)
            if not download:
                continue
            zip_content = urllib.urlopen(mod.url).read()
            fname = modules.get_module_path(str(mod.name)+'.zip', downloaded=True)
            try:
                with open(fname, 'wb') as fp:
                    fp.write(zip_content)
            except Exception:
                _logger.exception('Error when trying to create module '
                                  'file %s', fname)
                raise orm.except_orm(_('Error'), _('Can not create the module file:\n %s') % (fname,))
            terp = self.get_module_info(mod.name)
            self.write(cr, uid, mod.id, self.get_values_from_terp(terp))
            cr.execute('DELETE FROM ir_module_module_dependency ' \
                    'WHERE module_id = %s', (mod.id,))
            self._update_dependencies(cr, uid, mod, terp.get('depends',
                []))
            self._update_category(cr, uid, mod, terp.get('category',
                'Uncategorized'))
            # Import module
            zimp = zipimport.zipimporter(fname)
            zimp.load_module(mod.name)
        return res

    def _update_dependencies(self, cr, uid, mod_browse, depends=None):
        if depends is None:
            depends = []
        existing = set(x.name for x in mod_browse.dependencies_id)
        needed = set(depends)
        for dep in (needed - existing):
            cr.execute('INSERT INTO ir_module_module_dependency (module_id, name) values (%s, %s)', (mod_browse.id, dep))
        for dep in (existing - needed):
            cr.execute('DELETE FROM ir_module_module_dependency WHERE module_id = %s and name = %s', (mod_browse.id, dep))

    def _update_category(self, cr, uid, mod_browse, category='Uncategorized'):
        current_category = mod_browse.category_id
        current_category_path = []
        while current_category:
            current_category_path.insert(0, current_category.name)
            current_category = current_category.parent_id

        categs = category.split('/')
        if categs != current_category_path:
            p_id = None
            while categs:
                if p_id is not None:
                    cr.execute('SELECT id FROM ir_module_category WHERE name=%s AND parent_id=%s', (categs[0], p_id))
                else:
                    cr.execute('SELECT id FROM ir_module_category WHERE name=%s AND parent_id is NULL', (categs[0],))
                c_id = cr.fetchone()
                if not c_id:
                    cr.execute('INSERT INTO ir_module_category (name, parent_id) VALUES (%s, %s) RETURNING id', (categs[0], p_id))
                    c_id = cr.fetchone()[0]
                else:
                    c_id = c_id[0]
                p_id = c_id
                categs = categs[1:]
            self.write(cr, uid, [mod_browse.id], {'category_id': p_id})

    def update_translations(self, cr, uid, ids, filter_lang=None, context=None):
        if context is None:
            context = {}
        if not filter_lang:
            pool = pooler.get_pool(cr.dbname)
            lang_obj = pool.get('res.lang')
            lang_ids = lang_obj.search(cr, uid, [('translatable', '=', True)])
            filter_lang = [lang.code for lang in lang_obj.browse(cr, uid, lang_ids)]
        elif not isinstance(filter_lang, (list, tuple)):
            filter_lang = [filter_lang]

        for mod in self.browse(cr, uid, ids):
            if mod.state != 'installed':
                continue
            modpath = modules.get_module_path(mod.name)
            if not modpath:
                # unable to find the module. we skip
                continue
            for lang in filter_lang:
                iso_lang = tools.get_iso_codes(lang)
                f = modules.get_module_resource(mod.name, 'i18n', iso_lang + '.po')
                context2 = context and context.copy() or {}
                if f and '_' in iso_lang:
                    iso_lang2 = iso_lang.split('_')[0]
                    f2 = modules.get_module_resource(mod.name, 'i18n', iso_lang2 + '.po')
                    if f2:
                        _logger.info('module %s: loading base translation file %s for language %s', mod.name, iso_lang2, lang)
                        tools.trans_load(cr, f2, lang, verbose=False, context=context)
                        context2['overwrite'] = True
                # Implementation notice: we must first search for the full name of
                # the language derivative, like "en_UK", and then the generic,
                # like "en".
                if (not f) and '_' in iso_lang:
                    iso_lang = iso_lang.split('_')[0]
                    f = modules.get_module_resource(mod.name, 'i18n', iso_lang + '.po')
                if f:
                    _logger.info('module %s: loading translation file (%s) for language %s', mod.name, iso_lang, lang)
                    tools.trans_load(cr, f, lang, verbose=False, context=context2)
                elif iso_lang != 'en':
                    _logger.warning('module %s: no translation for language %s', mod.name, iso_lang)

    def check(self, cr, uid, ids, context=None):
        for mod in self.browse(cr, uid, ids, context=context):
            if not mod.description:
                _logger.warning('module %s: description is empty !', mod.name)

            if not mod.certificate or not mod.certificate.isdigit():
                _logger.info('module %s: no quality certificate', mod.name)
            else:
                val = long(mod.certificate[2:]) % 97 == 29
                if not val:
                    _logger.critical('module %s: invalid quality certificate: %s', mod.name, mod.certificate)
                    raise osv.except_osv(_('Error'), _('Module %s: Invalid Quality Certificate') % (mod.name,))

class module_dependency(osv.osv):
    _name = "ir.module.module.dependency"
    _description = "Module dependency"

    def _state(self, cr, uid, ids, name, args, context=None):
        result = {}
        mod_obj = self.pool.get('ir.module.module')
        for md in self.browse(cr, uid, ids):
            ids = mod_obj.search(cr, uid, [('name', '=', md.name)])
            if ids:
                result[md.id] = mod_obj.read(cr, uid, [ids[0]], ['state'])[0]['state']
            else:
                result[md.id] = 'unknown'
        return result

    _columns = {
        # The dependency name
        'name': fields.char('Name',  size=128, select=True),

        # The module that depends on it
        'module_id': fields.many2one('ir.module.module', 'Module', select=True, ondelete='cascade'),

        'state': fields.function(_state, type='selection', selection=[
            ('uninstallable','Uninstallable'),
            ('uninstalled','Not Installed'),
            ('installed','Installed'),
            ('to upgrade','To be upgraded'),
            ('to remove','To be removed'),
            ('to install','To be installed'),
            ('unknown', 'Unknown'),
            ], string='State', readonly=True, select=True),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
