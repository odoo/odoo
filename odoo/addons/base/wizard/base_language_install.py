# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class BaseLanguageInstall(models.TransientModel):
    _name = "base.language.install"
    _description = "Install Language"

    @api.model
    def _default_language(self):
        """ Display the selected language when using the 'Update Terms' action
            from the language list view
        """
        if self._context.get('active_model') == 'res.lang':
            lang = self.env['res.lang'].browse(self._context.get('active_id'))
            return lang.code
        return False

    @api.model
    def _get_languages(self):
        return self.env['res.lang'].get_available()

    lang = fields.Selection(_get_languages, string='Language', required=True,
                            default=_default_language)
    overwrite = fields.Boolean('Overwrite Existing Terms',
                               help="If you check this box, your customized translations will be overwritten and replaced by the official ones.")
    state = fields.Selection([('init', 'init'), ('done', 'done')],
                             string='Status', readonly=True, default='init')

    @api.multi
    def lang_install(self):
        self.ensure_one()
        mods = self.env['ir.module.module'].search([('state', '=', 'installed')])
        mods.with_context(overwrite=self.overwrite)._update_translations(self.lang)
        self.state = 'done'
        self.env.cr.execute('ANALYZE ir_translation')

        return {
            'name': _('Language Pack'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'base.language.install',
            'domain': [],
            'context': dict(self._context, active_ids=self.ids),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
        }

    def reload(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
