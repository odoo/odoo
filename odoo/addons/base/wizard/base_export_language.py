# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import contextlib
import io

from odoo import api, fields, models, tools, _

NEW_LANG_KEY = '__new__'

class BaseLanguageExport(models.TransientModel):
    _name = "base.language.export"
    _description = 'Language Export'

    @api.model
    def _get_languages(self):
        langs = self.env['res.lang'].search([('translatable', '=', True)])
        return [(NEW_LANG_KEY, _('New Language (Empty translation template)'))] + \
               [(lang.code, lang.name) for lang in langs]
   
    name = fields.Char('File Name', readonly=True)
    lang = fields.Selection(_get_languages, string='Language', required=True, default=NEW_LANG_KEY)
    format = fields.Selection([('csv','CSV File'), ('po','PO File'), ('tgz', 'TGZ Archive')],
                              string='File Format', required=True, default='csv')
    modules = fields.Many2many('ir.module.module', 'rel_modules_langexport', 'wiz_id', 'module_id',
                               string='Apps To Export', domain=[('state','=','installed')])
    data = fields.Binary('File', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], # choose language or get the file
                             default='choose')

    @api.multi
    def act_getfile(self):
        this = self[0]
        lang = this.lang if this.lang != NEW_LANG_KEY else False
        mods = sorted(this.mapped('modules.name')) or ['all']

        with contextlib.closing(io.BytesIO()) as buf:
            tools.trans_export(lang, mods, buf, this.format, self._cr)
            out = base64.encodestring(buf.getvalue())

        filename = 'new'
        if lang:
            filename = tools.get_iso_codes(lang)
        elif len(mods) == 1:
            filename = mods[0]
        extension = this.format
        if not lang and extension == 'po':
            extension = 'pot'
        name = "%s.%s" % (filename, extension)
        this.write({'state': 'get', 'data': out, 'name': name})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'base.language.export',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': this.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
