import ast
import base64
import io
import json
import logging
import lxml
import os
import pathlib
import sys
import traceback
import zipfile
from babel.messages import extract
from collections import defaultdict
from io import BytesIO
from os.path import join as opj

from odoo import api, fields, models, _
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.fields import Domain
from odoo.http import request
from odoo.modules.module import MANIFEST_NAMES, Manifest
from odoo.release import major_version
from odoo.tools import SQL, convert_file
from odoo.tools import file_open, file_path, file_open_temporary_directory, ormcache
from odoo.tools.misc import OrderedSet, topological_sort
from odoo.tools.translate import JAVASCRIPT_TRANSLATION_COMMENT, CodeTranslations, TranslationImporter, get_base_langs

from odoo.addons.base.models.ir_asset import is_wildcard_glob

_logger = logging.getLogger(__name__)

APPS_URL = "https://apps.odoo.com"
MAX_FILE_SIZE = 100 * 1024 * 1024  # in megabytes


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    imported = fields.Boolean(string="Imported Module")
    module_type = fields.Selection([
        ('official', 'Official Apps'),
        ('industries', 'Industries'),
    ], default='official')

    @api.model
    @ormcache(cache='stable')
    def _get_imported_module_names(self):
        return OrderedSet(self.sudo().search_fetch([('imported', '=', True), ('state', '=', 'installed')], ['name']).mapped('name'))

    def _get_modules_to_load_domain(self):
        # imported modules are not expected to be loaded as regular modules
        return super()._get_modules_to_load_domain() + [('imported', '=', False)]

    @api.model
    def _load_module_terms(self, modules, langs, overwrite=False):
        super()._load_module_terms(modules, langs, overwrite=overwrite)

        translation_importer = TranslationImporter(self.env.cr, verbose=False)
        IrAttachment = self.env['ir.attachment']

        for module in modules:
            if Manifest.for_addon(module, display_warning=False):
                continue
            for lang in langs:
                for lang_ in get_base_langs(lang):
                    # Translations for imported data modules only works with imported po files
                    attachment = IrAttachment.sudo().search([
                        ('name', '=', f"{module}_{lang_}.po"),
                        ('url', '=', f"/{module}/i18n/{lang_}.po"),
                        ('type', '=', 'binary'),
                    ], limit=1)
                    if attachment.raw:
                        try:
                            with io.BytesIO(attachment.raw) as fileobj:
                                fileobj.name = attachment.name
                                translation_importer.load(fileobj, 'po', lang, module=module)
                        except Exception:   # noqa: BLE001
                            _logger.warning('module %s: failed to load translation attachment %s for language %s', module, attachment.name, lang)
                if lang != 'en_US' and lang not in translation_importer.imported_langs:
                    _logger.info('module %s: no translation for language %s', module, lang)

        translation_importer.save(overwrite=overwrite)

    @api.depends('name')
    def _get_latest_version(self):
        imported_modules = self.filtered(lambda m: m.imported and m.latest_version)
        for module in imported_modules:
            module.installed_version = module.latest_version
        super(IrModuleModule, self - imported_modules)._get_latest_version()

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

        terp = Manifest._from_path(path, env=self.env)
        if not terp:
            return False
        values = self.get_values_from_terp(terp)
        try:
            icon_path = terp.raw_value('icon') or opj(terp.name, 'static/description/icon.png')
            file_path(icon_path, env=self.env, check_exists=True)
            values['icon'] = '/' + icon_path
        except OSError:
            pass  # keep the default icon
        values['latest_version'] = terp.version
        if self.env.context.get('data_module'):
            values['module_type'] = 'industries'
        if with_demo:
            values['demo'] = True

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

        exclude_list = set()
        base_dir = pathlib.Path(path)
        for pattern in terp.get('cloc_exclude', []):
            exclude_list.update(str(p.relative_to(base_dir)) for p in base_dir.glob(pattern) if p.is_file())

        kind_of_files = ['data', 'init_xml']
        if with_demo:
            kind_of_files.append('demo')
        for kind in kind_of_files:
            for filename in terp.get(kind, []):
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ('.xml', '.csv', '.sql'):
                    _logger.info("module %s: skip unsupported file %s", module, filename)
                    continue
                _logger.info("module %s: loading %s", module, filename)
                noupdate = ext == '.csv' and kind == 'init_xml'
                pathname = opj(path, filename)
                idref = {}
                convert_file(self.env, module, filename, idref, mode, noupdate, pathname=pathname)
                if filename in exclude_list:
                    for xml_id, rec_id in idref.items():
                        name = xml_id.replace('.', '_')
                        if self.env.ref(f"__cloc_exclude__.{name}", raise_if_not_found=False):
                            continue
                        self.env['ir.model.data'].create([{
                            'name': name,
                            'model': self.env['ir.model.data']._xmlid_lookup(xml_id)[0],
                            'module': "__cloc_exclude__",
                            'res_id': rec_id,
                        }])

        path_static = opj(path, 'static')
        IrAttachment = self.env['ir.attachment']
        if os.path.isdir(path_static):
            for root, _dirs, files in os.walk(path_static):
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
                        if str(pathlib.Path(full_path).relative_to(base_dir)) in exclude_list:
                            self.env['ir.model.data'].create({
                                'name': f"cloc_exclude_attachment_{url_path}".replace('.', '_').replace(' ', '_'),
                                'model': 'ir.attachment',
                                'module': "__cloc_exclude__",
                                'res_id': attachment.id,
                            })

        # store translation files as attachments to allow loading translations for webclient
        path_lang = opj(path, 'i18n')
        if os.path.isdir(path_lang):
            for entry in os.scandir(path_lang):
                if not entry.is_file() or not entry.name.endswith('.po'):
                    # we don't support sub-directories in i18n
                    continue
                with file_open(entry.path, 'rb', env=self.env) as fp:
                    raw = fp.read()
                lang = entry.name.split('.')[0]
                # store as binary ir.attachment
                values = {
                    'name': f'{module}_{lang}.po',
                    'url': f'/{module}/i18n/{lang}.po',
                    'res_model': 'ir.module.module',
                    'res_id': mod.id,
                    'type': 'binary',
                    'raw': raw,
                }
                attachment = IrAttachment.sudo().search([('url', '=', values['url']), ('type', '=', 'binary'), ('name', '=', values['name'])])
                if attachment:
                    attachment.write(values)
                else:
                    attachment = IrAttachment.create(values)
                    self.env['ir.model.data'].create({
                        'name': f'attachment_{module}_{lang}'.replace('.', '_').replace(' ', '_'),
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
                if is_wildcard_glob(path):
                    raise UserError(_(
                        "The assets path in the manifest of imported module '%(module_name)s' "
                        "cannot contain glob wildcards (e.g., *, **).", module_name=module))
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

        self.env['ir.module.module']._load_module_terms(
            [module],
            [lang for lang, _name in self.env['res.lang'].get_installed()],
            overwrite=True,
        )

        if ('knowledge.article' in self.env
            and (article_record := self.env.ref(f"{module}.welcome_article", raise_if_not_found=False))
            and article_record._name == 'knowledge.article'
            and self.env.ref(f"{module}.welcome_article_body", raise_if_not_found=False)
        ):
            body = self.env['ir.qweb']._render(f"{module}.welcome_article_body", lang=self.env.user.lang)
            article_record.write({'body': body})

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
            for zf in z.infolist():
                if zf.file_size > MAX_FILE_SIZE:
                    raise UserError(_("File '%s' exceed maximum allowed file size", zf.filename))

            with file_open_temporary_directory(self.env) as module_dir:
                manifest_files = sorted(
                    (file.filename.split('/')[0], file)
                    for file in z.infolist()
                    if file.filename.count('/') == 1
                    and file.filename.split('/')[1] in MANIFEST_NAMES
                )
                module_data_files = defaultdict(list)
                dependencies = defaultdict(list)
                for mod_name, manifest in manifest_files:
                    _manifest_path = z.extract(manifest, module_dir)
                    terp = Manifest._from_path(opj(module_dir, mod_name), env=self.env)
                    if not terp:
                        continue
                    files_to_import = terp.get('data', []) + terp.get('init_xml', []) + terp.get('update_xml', [])
                    if with_demo:
                        files_to_import += terp.get('demo', [])
                    for filename in files_to_import:
                        if os.path.splitext(filename)[1].lower() not in ('.xml', '.csv', '.sql'):
                            continue
                        module_data_files[mod_name].append('%s/%s' % (mod_name, filename))
                    dependencies[mod_name] = terp.get('depends', [])

                dirs = {d for d in os.listdir(module_dir) if os.path.isdir(opj(module_dir, d))}
                sorted_dirs = topological_sort(dependencies)
                if wrong_modules := dirs.difference(sorted_dirs):
                    raise UserError(_(
                        "No manifest found in '%(modules)s'. Can't import the zip file.",
                        modules=", ".join(wrong_modules)
                    ))

                for file in z.infolist():
                    filename = file.filename
                    mod_name = filename.split('/')[0]
                    is_data_file = filename in module_data_files[mod_name]
                    is_static = filename.startswith('%s/static' % mod_name)
                    is_translation = filename.startswith('%s/i18n' % mod_name) and filename.endswith('.po')
                    if is_data_file or is_static or is_translation:
                        z.extract(file, module_dir)

                for mod_name in sorted_dirs:
                    module_names.append(mod_name)
                    try:
                        # assert mod_name.startswith('theme_')
                        path = opj(module_dir, mod_name)
                        self.sudo()._import_module(mod_name, path, force=force, with_demo=with_demo)
                    except Exception as e:
                        raise UserError(_(
                            "Error while importing module '%(module)s'.\n\n %(error_message)s \n\n",
                            module=mod_name, error_message=traceback.format_exc(),
                        )) from e
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
            _logger.info("deleting imported modules upon uninstallation: %s",
                         ", ".join(deleted_modules_names))
            modules_to_delete.unlink()
        return res

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        if _domain_asks_for_industries(domain):
            fields_name = list(specification.keys())
            modules_list = self._get_modules_from_apps(fields_name, 'industries', False, domain, offset=offset)
            return {
                'length': len(modules_list) + offset,
                'records': modules_list[:(limit or 80)],
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
        if module_type == 'industries':
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
        import requests  # noqa: PLC0415
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
        import requests  # noqa: PLC0415
        return requests.post(
                f"{APPS_URL}/loempia/listdatamodules",
                data=payload,
                headers=headers,
                timeout=5.0,
            )

    @api.model
    @ormcache()
    def _get_industry_categories_from_apps(self):
        import requests  # noqa: PLC0415
        try:
            resp = requests.post(
                f"{APPS_URL}/loempia/listindustrycategory/{major_version}",
                json={'params': {}},
                timeout=5.0,
            )
            resp.raise_for_status()
            return resp.json().get('result', [])
        except requests.exceptions.HTTPError:
            return []
        except requests.exceptions.ConnectionError:
            return []

    def button_upgrade(self):
        res = super().button_upgrade()
        # revert states for imported modules since they cannot be upgraded
        self.search([('imported', '=', True), ('state', '=', 'to upgrade')]).state = 'installed'
        return res

    def button_immediate_install_app(self):
        if not self.env.is_admin():
            raise AccessDenied()
        module_name = self.env.context.get('module_name')
        import requests  # noqa: PLC0415
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
            raise UserError(_('Connection to %(url)s failed, the module %(module)s cannot be downloaded.', url=APPS_URL, module=module_name))

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
                for file in z.infolist()
                if file.filename.count('/') == 1
                and file.filename.split('/')[1] in MANIFEST_NAMES
            ]
            modules_in_zip = {manifest.filename.split('/')[0] for manifest in manifest_files}
            for manifest_file in manifest_files:
                if manifest_file.file_size > MAX_FILE_SIZE:
                    raise UserError(_("File '%s' exceed maximum allowed file size", manifest_file.filename))
                try:
                    with z.open(manifest_file) as manifest:
                        terp = ast.literal_eval(manifest.read().decode())
                except Exception:
                    continue
                unmet_dependencies = set(terp.get('depends', [])).difference(installed_mods, modules_in_zip)
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

    @api.model
    @ormcache('module', 'lang', cache='stable')
    def _get_imported_module_translations_for_webclient(self, module, lang):
        if not lang:
            lang = self.env.context.get("lang") or 'en_US'
        IrAttachment = self.env['ir.attachment']

        def filter_func(row):
            return row.get('value') and JAVASCRIPT_TRANSLATION_COMMENT in row['comments']

        translations = {}
        for lang_ in get_base_langs(lang):
            attachment = IrAttachment.sudo().search([
                ('name', '=', f"{module}_{lang_}.po"),
                ('url', '=', f"/{module}/i18n/{lang_}.po"),
                ('res_model', '=', 'ir.module.module'),
                ('res_id', '=', self._get_id(module)),
                ('type', '=', 'binary'),
            ], limit=1)
            if attachment.raw:
                try:
                    with io.BytesIO(attachment.raw) as fileobj:
                        fileobj.name = attachment.name
                        webclient_translations = CodeTranslations._read_code_translations_file(fileobj, filter_func)
                        translations.update(webclient_translations)
                except Exception:  # noqa: BLE001
                    _logger.warning('module %s: failed to load translation attachment %s for language %s', module, attachment.name, lang)

        return {
            'messages': tuple({
                'id': src,
                'string': value,
            } for src, value in translations.items())
        }

    @api.model
    def _extract_resource_attachment_translations(self, module, lang):
        yield from super()._extract_resource_attachment_translations(module, lang)
        if not self._get(module).imported:
            return
        self.env['ir.model.data'].flush_model()
        IrAttachment = self.env['ir.attachment']
        IrAttachment.flush_model()
        module_ = module.replace('_', r'\_')
        ids = [r[0] for r in self.env.execute_query(SQL(
            """
                SELECT ia.id
                FROM ir_attachment ia
                JOIN ir_model_data imd
                ON ia.id = imd.res_id
                AND imd.model = 'ir.attachment'
                AND imd.module = %(module)s
                AND ia.res_model = 'ir.ui.view'
                AND ia.res_field IS NULL
                AND ia.res_id IS NULL
                AND (ia.url ilike %(js_pattern)s or ia.url ilike %(xml_pattern)s)
                AND ia.type = 'binary'
                ORDER BY ia.url
            """,
            module=module,
            js_pattern=f'/{module_}/static/src/%.js',
            xml_pattern=f'/{module_}/static/src/%.xml',
        ))]
        attachments = IrAttachment.browse(OrderedSet(ids))
        if not attachments:
            return
        translations = self._get_imported_module_translations_for_webclient(module, lang)
        translations = {tran['id']: tran['string'] for tran in translations['messages']}
        for attachment in attachments.filtered('raw'):
            display_path = f'addons{attachment.url}'
            if attachment.url.endswith('js'):
                extract_method = 'odoo.tools.babel:extract_javascript'
                extract_keywords = {'_t': None}
            else:
                extract_method = 'odoo.tools.translate:babel_extract_qweb'
                extract_keywords = {}
            try:
                with io.BytesIO(attachment.raw) as fileobj:
                    for extracted in extract.extract(extract_method, fileobj, keywords=extract_keywords):
                        lineno, message, comments = extracted[:3]
                        value = translations.get(message, '')
                        # (module, ttype, name, res_id, source, comments, record_id, value)
                        yield (module, 'code', display_path, lineno, message, comments + [JAVASCRIPT_TRANSLATION_COMMENT], None, value)
            except Exception:  # noqa: BLE001
                _logger.exception("Failed to extract terms from attachment with url %s", attachment.url)


def _domain_asks_for_industries(domain):
    for condition in Domain(domain).iter_conditions():
        if condition.field_expr == 'module_type':
            if condition.operator == '=':
                if condition.value == 'industries':
                    return True
            elif condition.operator == 'in' and len(condition.value) == 1:
                if 'industries' in condition.value:
                    return True
            else:
                raise UserError(f'Unsupported domain condition {condition!r}')  # pylint: disable=missing-gettext
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
