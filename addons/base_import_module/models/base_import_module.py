# -*- coding: utf-8 -*-
import base64
import zipfile
from io import BytesIO
from odoo import fields, models, _
from odoo.exceptions import AccessError, RedirectWarning, UserError
from odoo.modules.module import MANIFEST_NAMES


class BaseImportModule(models.TransientModel):
    """ Import Module """
    _name = "base.import.module"
    _description = "Import Module"

    module_file = fields.Binary(string='Module .ZIP file', required=True, attachment=False)
    state = fields.Selection([('init', 'init'), ('done', 'done')], string='Status', readonly=True, default='init')
    import_message = fields.Text()
    force = fields.Boolean(string='Force init', help="Force init mode even if installed. (will update `noupdate='1'` records)")
    with_demo = fields.Boolean(string='Import demo data of module')
    modules_dependencies = fields.Text()

    def _get_module_names(self, module_file):
        if not self.env.is_admin():
            raise AccessError(_("Only administrators can install data modules."))
        if not module_file:
            raise Exception(_("No file sent."))
        if not zipfile.is_zipfile(module_file):
            raise UserError(_('Only zip files are supported.'))

        module_names = []
        for file in zipfile.ZipFile(module_file, "r").filelist:
            file_dirs = file.filename.split('/')
            if len(file_dirs) == 2 and file_dirs[1] in MANIFEST_NAMES:
                module_names.append(file_dirs[0])
        return module_names

    def import_module(self):
        self.ensure_one()
        IrModule = self.env['ir.module.module']
        zip_data = base64.decodebytes(self.module_file)
        fp = BytesIO()
        fp.write(zip_data)
        module_names = self._get_module_names(fp)
        installed_major_versions = {
            module.id: int(module.installed_version.split('.')[2])
            for module in IrModule.search([('name', 'in', module_names)])
        }
        IrModule._import_zipfile(fp, force=self.force, with_demo=self.with_demo)
        latest_major_versions = {
            module.id: int(module.latest_version.split('.')[2])
            for module in IrModule.search([('name', 'in', module_names)])
        }
        IMPORT_ACTION = {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/odoo',
        }
        if any(installed_major_versions[id] < latest_major_versions[id] for id in installed_major_versions):
            raise RedirectWarning(
                _("A new version is available!\n\nHowever upgrade script is not yet available to upgrade to new version.\nProceeding may break some data in your modules."),
                IMPORT_ACTION,
                _('Upgrade')
            )
        return IMPORT_ACTION

    def get_dependencies_to_install_names(self):
        module_ids, _not_found = self.env['ir.module.module']._get_missing_dependencies_modules(base64.decodebytes(self.module_file))
        return module_ids.mapped('name')

    def action_module_open(self):
        self.ensure_one()
        return {
            'domain': [('name', 'in', self.env.context.get('module_name', []))],
            'name': 'Modules',
            'view_mode': 'list,form',
            'res_model': 'ir.module.module',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
