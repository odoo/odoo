# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import base

from odoo import models
from odoo.addons.base.models.res_lang import LangDataDict


class ResLang(models.Model, base.ResLang):

    def _get_frontend(self) -> LangDataDict:
        """ Return the available languages for current request
        :return: LangDataDict({code: LangData})
        """
        return self._get_active_by('code')
