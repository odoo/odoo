# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _


class BaseLanguageInstall(models.TransientModel):
    _inherit = "base.language.install"

    def lang_install(self):
        self.ensure_one()
        if self.overwrite:
            self.env.cr.execute("""
                delete from ir_translation
                where lang=%s
                """, (self.lang,))
            self.env.cr.commit()
        return super(BaseLanguageInstall, self).lang_install()
