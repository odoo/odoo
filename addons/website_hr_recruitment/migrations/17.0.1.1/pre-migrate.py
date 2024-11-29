# Part of Odoo. See LICENSE file for full copyright and licensing details.

def migrate(cr, version):
    # Remove the csrf_token and its surrounding div from the
    # website_hr_recruitment.apply (it was set with a t-att- breaking the
    # possibility to properly edit the form, and it was actually useless).
    cr.execute(r"""
        UPDATE ir_ui_view
        SET arch_db = REGEXP_REPLACE(arch_db::text, '<div[^<]*>[^<]*<input[^>]+id=\\"csrf_token\\"[^>]*/>[^<]*</div>', '', 'g')::jsonb
        WHERE key = 'website_hr_recruitment.apply'
        AND website_id IS NOT NULL
        AND arch_db::text LIKE '%csrf_token%'
    """)
