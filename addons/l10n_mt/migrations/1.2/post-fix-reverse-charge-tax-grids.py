# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, SUPERUSER_ID
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

TAX_GRID_FIXES = {
    'VAT_P_IN_MT_RC_0_S_EU': ('II.3', 'II.2'),
    'VAT_P_IN_MT_RC_0_IC_CG': ('II.2', 'II.3'),
}


def _get_tag(env, country, tag_name):
    tags = env['account.account.tag']._get_tax_tags(tag_name, country.id)
    if len(tags) != 1:
        _logger.warning(
            "l10n_mt migration: expected one tax tag named %r for %s, found %s; skipping it.",
            tag_name, country.code, len(tags),
        )
        return None
    return tags


def _move_repartition_line_tags(cr, tax_ids, repartition_type, old_tag_id, new_tag_id):
    lines_filter = SQL(
        """
        rel.account_tax_repartition_line_id IN (
            SELECT id
              FROM account_tax_repartition_line
             WHERE tax_id IN %s
               AND repartition_type = %s
        )
        """,
        tax_ids, repartition_type,
    )
    cr.execute(SQL(
        """
        UPDATE account_account_tag_account_tax_repartition_line_rel rel
           SET account_account_tag_id = %(new_tag)s
         WHERE rel.account_account_tag_id = %(old_tag)s
           AND %(lines_filter)s
           AND NOT EXISTS (
                SELECT 1
                  FROM account_account_tag_account_tax_repartition_line_rel existing
                 WHERE existing.account_tax_repartition_line_id = rel.account_tax_repartition_line_id
                   AND existing.account_account_tag_id = %(new_tag)s
           )
        """,
        new_tag=new_tag_id, old_tag=old_tag_id, lines_filter=lines_filter,
    ))
    updated = cr.rowcount

    cr.execute(SQL(
        """
        DELETE FROM account_account_tag_account_tax_repartition_line_rel rel
         WHERE rel.account_account_tag_id = %(old_tag)s
           AND %(lines_filter)s
        """,
        old_tag=old_tag_id, lines_filter=lines_filter,
    ))
    return updated, cr.rowcount


def _move_move_line_tags(cr, tax_ids, repartition_type, old_tag_id, new_tag_id):
    if repartition_type == 'base':
        lines_query = SQL(
            """
            SELECT account_move_line_id
              FROM account_move_line_account_tax_rel
             WHERE account_tax_id IN %s
            """,
            tax_ids,
        )
    else:
        lines_query = SQL(
            """
            SELECT aml.id
              FROM account_move_line aml
              JOIN account_tax_repartition_line repartition
                ON repartition.id = aml.tax_repartition_line_id
             WHERE repartition.tax_id IN %s
               AND repartition.repartition_type = 'tax'
            """,
            tax_ids,
        )
    cr.execute(SQL(
        """
        UPDATE account_account_tag_account_move_line_rel rel
           SET account_account_tag_id = %(new_tag)s
         WHERE rel.account_account_tag_id = %(old_tag)s
           AND rel.account_move_line_id IN (%(lines_query)s)
           AND NOT EXISTS (
                SELECT 1
                  FROM account_account_tag_account_move_line_rel existing
                 WHERE existing.account_move_line_id = rel.account_move_line_id
                   AND existing.account_account_tag_id = %(new_tag)s
           )
        """,
        new_tag=new_tag_id, old_tag=old_tag_id, lines_query=lines_query,
    ))
    updated = cr.rowcount

    cr.execute(SQL(
        """
        DELETE FROM account_account_tag_account_move_line_rel rel
         WHERE rel.account_account_tag_id = %(old_tag)s
           AND rel.account_move_line_id IN (%(lines_query)s)
        """,
        old_tag=old_tag_id, lines_query=lines_query,
    ))
    return updated, cr.rowcount


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    country = env.ref('base.mt', raise_if_not_found=False)
    if not country:
        _logger.warning("l10n_mt migration: country 'base.mt' not found; reverse-charge tax grids not fixed.")
        return

    companies = env['res.company'].search([('account_fiscal_country_id', '=', country.id)])
    if not companies:
        return

    for tax_code, (old_grid, new_grid) in TAX_GRID_FIXES.items():
        taxes = env['account.tax']
        for company in companies:
            tax = env.ref(f'account.{company.id}_{tax_code}', raise_if_not_found=False)
            if tax:
                taxes |= tax
            else:
                _logger.warning(
                    "l10n_mt migration: tax %s not found for company %s (id %s); skipping it.",
                    tax_code, company.name, company.id,
                )
        if not taxes:
            continue
        tax_ids = tuple(taxes.ids)

        for repartition_type in ('base', 'tax'):
            old_tag = _get_tag(env, country, f'{old_grid}_{repartition_type}')
            new_tag = _get_tag(env, country, f'{new_grid}_{repartition_type}')
            if not old_tag or not new_tag:
                continue

            rep_updated, rep_deleted = _move_repartition_line_tags(
                cr, tax_ids, repartition_type, old_tag.id, new_tag.id,
            )
            aml_updated, aml_deleted = _move_move_line_tags(
                cr, tax_ids, repartition_type, old_tag.id, new_tag.id,
            )
            _logger.info(
                "l10n_mt migration: %s %s -> %s on taxes %s: "
                "repartition lines updated=%s, duplicates removed=%s; "
                "journal items updated=%s, duplicates removed=%s",
                tax_code, old_tag.name, new_tag.name, list(tax_ids),
                rep_updated, rep_deleted, aml_updated, aml_deleted,
            )
