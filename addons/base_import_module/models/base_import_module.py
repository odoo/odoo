# -*- coding: utf-8 -*-
import base64
from io import BytesIO
from odoo import api, fields, models


class BaseImportModule(models.TransientModel):
    """ Import Module """
    _name = 'base.import.module'
    _description = "Import Module"

    module_file = fields.Binary(string='Module .ZIP file', required=True, attachment=False)
    state = fields.Selection([('init', 'init'), ('done', 'done')], string='Status', readonly=True, default='init')
    import_message = fields.Text()
    force = fields.Boolean(string='Force init', help="Force init mode even if installed. (will update `noupdate='1'` records)")
    with_demo = fields.Boolean(string='Import demo data of module')
    modules_dependencies = fields.Text()

    def import_module(self):
        self.ensure_one()
        IrModule = self.env['ir.module.module']
        zip_data = base64.decodebytes(self.module_file)
        fp = BytesIO()
        fp.write(zip_data)
        res = IrModule._import_zipfile(fp, force=self.force, with_demo=self.with_demo)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/odoo',
        }

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
