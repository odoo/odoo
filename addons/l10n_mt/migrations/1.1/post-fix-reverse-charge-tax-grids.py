import logging

from odoo import api, SUPERUSER_ID


_logger = logging.getLogger(__name__)


def _replace_tax_grid(cr, tax, old_tag, new_tag, is_base):
    if not tax or not old_tag or not new_tag:
        return 0

    tax_ids = (tax.id,)
    if is_base:
        join_clause = "account_move_line_account_tax_rel tax_rel"
        condition = "tag_rel.account_move_line_id = tax_rel.account_move_line_id AND tax_rel.account_tax_id IN %(tax_ids)s"
    else:
        join_clause = "account_move_line aml"
        condition = "tag_rel.account_move_line_id = aml.id AND aml.tax_line_id IN %(tax_ids)s"

    cr.execute(f"""
        UPDATE account_account_tag_account_move_line_rel tag_rel
           SET account_account_tag_id = %(new_tag)s
          FROM {join_clause}
         WHERE {condition}
           AND tag_rel.account_account_tag_id = %(old_tag)s
           AND NOT EXISTS (
                SELECT 1
                  FROM account_account_tag_account_move_line_rel tag_rel2
                 WHERE tag_rel2.account_move_line_id = tag_rel.account_move_line_id
                   AND tag_rel2.account_account_tag_id = %(new_tag)s
           )
    """, {
        'new_tag': new_tag.id,
        'old_tag': old_tag.id,
        'tax_ids': tax_ids,
    })
    updated_count = cr.rowcount

    cr.execute(f"""
        DELETE FROM account_account_tag_account_move_line_rel tag_rel
         USING {join_clause}
         WHERE {condition}
           AND tag_rel.account_account_tag_id = %(old_tag)s
    """, {
        'old_tag': old_tag.id,
        'tax_ids': tax_ids,
    })

    cr.execute("""
        UPDATE account_account_tag_account_tax_repartition_line_rel rel
           SET account_account_tag_id = %s
          FROM account_tax_repartition_line repartition
         WHERE repartition.id = rel.account_tax_repartition_line_id
           AND repartition.tax_id = %s
           AND rel.account_account_tag_id = %s
           AND NOT EXISTS (
                SELECT 1
                  FROM account_account_tag_account_tax_repartition_line_rel tag_rel2
                 WHERE tag_rel2.account_tax_repartition_line_id = rel.account_tax_repartition_line_id
                   AND tag_rel2.account_account_tag_id = %s
           )
    """, [new_tag.id, tax.id, old_tag.id, new_tag.id])

    cr.execute("""
        DELETE FROM account_account_tag_account_tax_repartition_line_rel rel
         USING account_tax_repartition_line repartition
         WHERE repartition.id = rel.account_tax_repartition_line_id
           AND repartition.tax_id = %s
           AND rel.account_account_tag_id = %s
    """, [tax.id, old_tag.id])

    return updated_count


def migrate(cr, version):
    """Correct the II.2 and II.3 grids on Malta's reverse-charge taxes and existing entries."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env['res.company'].search([('account_fiscal_country_id.code', '=', 'MT')])

    tags = {
        name: env['account.account.tag'].search([('name', '=', name), ('country_id.code', '=', 'MT')], limit=1)
        for name in (
            '+II.2_base', '+II.2_tax', '-II.2_base', '-II.2_tax',
            '+II.3_base', '+II.3_tax', '-II.3_base', '-II.3_tax',
        )
    }

    service_taxes = env['account.tax']
    capital_goods_taxes = env['account.tax']
    for company in companies:
        service_tax = env.ref(f'account.{company.id}_VAT_P_IN_MT_RC_0_S_EU', raise_if_not_found=False)
        capital_goods_tax = env.ref(f'account.{company.id}_VAT_P_IN_MT_RC_0_IC_CG', raise_if_not_found=False)
        if service_tax:
            service_taxes |= service_tax
        if capital_goods_tax:
            capital_goods_taxes |= capital_goods_tax

    updated = {}
    for tax in service_taxes:
        for sign in ('+', '-'):
            updated[tax.id, f'{sign}base'] = _replace_tax_grid(
                cr, tax, tags[f'{sign}II.3_base'], tags[f'{sign}II.2_base'], is_base=True,
            )
            updated[tax.id, f'{sign}tax'] = _replace_tax_grid(
                cr, tax, tags[f'{sign}II.3_tax'], tags[f'{sign}II.2_tax'], is_base=False,
            )
    for tax in capital_goods_taxes:
        for sign in ('+', '-'):
            updated[tax.id, f'{sign}base'] = _replace_tax_grid(
                cr, tax, tags[f'{sign}II.2_base'], tags[f'{sign}II.3_base'], is_base=True,
            )
            updated[tax.id, f'{sign}tax'] = _replace_tax_grid(
                cr, tax, tags[f'{sign}II.2_tax'], tags[f'{sign}II.3_tax'], is_base=False,
            )

    _logger.info('Updated Malta reverse-charge tax grids on existing entries: %s', updated)
