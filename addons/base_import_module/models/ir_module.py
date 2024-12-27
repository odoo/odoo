# -*- coding: utf-8 -*-
import ast
import base64
import json
import logging
import lxml
import os
import requests
import sys
import zipfile
from collections import defaultdict
from io import BytesIO
from os.path import join as opj

from odoo import api, fields, models, _
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.http import request
from odoo.modules.module import adapt_version, MANIFEST_NAMES
from odoo.osv.expression import is_leaf
from odoo.release import major_version
from odoo.tools import convert_csv_import, convert_sql_import, convert_xml_import, exception_to_unicode
from odoo.tools import file_open, file_open_temporary_directory, ormcache
from odoo.tools.translate import get_po_paths_env, TranslationImporter

_logger = logging.getLogger(__name__)

APPS_URL = "https://apps.odoo.com"
MAX_FILE_SIZE = 100 * 1024 * 1024  # in megabytes


class IrModule(models.Model):
    _inherit = "ir.module.module"

    imported = fields.Boolean(string="Imported Module")
    module_type = fields.Selection([
        ('official', 'Official Apps'),
        ('industries', 'Industries'),
    ], default='official')

    def _get_modules_to_load_domain(self):
        # imported modules are not expected to be loaded as regular modules
        return super()._get_modules_to_load_domain() + [('imported', '=', False)]

    @api.depends('name')
    def _get_latest_version(self):
        imported_modules = self.filtered(lambda m: m.imported and m.latest_version)
        for module in imported_modules:
            module.installed_version = module.latest_version
        super(IrModule, self - imported_modules)._get_latest_version()

    @api.depends('icon')
    def _get_icon_image(self):
        super()._get_icon_image()
        IrAttachment = self.env["ir.attachment"]
        for module in self.filtered('imported'):
            attachment = IrAttachment.sudo().search([
                ('url', '=', module.icon),
                ('type', '=', 'binary'),
                ('res_model', '=', 'ir.ui.view')
            ], limit=1)
            if attachment:
                module.icon_image = attachment.datas

    def _import_module(self, module, path, force=False, with_demo=False):
        # Do not create a bridge module for these neutralizations.
        # Do not involve specific website during import by resetting
        # information used by website's get_current_website.
        self = self.with_context(website_id=None)  # noqa: PLW0642
        force_website_id = None
        if request and request.session.get('force_website_id'):
            force_website_id = request.session.pop('force_website_id')

        known_mods = self.search([])
        known_mods_names = {m.name: m for m in known_mods}
        installed_mods = [m.name for m in known_mods if m.state == 'installed']

        terp = {}
        manifest_path = next((opj(path, name) for name in MANIFEST_NAMES if os.path.exists(opj(path, name))), None)
        if manifest_path:
            with file_open(manifest_path, 'rb', env=self.env) as f:
                terp.update(ast.literal_eval(f.read().decode()))
        if not terp:
            return False
        if not terp.get('icon'):
            icon_path = 'static/description/icon.png'
            module_icon = module if os.path.exists(opj(path, icon_path)) else 'base'
            terp['icon'] = opj('/', module_icon, icon_path)
        values = self.get_values_from_terp(terp)
        if 'version' in terp:
            values['latest_version'] = adapt_version(terp['version'])
        if self.env.context.get('data_module'):
            values['module_type'] = 'industries'

        unmet_dependencies = set(terp.get('depends', [])).difference(installed_mods)

        if unmet_dependencies:
            wrong_dependencies = unmet_dependencies.difference(known_mods.mapped("name"))
            if wrong_dependencies:
                err = _("Unknown module dependencies:") + "\n - " + "\n - ".join(wrong_dependencies)
                raise UserError(err)
            to_install = known_mods.filtered(lambda mod: mod.name in unmet_dependencies)
            to_install.button_immediate_install()
        elif 'web_studio' not in installed_mods and _is_studio_custom(path):
            raise UserError(_("Studio customizations require the Odoo Studio app."))

        mod = known_mods_names.get(module)
        if mod:
            mod.write(dict(state='installed', **values))
            mode = 'update' if not force else 'init'
        else:
            assert terp.get('installable', True), "Module not installable"
            mod = self.create(dict(name=module, state='installed', imported=True, **values))
            mode = 'init'

        kind_of_files = ['data', 'init_xml', 'update_xml']
        if with_demo:
            kind_of_files.append('demo')
        for kind in kind_of_files:
            for filename in terp.get(kind, []):
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ('.xml', '.csv', '.sql'):
                    _logger.info("module %s: skip unsupported file %s", module, filename)
                    continue
                _logger.info("module %s: loading %s", module, filename)
                noupdate = False
                if ext == '.csv' and kind in ('init', 'init_xml'):
                    noupdate = True
                pathname = opj(path, filename)
                idref = {}
                with file_open(pathname, 'rb', env=self.env) as fp:
                    if ext == '.csv':
                        convert_csv_import(self.env, module, pathname, fp.read(), idref, mode, noupdate)
                    elif ext == '.sql':
                        convert_sql_import(self.env, fp)
                    elif ext == '.xml':
                        convert_xml_import(self.env, module, fp, idref, mode, noupdate)

        path_static = opj(path, 'static')
        IrAttachment = self.env['ir.attachment']
        if os.path.isdir(path_static):
            for root, dirs, files in os.walk(path_static):
                for static_file in files:
                    full_path = opj(root, static_file)
                    with file_open(full_path, 'rb', env=self.env) as fp:
                        data = base64.b64encode(fp.read())
                    url_path = '/{}{}'.format(module, full_path.split(path)[1].replace(os.path.sep, '/'))
                    if not isinstance(url_path, str):
                        url_path = url_path.decode(sys.getfilesystemencoding())
                    filename = os.path.split(url_path)[1]
                    values = dict(
                        name=filename,
                        url=url_path,
                        res_model='ir.ui.view',
                        type='binary',
                        datas=data,
                    )
                    # Do not create a bridge module for this check.
                    if 'public' in IrAttachment._fields:
                        # Static data is public and not website-specific.
                        values['public'] = True
                    attachment = IrAttachment.sudo().search([('url', '=', url_path), ('type', '=', 'binary'), ('res_model', '=', 'ir.ui.view')])
                    if attachment:
                        attachment.write(values)
                    else:
                        attachment = IrAttachment.create(values)
                        self.env['ir.model.data'].create({
                            'name': f"attachment_{url_path}".replace('.', '_').replace(' ', '_'),
                            'model': 'ir.attachment',
                            'module': module,
                            'res_id': attachment.id,
                        })

        IrAsset = self.env['ir.asset']
        assets_vals = []

        # Generate 'ir.asset' record values for each asset delared in the manifest
        for bundle, commands in terp.get('assets', {}).items():
            for command in commands:
                directive, target, path = IrAsset._process_command(command)
                path = path if path.startswith('/') else '/' + path # Ensures a '/' at the start
                assets_vals.append({
                    'name': f'{module}.{bundle}.{path}',
                    'directive': directive,
                    'target': target,
                    'path': path,
                    'bundle': bundle,
                })

        # Look for existing assets
        existing_assets = {
            asset.name: asset
            for asset in IrAsset.search([('name', 'in', [vals['name'] for vals in assets_vals])])
        }
        assets_to_create = []

        # Update existing assets and generate the list of new assets values
        for values in assets_vals:
            if values['name'] in existing_assets:
                existing_assets[values['name']].write(values)
            else:
                assets_to_create.append(values)

        # Create new assets and attach 'ir.model.data' records to them
        created_assets = IrAsset.create(assets_to_create)
        self.env['ir.model.data'].create([{
            'name': f"{asset['bundle']}_{asset['path']}".replace(".", "_"),
            'model': 'ir.asset',
            'module': module,
            'res_id': asset.id,
        } for asset in created_assets])

        translation_importer = TranslationImporter(self.env.cr, verbose=False)
        for lang_ in self.env['res.lang'].get_installed():
            lang = lang_[0]
            is_lang_imported = False
            for po_path in get_po_paths_env(module, lang, env=self.env):
                translation_importer.load_file(po_path, lang)
                is_lang_imported = True
            if lang != 'en_US' and not is_lang_imported:
                _logger.info('module %s: no translation for language %s', module, lang)
        translation_importer.save(overwrite=True)

        mod._update_from_terp(terp)
        _logger.info("Successfully imported module '%s'", module)

        if force_website_id:
            # Restore neutralized website_id.
            request.session['force_website_id'] = force_website_id

        return True

    @api.model
    def _import_zipfile(self, module_file, force=False, with_demo=False):
        if not self.env.is_admin():
            raise AccessError(_("Only administrators can install data modules."))
        if not module_file:
            raise Exception(_("No file sent."))
        if not zipfile.is_zipfile(module_file):
            raise UserError(_('Only zip files are supported.'))

        module_names = []
        with zipfile.ZipFile(module_file, "r") as z:
            for zf in z.filelist:
                if zf.file_size > MAX_FILE_SIZE:
                    raise UserError(_("File '%s' exceed maximum allowed file size", zf.filename))

            with file_open_temporary_directory(self.env) as module_dir:
                manifest_files = [
                    file
                    for file in z.filelist
                    if file.filename.count('/') == 1
                    and file.filename.split('/')[1] in MANIFEST_NAMES
                ]
                module_data_files = defaultdict(list)
                for manifest in manifest_files:
                    manifest_path = z.extract(manifest, module_dir)
                    mod_name = manifest.filename.split('/')[0]
                    try:
                        with file_open(manifest_path, 'rb', env=self.env) as f:
                            terp = ast.literal_eval(f.read().decode())
                    except Exception:
                        continue
                    files_to_import = terp.get('data', []) + terp.get('init_xml', []) + terp.get('update_xml', [])
                    if with_demo:
                        files_to_import += terp.get('demo', [])
                    for filename in files_to_import:
                        if os.path.splitext(filename)[1].lower() not in ('.xml', '.csv', '.sql'):
                            continue
                        module_data_files[mod_name].append('%s/%s' % (mod_name, filename))
                for file in z.filelist:
                    filename = file.filename
                    mod_name = filename.split('/')[0]
                    is_data_file = filename in module_data_files[mod_name]
                    is_static = filename.startswith('%s/static' % mod_name)
                    is_translation = filename.startswith('%s/i18n' % mod_name) and filename.endswith('.po')
                    if is_data_file or is_static or is_translation:
                        z.extract(file, module_dir)

                dirs = [d for d in os.listdir(module_dir) if os.path.isdir(opj(module_dir, d))]
                for mod_name in dirs:
                    module_names.append(mod_name)
                    try:
                        # assert mod_name.startswith('theme_')
                        path = opj(module_dir, mod_name)
                        self.sudo()._import_module(mod_name, path, force=force, with_demo=with_demo)
                    except Exception as e:
                        raise UserError(_(
                            "Error while importing module '%(module)s'.\n\n %(error_message)s \n\n",
                            module=mod_name, error_message=exception_to_unicode(e),
                        ))
        return "", module_names

    def module_uninstall(self):
        # Delete an ir_module_module record completely if it was an imported
        # one. The rationale behind this is that an imported module *cannot* be
        # reinstalled anyway, as it requires the data files. Any attempt to
        # install it again will simply fail without trace.
        # /!\ modules_to_delete must be calculated before calling super().module_uninstall(),
        # because when uninstalling `base_import_module` the `imported` column will no longer be
        # in the database but we'll still have an old registry that runs this code.
        modules_to_delete = self.filtered('imported')
        res = super().module_uninstall()
        if modules_to_delete:
            deleted_modules_names = modules_to_delete.mapped('name')
            assets_data = self.env['ir.model.data'].search([
                ('model', '=', 'ir.asset'),
                ('module', 'in', deleted_modules_names),
            ])
            assets = self.env['ir.asset'].search([('id', 'in', assets_data.mapped('res_id'))])
            assets.unlink()
            _logger.info("deleting imported modules upon uninstallation: %s",
                         ", ".join(deleted_modules_names))
            modules_to_delete.unlink()
        return res

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        if _domain_asks_for_industries(domain):
            fields_name = list(specification.keys())
            modules_list = self._get_modules_from_apps(fields_name, 'industries', False, domain, offset=offset, limit=limit)
            return {
                'length': len(modules_list),
                'records': modules_list,
            }
        else:
            return super().web_search_read(domain, specification, offset=offset, limit=limit, order=order, count_limit=count_limit)

    def more_info(self):
        return {
            'name': _('Apps'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.module.module',
            'view_mode': 'form',
            'res_id': self.id,
            'context': self.env.context,
        }

    def web_read(self, specification):
        fields = list(specification.keys())
        module_type = self.env.context.get('module_type', 'official')
        if module_type != 'official':
            modules_list = self._get_modules_from_apps(fields, module_type, self.env.context.get('module_name'))
            return modules_list
        else:
            return super().web_read(specification)

    @api.model
    def _get_modules_from_apps(self, fields, module_type, module_name, domain=None, limit=None, offset=None):
        if 'name' not in fields:
            fields = fields + ['name']
        payload = {
            'params': {
                'series': major_version,
                'module_fields': fields,
                'module_type': module_type,
                'module_name': module_name,
                'domain': domain,
                'limit': limit,
                'offset': offset,
            }
        }
        try:
            resp = self._call_apps(json.dumps(payload))
            resp.raise_for_status()
            modules_list = resp.json().get('result', [])
            for mod in modules_list:
                module_name = mod['name']
                existing_mod = self.search([('name', '=', module_name), ('state', '=', 'installed')])
                mod['id'] = existing_mod.id if existing_mod else -1
                if 'icon' in fields:
                    mod['icon'] = f"{APPS_URL}{mod['icon']}"
                if 'state' in fields:
                    if existing_mod:
                        mod['state'] = 'installed'
                    else:
                        mod['state'] = 'uninstalled'
                if 'module_type' in fields:
                    mod['module_type'] = module_type
                if 'website' in fields:
                    mod['website'] = f"{APPS_URL}/apps/modules/{major_version}/{module_name}/"
            return modules_list
        except requests.exceptions.HTTPError:
            raise UserError(_('The list of industry applications cannot be fetched. Please try again later'))
        except requests.exceptions.ConnectionError:
            raise UserError(_('Connection to %s failed The list of industry modules cannot be fetched') % APPS_URL)

    @api.model
    @ormcache('payload')
    def _call_apps(self, payload):
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        return requests.post(
                f"{APPS_URL}/loempia/listdatamodules",
                data=payload,
                headers=headers,
                timeout=5.0,
            )

    @api.model
    @ormcache()
    def _get_industry_categories_from_apps(self):
        try:
            resp = requests.post(
                f"{APPS_URL}/loempia/listindustrycategory",
                json={'params': {}},
                timeout=5.0,
            )
            resp.raise_for_status()
            return resp.json().get('result', [])
        except requests.exceptions.HTTPError:
            return []
        except requests.exceptions.ConnectionError:
            return []

    def button_immediate_install_app(self):
        if not self.env.is_admin():
            raise AccessDenied()
        module_name = self.env.context.get('module_name')
        try:
            resp = requests.get(
                f"{APPS_URL}/loempia/download/data_app/{module_name}/{major_version}",
                timeout=5.0,
            )
            resp.raise_for_status()
            missing_dependencies_description, unavailable_modules = self._get_missing_dependencies(resp.content)
            if unavailable_modules:
                raise UserError(missing_dependencies_description)
            import_module = self.env['base.import.module'].create({
                'module_file': base64.b64encode(resp.content),
                'state': 'init',
                'modules_dependencies': missing_dependencies_description,
            })
            return {
                'name': _("Install an Industry"),
                'view_mode': 'form',
                'target': 'new',
                'res_id': import_module.id,
                'res_model': 'base.import.module',
                'type': 'ir.actions.act_window',
                'context': {'data_module': True}
            }
        except requests.exceptions.HTTPError:
            raise UserError(_('The module %s cannot be downloaded') % module_name)
        except requests.exceptions.ConnectionError:
            raise UserError(_('Connection to %s failed, the module %s cannot be downloaded.', APPS_URL, module_name))

    @api.model
    def _get_missing_dependencies(self, zip_data):
        _modules, unavailable_modules = self._get_missing_dependencies_modules(zip_data)
        description = ''
        if unavailable_modules:
            description = _(
                "The installation of the data module would fail as the following dependencies can't"
                " be found in the addons-path:\n"
            )
            for module in unavailable_modules:
                description += "- " + module + "\n"
            description += _(
                "\nYou may need the Enterprise version to install the data module. Please visit "
                "https://www.odoo.com/pricing-plan for more information.\n"
                "If you need Website themes, it can be downloaded from https://github.com/odoo/design-themes.\n"
            )
        else:
            description = _(
                "Load demo data to test the industry's features with sample records. "
                "Do not load them if this is your production database.",
            )
        return description, unavailable_modules

    def _get_missing_dependencies_modules(self, zip_data):
        dependencies_to_install = self.env['ir.module.module']
        known_mods = self.search([('to_buy', '=', False)])
        installed_mods = [m.name for m in known_mods if m.state == 'installed']
        not_found_modules = set()
        with zipfile.ZipFile(BytesIO(zip_data), "r") as z:
            manifest_files = [
                file
                for file in z.filelist
                if file.filename.count('/') == 1
                and file.filename.split('/')[1] in MANIFEST_NAMES
            ]
            for manifest_file in manifest_files:
                if manifest_file.file_size > MAX_FILE_SIZE:
                    raise UserError(_("File '%s' exceed maximum allowed file size", manifest_file.filename))
                try:
                    with z.open(manifest_file) as manifest:
                        terp = ast.literal_eval(manifest.read().decode())
                except Exception:
                    continue
                unmet_dependencies = set(terp.get('depends', [])).difference(installed_mods)
                dependencies_to_install |= known_mods.filtered(lambda m: m.name in unmet_dependencies)
                not_found_modules |= set(
                    mod for mod in unmet_dependencies if mod not in dependencies_to_install.mapped('name')
                )
        return dependencies_to_install, not_found_modules

    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        if field_name == 'category_id' and _domain_asks_for_industries(kwargs.get('category_domain', [])):
            categories = self._get_industry_categories_from_apps()
            return {
                'parent_field': 'parent_id',
                'values': categories,
            }
        return super().search_panel_select_range(field_name, **kwargs)


def _domain_asks_for_industries(domain):
    for dom in domain:
        if is_leaf(dom) and dom[0] == 'module_type':
            if dom[2] == 'industries':
                if dom[1] != '=':
                    raise UserError('%r is an unsupported leaf' % (dom,))
                return True
    return False


def _is_studio_custom(path):
    """
    Checks the to-be-imported records to see if there are any references to
    studio, which would mean that the module was created using studio

    Returns True if any of the records contains a context with the key
    studio in it, False if none of the records do
    """
    filepaths = []
    for level in os.walk(path):
        filepaths += [os.path.join(level[0], fn) for fn in level[2]]
    filepaths = [fp for fp in filepaths if fp.lower().endswith('.xml')]

    for fp in filepaths:
        root = lxml.etree.parse(fp).getroot()

        for record in root:
            # there might not be a context if it's a non-studio module
            try:
                # ast.literal_eval is like eval(), but safer
                # context is a string representing a python dict
                ctx = ast.literal_eval(record.get('context'))
                # there are no cases in which studio is false
                # so just checking for its existence is enough
                if ctx and ctx.get('studio'):
                    return True
            except Exception:
                continue
    return False
