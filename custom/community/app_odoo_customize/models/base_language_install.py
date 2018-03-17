# -*- coding: utf-8 -*-
# Copyright 2017 Jarvis (www.odoomod.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _


class BaseLanguageInstall(models.TransientModel):
    _inherit = "base.language.install"

    @api.multi
    def lang_install(self):
        self.ensure_one()
        self.env.cr.execute("""
            delete from ir_translation
            where (name='ir.module.module,shortdesc' 
                    or name='ir.module.module,description' 
                    or name='ir.module.module,summary')
                and lang=%s
            """, (self.lang,))
        return super(BaseLanguageInstall, self).lang_install()
