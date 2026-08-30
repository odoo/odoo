from odoo import api, models
from odoo.tools.misc import frozendict

from odoo.addons.test_translation_mode.tools.translate import contextualize_entry


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _get_debug_modes(self):
        return super()._get_debug_modes() | {'translate'}

    @api.model
    def _get_translations_for_webclient(self, modules, lang):
        translations_per_module, lang_params = super()._get_translations_for_webclient(modules, lang)
        for module, data in translations_per_module.items():
            messages = data.get('messages') or ()
            translations_per_module[module] = frozendict({
                'messages': tuple(
                    frozendict({
                        'id': msg['id'],
                        'string': contextualize_entry({
                            'module': module,
                            'src': msg['id'],
                            'value': msg['string'],
                        })['value'],
                    })
                    for msg in messages
                ),
            })
        return translations_per_module, lang_params
