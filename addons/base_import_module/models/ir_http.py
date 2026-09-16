# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models
from odoo.tools import partition

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @api.model
    def _get_translations_for_webclient(self, modules, lang):
        all_imported_modules = self.env['ir.module.module']._get_imported_module_names()
        imported_modules, non_imported_modules = partition(lambda m: m in all_imported_modules, modules)

        translations_per_module, lang_params = super()._get_translations_for_webclient(non_imported_modules, lang)
        for module in imported_modules:
            translations_per_module[module] = self.env['ir.module.module']._get_imported_module_translations_for_webclient(module, lang)
        return translations_per_module, lang_params
