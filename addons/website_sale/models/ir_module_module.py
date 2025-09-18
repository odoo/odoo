# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from itertools import batched

from odoo.tools import SQL


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    @api.model
    def _load_module_terms(self, modules, langs, overwrite=False):
        # Add missing website_sale-specific translations

        super()._load_module_terms(modules, langs, overwrite=overwrite)

        to_langs = [lang for lang in langs if lang != 'en_US']
        if not (to_langs and modules):
            return  # nothing to translate

        def set_field(fname):
            lang_items = (
                # lang must be a SQL literal (not a bound parameter) because
                # psycopg3 can't infer the type for jsonb->>$N operators.
                SQL('%(lang)s, o_step.%(fname)s->>%(lang)s', lang=SQL("'%s'" % lang), fname=fname)  # pylint: disable=E8501
                for lang in to_langs
            )
            # PSQL functions take 100 args max, and we're generating 2 per lang
            batched_lang_items = batched(lang_items, 50)
            update_jsonb = SQL(' || ').join(
                SQL('jsonb_build_object(%s)', SQL(', ').join(batch))
                for batch in batched_lang_items
            )
            ordered = reversed if overwrite else iter
            src = SQL(' || ').join(ordered([
                SQL('jsonb_strip_nulls(%s)', update_jsonb),  # gets updated translation
                SQL('jsonb_strip_nulls(step.%s)', fname),  # keeps current translation
            ]))
            return SQL('%(fname)s = %(src)s', fname=fname, src=src)

        WebsiteCheckoutStep = self.env['website.checkout.step']
        to_translate = [
            SQL.identifier(field.name)
            for field in WebsiteCheckoutStep._fields.values()
            if field.translate is True  # more correct in case of `callable(field.translate)`
        ]
        set_fields = SQL(', ').join(set_field(fname) for fname in to_translate)

        WebsiteCheckoutStep.invalidate_model()
        self.env.cr.execute(SQL(
            '''
            UPDATE website_checkout_step step
               SET %(set_fields)s
              FROM website_checkout_step o_step
              JOIN website_checkout_step s_step
                ON o_step.step_href = s_step.step_href
             WHERE o_step.website_id IS NULL
               AND s_step.website_id IS NOT NULL
               AND step.id = s_step.id
            ''',
            set_fields=set_fields,
        ))
