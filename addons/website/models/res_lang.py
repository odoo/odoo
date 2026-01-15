# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, tools, _
from odoo.addons.base.models.res_lang import LangDataDict, LangData
from odoo.exceptions import UserError
from odoo.http import request


class ResLang(models.Model):
    _inherit = "res.lang"

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            if self.env['website'].search_count([('language_ids', 'in', self._ids)], limit=1):
                raise UserError(_("Cannot deactivate a language that is currently used on a website."))
        return super().write(vals)

    @tools.ormcache('self.env.context.get("website_id")', 'self.env.context.get("web_force_installed_langs")')
    def _get_frontend(self) -> LangDataDict:
        """ Return the available languages for current request
        :return: LangDataDict({code: LangData})
        """
        if request and getattr(request, 'is_frontend', True):
            # get languages while ignoring current language as the one in the context may be invalid
            if self.env.context.get('web_force_installed_langs'):
                langs = sorted(map(dict, self._get_active_by('code').values()),
                               key=lambda lang: lang['name'])
            else:
                lang_ids = self.env['website'].get_current_website().with_context(lang=False).language_ids.sorted('name').ids
                langs = [dict(self.env['res.lang']._get_data(id=id_)) for id_ in lang_ids]
            es_419_exists = any(lang['code'] == 'es_419' for lang in langs)
            already_shortened = []
            for lang in langs:
                code = lang['code']
                short_code = code.split('_')[0]
                # Always shorten one language for each group of languages.
                # Special case for spanish, as es_419 is not a valid hreflang
                # and es_419 is actually the new "generic" spanish, when it is
                # in the available languages, it should be the one shortened.
                if (
                    short_code not in already_shortened
                    and not (
                        short_code == 'es'
                        and code != 'es_419'
                        and es_419_exists
                    )
                ):
                    lang['hreflang'] = short_code
                    already_shortened.append(short_code)
                else:
                    lang['hreflang'] = code.lower().replace('_', '-')
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
