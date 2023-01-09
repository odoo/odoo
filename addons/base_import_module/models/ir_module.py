# -*- coding: utf-8 -*-
import ast
import base64
import logging
import lxml
import os
import sys
import tempfile
import zipfile
from os.path import join as opj

import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.modules.module import load_manifest
from odoo.tools import convert_file, exception_to_unicode

_logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 100 * 1024 * 1024  # in megabytes


class IrModule(models.Model):
    _inherit = "ir.module.module"

    imported = fields.Boolean(string="Imported Module")

    def _get_modules_to_load_domain(self):
        # imported modules are not expected to be loaded as regular modules
        return super()._get_modules_to_load_domain() + [('imported', '=', False)]

    @api.depends('name')
    def _get_latest_version(self):
        imported_modules = self.filtered(lambda m: m.imported and m.latest_version)
        for module in imported_modules:
            module.installed_version = module.latest_version
        super(IrModule, self - imported_modules)._get_latest_version()

    def _import_module(self, module, path, force=False):
        known_mods = self.search([])
        known_mods_names = {m.name: m for m in known_mods}
        installed_mods = [m.name for m in known_mods if m.state == 'installed']

        terp = load_manifest(module, mod_path=path)
        if not terp:
            return False
        values = self.get_values_from_terp(terp)
        if 'version' in terp:
            values['latest_version'] = terp['version']

        unmet_dependencies = set(terp['depends']).difference(installed_mods)

        if unmet_dependencies:
            if (unmet_dependencies == set(['web_studio']) and
                    _is_studio_custom(path)):
                err = _("Studio customizations require Studio")
            else:
                err = _("Unmet module dependencies: \n\n - %s") % '\n - '.join(
                    known_mods.filtered(lambda mod: mod.name in unmet_dependencies).mapped('shortdesc')
                )
            raise UserError(err)
        elif 'web_studio' not in installed_mods and _is_studio_custom(path):
            raise UserError(_("Studio customizations require the Odoo Studio app."))

        mod = known_mods_names.get(module)
        if mod:
            mod.write(dict(state='installed', **values))
            mode = 'update' if not force else 'init'
        else:
            assert terp.get('installable', True), "Module not installable"
            self.create(dict(name=module, state='installed', imported=True, **values))
            mode = 'init'

        for kind in ['data', 'init_xml', 'update_xml']:
            for filename in terp[kind]:
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
                convert_file(self.env.cr, module, filename, idref, mode=mode, noupdate=noupdate, kind=kind, pathname=pathname)

        path_static = opj(path, 'static')
        IrAttachment = self.env['ir.attachment']
        if os.path.isdir(path_static):
            for root, dirs, files in os.walk(path_static):
                for static_file in files:
                    full_path = opj(root, static_file)
                    with open(full_path, 'rb') as fp:
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
                    attachment = IrAttachment.sudo().search([('url', '=', url_path), ('type', '=', 'binary'), ('res_model', '=', 'ir.ui.view')])
                    if attachment:
                        attachment.write(values)
                    else:
                        attachment = IrAttachment.create(values)
                        self.env['ir.model.data'].create({
                            'name': f"attachment_{url_path}".replace('.', '_'),
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

        return True

    @api.model
    def import_zipfile(self, module_file, force=False):
        if not module_file:
            raise Exception(_("No file sent."))
        if not zipfile.is_zipfile(module_file):
            raise UserError(_('Only zip files are supported.'))

        success = []
        errors = dict()
        module_names = []
        with zipfile.ZipFile(module_file, "r") as z:
            for zf in z.filelist:
                if zf.file_size > MAX_FILE_SIZE:
                    raise UserError(_("File '%s' exceed maximum allowed file size", zf.filename))

            with tempfile.TemporaryDirectory() as module_dir:
                import odoo.modules.module as module
                try:
                    odoo.addons.__path__.append(module_dir)
                    z.extractall(module_dir)
                    dirs = [d for d in os.listdir(module_dir) if os.path.isdir(opj(module_dir, d))]
                    for mod_name in dirs:
                        module_names.append(mod_name)
                        try:
                            # assert mod_name.startswith('theme_')
                            path = opj(module_dir, mod_name)
                            if self._import_module(mod_name, path, force=force):
                                success.append(mod_name)
                        except Exception as e:
                            _logger.exception('Error while importing module')
                            errors[mod_name] = exception_to_unicode(e)
                finally:
                    odoo.addons.__path__.remove(module_dir)
        r = ["Successfully imported module '%s'" % mod for mod in success]
        for mod, error in errors.items():
            r.append("Error while importing module '%s'.\n\n %s \n Make sure those modules are installed and try again." % (mod, error))
        return '\n'.join(r), module_names

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
