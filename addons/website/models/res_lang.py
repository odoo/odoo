# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, tools, _
from odoo.addons.base.models.res_lang import LangDataDict, LangData
from odoo.exceptions import UserError
from odoo.http import request


class Lang(models.Model):
    _inherit = "res.lang"

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            if self.env['website'].search_count([('language_ids', 'in', self._ids)], limit=1):
                raise UserError(_("Cannot deactivate a language that is currently used on a website."))
        return super(Lang, self).write(vals)

    @tools.ormcache_context(keys=("website_id",))
    def _get_frontend(self) -> LangDataDict:
        """ Return the available languages for current request
        :return: LangDataDict({code: LangData})
        """
        if request and getattr(request, 'is_frontend', True):
            lang_ids = self.env['website'].get_current_website().language_ids.sorted('name').ids
            ResLang = self.env['res.lang']
            langs = [dict(ResLang._get_data(id=id_)) for id_ in lang_ids]
            # if only one region for a language, use only the language code
            shorts = [lang['code'].split('_')[0] for lang in langs]
            for lang, short in zip(langs, shorts):
                if shorts.count(short) == 1:
                    lang['hreflang'] = short
                else:
                    lang['hreflang'] = lang['code'].lower().replace('_', '-')
            return LangDataDict({lang['code']: LangData(lang) for lang in langs})
        return super()._get_frontend()

    def action_activate_langs(self):
        """
        Open wizard to install language(s), so user can select the website(s)
        to translate in that language.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add languages'),
            'view_mode': 'form',
            'res_model': 'base.language.install',
            'views': [[False, 'form']],
            'target': 'new',
        }
