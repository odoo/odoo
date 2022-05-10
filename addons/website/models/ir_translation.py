# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2.extras import Json

from odoo import models

class IrTranslation(models.TransientModel):
    _inherit = "ir.translation"

    def _load_module_terms(self, modules, langs, overwrite=False):
        """ Add missing website specific translation """
        res = super()._load_module_terms(modules, langs, overwrite=overwrite)

        if not langs or langs == ['en_US'] or not modules:
            return res

        # Add specific view translations

        # use the translation dic of the generic to translate the specific
        self.env.cr.flush()
        # TODO CWG: check cache invalidate
        towrite = self.env.all.towrite['ir.ui.view']
        field = self.env['ir.ui.view']._fields['arch_db']
        # assume there are not too many records
        self.env.cr.execute(""" SELECT generic.arch_db, specific.arch_db, specific.id
                      FROM ir_ui_view generic
                     INNER JOIN ir_ui_view specific
                        ON generic.key = specific.key
                     WHERE generic.website_id IS NULL AND generic.type = 'qweb'
                     AND specific.website_id IS NOT NULL
        """)
        for generic_arch_db, specific_arch_db, specific_id in self.env.cr.fetchall():
            if not generic_arch_db:
                continue
            langs_update = (langs & generic_arch_db.keys()) - {'en_US'}
            generic_arch_db_en = generic_arch_db.pop('en_US')
            specific_arch_db_en = specific_arch_db.pop('en_US')
            generic_arch_db = {k: generic_arch_db[k] for k in langs_update}
            # TODO: CWG: use emtpy key-value pair for new languages to speed up installation
            specific_arch_db = {k: specific_arch_db.get(k, specific_arch_db_en) for k in langs_update}
            generic_translation_dictionary = field.get_translation_dictionary(generic_arch_db_en, generic_arch_db)
            specific_translation_dictionary = field.get_translation_dictionary(specific_arch_db_en, specific_arch_db)
            # update specific_translation_dictionary
            for term_en, specific_term_langs in specific_translation_dictionary.items():
                if term_en not in generic_translation_dictionary:
                    continue
                for lang, generic_term_lang in generic_translation_dictionary[term_en].items():
                    if overwrite or term_en == specific_term_langs[lang]:
                        specific_term_langs[lang] = generic_term_lang
            for lang in langs_update:
                specific_arch_db[lang] = field.translate(lambda term: specific_translation_dictionary.get(term, {lang: None})[lang], specific_arch_db_en)
            specific_arch_db['en_US'] = specific_arch_db_en
            towrite[specific_id]['arch_db'] = Json(specific_arch_db)

        default_menu = self.env.ref('website.main_menu', raise_if_not_found=False)
        if not default_menu:
            return res

        o_menu_name = [f"'{lang}', o_menu.name->>'{lang}'" for lang in langs if lang != 'en_US']
        o_menu_name = 'jsonb_build_object(' + ', '.join(o_menu_name) + ')'
        self.env.cr.execute(f"""
                    UPDATE website_menu menu
                       SET name = {'menu.name || ' + o_menu_name  if overwrite else o_menu_name + ' || menu.name'}
                      FROM website_menu o_menu
                     INNER JOIN website_menu s_menu
                        ON o_menu.name->>'en_US' = s_menu.name->>'en_US' AND o_menu.url = s_menu.url
                     INNER JOIN website_menu root_menu
                        ON s_menu.parent_id = root_menu.id AND root_menu.parent_id IS NULL
                     WHERE o_menu.website_id IS NULL AND o_menu.parent_id = %s
                       AND s_menu.website_id IS NOT NULL
                       AND menu.id = s_menu.id
        """, (default_menu.id,))

        return res
