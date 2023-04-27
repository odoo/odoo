# -*- coding: utf-8 -*-
import base64
from io import BytesIO
from odoo import api, fields, models


class BaseImportModule(models.TransientModel):
    """ Import Module """
    _name = "base.import.module"
    _description = "Import Module"

    module_file = fields.Binary(string='Module .ZIP file', required=True, attachment=False)
    state = fields.Selection([('init', 'init'), ('done', 'done')], string='Status', readonly=True, default='init')
    import_message = fields.Text()
    force = fields.Boolean(string='Force init', help="Force init mode even if installed. (will update `noupdate='1'` records)")

    def import_module(self):
        self.ensure_one()
        IrModule = self.env['ir.module.module']
        zip_data = base64.decodebytes(self.module_file)
        fp = BytesIO()
        fp.write(zip_data)
        res = IrModule.import_zipfile(fp, force=self.force)
        self.write({'state': 'done', 'import_message': res[0]})
        context = dict(self.env.context, module_name=res[1])
        # Return wizard otherwise it will close wizard and will not show result message to user.
        return {
            'name': 'Import Module',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
            'res_model': 'base.import.module',
            'type': 'ir.actions.act_window',
            'context': context,
        }

    def action_module_open(self):
        self.ensure_one()
        return {
            'domain': [('name', 'in', self.env.context.get('module_name', []))],
            'name': 'Modules',
            'view_mode': 'tree,form',
            'res_model': 'ir.module.module',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
