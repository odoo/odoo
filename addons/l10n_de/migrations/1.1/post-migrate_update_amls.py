# Part of Odoo. See LICENSE file for full copyright and licensing details
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    # The tax report line 68 has been removed as it does not appear in tax report anymore.
    # But, it was referenced in the account.sales.report
    # So, we update amls of this line only, to make this report consistent.

    env = api.Environment(cr, SUPERUSER_ID, {})
    country = env['res.country'].search([('code', '=', 'DE')], limit=1)
    tags_68 = env['account.account.tag']._get_tax_tags('68', country.id)
    tags_60 = env.ref('l10n_de.tax_report_de_tag_60').tag_ids

    if tags_68.filtered(lambda tag: tag.tax_negate):
        cr.execute(
            """
            UPDATE account_account_tag_account_move_line_rel
               SET account_account_tag_id = %s
             WHERE account_account_tag_id IN %s;
            """,
            [
                tags_60.filtered(lambda tag: tag.tax_negate)[0].id,
                tuple(tags_68.filtered(lambda tag: tag.tax_negate).ids)
            ]
        )

    if tags_68.filtered(lambda tag: not tag.tax_negate):
        cr.execute(
            """
            UPDATE account_account_tag_account_move_line_rel
               SET account_account_tag_id = %s
             WHERE account_account_tag_id IN %s;
            """,
            [
                tags_60.filtered(lambda tag: not tag.tax_negate)[0].id,
                tuple(tags_68.filtered(lambda tag: not tag.tax_negate).ids)
            ]
        )

    cr.execute(
        r"""
        UPDATE account_move_line
           SET tax_audit = REGEXP_REPLACE(tax_audit, '(?<=(^|\s))68:', '60:')
          FROM (
              SELECT aml.id as aml_id
                FROM account_move_line aml
                JOIN account_account_tag_account_move_line_rel aml_tag_rel ON aml_tag_rel.account_move_line_id = aml.id
               WHERE aml_tag_rel.account_account_tag_id IN %s
               ) aml
         WHERE id = aml.aml_id
        """, [tuple(tags_60.ids)]
    )
