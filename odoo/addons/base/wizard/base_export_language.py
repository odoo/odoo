# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import base64
import io

from odoo import api, fields, models, tools
from odoo.tools.translate import trans_export, trans_export_records

NEW_LANG_KEY = '__new__'


class BaseLanguageExport(models.TransientModel):
    _name = 'base.language.export'
    _description = 'Language Export'

    @api.model
    def _get_languages(self):
        langs = self.env['res.lang'].get_installed()
        return [(NEW_LANG_KEY, self.env._('New Language (Empty translation template)'))] + \
               langs

    name = fields.Char('File Name', readonly=True)
    lang = fields.Selection(_get_languages, string='Language', required=True, default=NEW_LANG_KEY)
    format = fields.Selection([('csv','CSV File'), ('po','PO File'), ('tgz', 'TGZ Archive')],
                              string='File Format', required=True, default='po')
    export_type = fields.Selection([('module', 'Module'), ('model', 'Model')],
                                   string='Export Type', required=True, default='module')
    modules = fields.Many2many('ir.module.module', 'rel_modules_langexport', 'wiz_id', 'module_id',
                               string='Apps To Export', domain=[('state','=','installed')])
    model_id = fields.Many2one('ir.model', string='Model to Export', domain=[('transient', '=', False)])
    model_name = fields.Char(string="Model Name", related="model_id.model")
    domain = fields.Char(string="Model Domain", default='[]')
    data = fields.Binary('File', readonly=True, attachment=False)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],  # choose language or get the file
                             default='choose')

    def act_getfile(self):
        self.ensure_one()
        lang = self.lang if self.lang != NEW_LANG_KEY else False

        with io.BytesIO() as buf:
            if self.export_type == 'model':
                ids = self.env[self.model_name].search(ast.literal_eval(self.domain)).ids
                is_exported = trans_export_records(lang, self.model_name, ids, buf, self.format, self.env)
            else:
                mods = sorted(self.mapped('modules.name')) or ['all']
                is_exported = trans_export(lang, mods, buf, self.format, self.env)
            out = is_exported and base64.encodebytes(buf.getvalue())

        filename = 'new'
        if lang:
            filename = tools.get_iso_codes(lang)
        elif self.export_type == 'model':
            filename = self.model_name.replace('.', '_')
        elif len(mods) == 1:
            filename = mods[0]
        extension = self.format
        if not lang and extension == 'po':
            extension = 'pot'
        name = "%s.%s" % (filename, extension)

        self.write({'state': 'get', 'data': out, 'name': name})
        return {
            'name': self.env.ref('base.action_wizard_lang_export').name,
            'type': 'ir.actions.act_window',
            'res_model': 'base.language.export',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
