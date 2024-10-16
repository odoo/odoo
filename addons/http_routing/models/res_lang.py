# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.base.models.res_lang import LangDataDict
from odoo.addons import base


class ResLang(base.ResLang):

    def _get_frontend(self) -> LangDataDict:
        """ Return the available languages for current request
        :return: LangDataDict({code: LangData})
        """
        return self._get_active_by('code')
