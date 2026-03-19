import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def _replace_tags_sql(cr, tax_ids, old_tag, new_tag, is_base=False):
    if not tax_ids or not old_tag or not new_tag:
        return 0

    tax_ids_tuple = tuple(tax_ids.ids)

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
              SELECT 1 FROM account_account_tag_account_move_line_rel tag_rel2
              WHERE tag_rel2.account_move_line_id = tag_rel.account_move_line_id
                AND tag_rel2.account_account_tag_id = %(new_tag)s
          )
    """, {
        'new_tag': new_tag.id,
        'old_tag': old_tag.id,
        'tax_ids': tax_ids_tuple
    })
    updated_count = cr.rowcount

    cr.execute(f"""
        DELETE FROM account_account_tag_account_move_line_rel tag_rel
        USING {join_clause}
        WHERE {condition}
          AND tag_rel.account_account_tag_id = %(old_tag)s
    """, {
        'old_tag': old_tag.id,
        'tax_ids': tax_ids_tuple
    })

    return updated_count


def migrate(cr, version):
    """Updates the tax grid in the journal items by assigning the correct tax tags for 7% and 5% Malta sales taxes."""
    env = api.Environment(cr, SUPERUSER_ID, {})

    tax_7 = env['account.tax']
    tax_5 = env['account.tax']

    companies = env['res.company'].search([('account_fiscal_country_id.code', '=', 'MT')])

    for company in companies:
        tax_7 |= env.ref(f'account.{company.id}_VAT_S_IN_MT_7_G', raise_if_not_found=False)
        tax_7 |= env.ref(f'account.{company.id}_VAT_S_IN_MT_7_S', raise_if_not_found=False)
        tax_5 |= env.ref(f'account.{company.id}_VAT_S_IN_MT_5_G', raise_if_not_found=False)
        tax_5 |= env.ref(f'account.{company.id}_VAT_S_IN_MT_5_S', raise_if_not_found=False)

    tag_iii_1_base = env['account.account.tag'].search([('name', '=', 'III.1_base'), ('country_id.code', '=', 'MT')], limit=1)
    tag_iii_1_tax = env['account.account.tag'].search([('name', '=', 'III.1_tax'), ('country_id.code', '=', 'MT')], limit=1)
    tag_iii_2_base = env['account.account.tag'].search([('name', '=', 'III.2_base'), ('country_id.code', '=', 'MT')], limit=1)
    tag_iii_2_tax = env['account.account.tag'].search([('name', '=', 'III.2_tax'), ('country_id.code', '=', 'MT')], limit=1)
    tag_iii_3_base = env['account.account.tag'].search([('name', '=', 'III.3_base'), ('country_id.code', '=', 'MT')], limit=1)
    tag_iii_3_tax = env['account.account.tag'].search([('name', '=', 'III.3_tax'), ('country_id.code', '=', 'MT')], limit=1)

    updated_7_tax = _replace_tags_sql(cr, tax_7, tag_iii_1_tax, tag_iii_2_tax, is_base=False)
    updated_7_base = _replace_tags_sql(cr, tax_7, tag_iii_1_base, tag_iii_2_base, is_base=True)

    updated_5_tax = _replace_tags_sql(cr, tax_5, tag_iii_1_tax, tag_iii_3_tax, is_base=False)
    updated_5_base = _replace_tags_sql(cr, tax_5, tag_iii_1_base, tag_iii_3_base, is_base=True)

    _logger.info('Updated Malta tax grids: 7%% base=%s, 7%% tax=%s, 5%% base=%s, 5%% tax=%s', updated_7_base, updated_7_tax, updated_5_base, updated_5_tax)
