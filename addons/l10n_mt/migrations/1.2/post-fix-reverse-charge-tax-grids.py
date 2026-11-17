# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    taxes = env['account.tax']
    for company in env['res.company'].search([('account_fiscal_country_id.code', '=', 'MT')]):
        for tax_code in ('VAT_P_IN_MT_RC_0_IC_CG', 'VAT_P_IN_MT_RC_0_S_EU'):
            tax = env.ref(f'account.{company.id}_{tax_code}', raise_if_not_found=False)
            if tax:
                taxes |= tax

    if not taxes:
        return

    tags = {
        tag.name: tag.id
        for tag in env['account.account.tag'].search([
            ('name', 'in', ['II.2_base', 'II.2_tax', 'II.3_base', 'II.3_tax']),
            ('country_id.code', '=', 'MT'),
        ])
    }
    tag_pairs = [
        (tags.get('II.2_base'), tags.get('II.3_base')),
        (tags.get('II.2_tax'), tags.get('II.3_tax')),
    ]
    for tag_2, tag_3 in tag_pairs:
        if not tag_2 or not tag_3:
            continue
        cr.execute(
            """
            UPDATE account_account_tag_account_tax_repartition_line_rel rel
               SET account_account_tag_id = CASE rel.account_account_tag_id
                   WHEN %s THEN %s ELSE %s END
              FROM account_tax_repartition_line repartition
             WHERE repartition.id = rel.account_tax_repartition_line_id
               AND repartition.tax_id IN %s
               AND rel.account_account_tag_id IN (%s, %s)
            """,
            [tag_2, tag_3, tag_2, tuple(taxes.ids), tag_2, tag_3],
        )

        cr.execute(
            """
            UPDATE account_account_tag_account_move_line_rel rel
               SET account_account_tag_id = CASE rel.account_account_tag_id
                   WHEN %s THEN %s ELSE %s END
              FROM account_move_line aml
             WHERE aml.id = rel.account_move_line_id
               AND aml.tax_line_id IN %s
               AND rel.account_account_tag_id IN (%s, %s)
            """,
            [tag_2, tag_3, tag_2, tuple(taxes.ids), tag_2, tag_3],
        )
        cr.execute(
            """
            UPDATE account_account_tag_account_move_line_rel rel
               SET account_account_tag_id = CASE rel.account_account_tag_id
                   WHEN %s THEN %s ELSE %s END
              FROM account_move_line_account_tax_rel tax_rel
             WHERE tax_rel.account_move_line_id = rel.account_move_line_id
               AND tax_rel.account_tax_id IN %s
               AND rel.account_account_tag_id IN (%s, %s)
            """,
            [tag_2, tag_3, tag_2, tuple(taxes.ids), tag_2, tag_3],
        )
