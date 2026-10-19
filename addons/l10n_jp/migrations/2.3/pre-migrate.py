# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if not env.ref('l10n_jp.l10n_jp_tax_group_exempt', raise_if_not_found=False):
        cr.execute("""
            UPDATE ir_model_data
              SET name = 'l10n_jp_tax_group_exempt'
            WHERE name = 'tax_group_0'
              AND module = 'l10n_jp'
        """)
    if not env.ref('l10n_jp.l10n_jp_tax_group_8', raise_if_not_found=False):
        cr.execute("""
            UPDATE ir_model_data
            SET name = 'l10n_jp_tax_group_8'
            WHERE name = 'tax_group_8'
            AND module = 'l10n_jp'
        """)
    if not env.ref('l10n_jp.l10n_jp_tax_group_10', raise_if_not_found=False):
        cr.execute("""
            UPDATE ir_model_data
            SET name = 'l10n_jp_tax_group_10'
            WHERE name = 'tax_group_10'
            AND module = 'l10n_jp'
        """)
