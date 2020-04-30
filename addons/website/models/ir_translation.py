# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class IrTranslation(models.Model):
    _inherit = "ir.translation"

    def load_module_terms(self, modules, langs):
        """ Add missing website specific translation """
        res = super().load_module_terms(modules, langs)

        default_menu = self.env.ref('website.main_menu', raise_if_not_found=False)

        if not default_menu or not langs or not modules:
            return res

        if self.env.context.get('overwrite'):
            conflict_clause = """
                   ON CONFLICT (type, lang, name, res_id) WHERE type = 'model'
                   DO UPDATE SET (name, lang, res_id, src, type, value, module, state, comments) =
                       (EXCLUDED.name, EXCLUDED.lang, EXCLUDED.res_id, EXCLUDED.src, EXCLUDED.type,
                        EXCLUDED.value, EXCLUDED.module, EXCLUDED.state, EXCLUDED.comments)
                WHERE EXCLUDED.value IS NOT NULL AND EXCLUDED.value != ''
            """;
        else:
            conflict_clause = " ON CONFLICT DO NOTHING"

        # Add specific menu translations
        self.env.cr.execute("""
            INSERT INTO ir_translation(name, lang, res_id, src, type, value, module, state, comments)
            SELECT DISTINCT ON (s_menu.id, t.lang) t.name, t.lang, s_menu.id, t.src, t.type, t.value, t.module, t.state, t.comments
              FROM ir_translation t
             INNER JOIN website_menu o_menu
                ON t.type = 'model' AND t.name = 'website.menu,name' AND t.res_id = o_menu.id
             INNER JOIN website_menu s_menu
                ON o_menu.name = s_menu.name AND o_menu.url = s_menu.url
             INNER JOIN website_menu root_menu
                ON s_menu.parent_id = root_menu.id AND root_menu.parent_id IS NULL
             WHERE t.lang IN %s and t.module IN %s
               AND o_menu.website_id IS NULL AND o_menu.parent_id = %s
               AND s_menu.website_id IS NOT NULL""" + conflict_clause,
            (tuple(langs), tuple(modules), default_menu.id))

        return res
