# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID
from psycopg2 import sql


def _get_tax_ids_for_xml_id(cr, xml_id):
    cr.execute(sql.SQL(
        """
        SELECT res_id
        FROM ir_model_data
        WHERE model = 'account.tax'
        AND name LIKE '%' || {xml_id}
        """
    ).format(xml_id=sql.Literal(xml_id)))

    return [line['res_id'] for line in cr.dictfetchall()]


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    goods_taxes = env['account.tax'].browse(_get_tax_ids_for_xml_id(cr, 'btw_X0_producten'))
    services_taxes = env['account.tax'].browse(_get_tax_ids_for_xml_id(cr, 'btw_X0_diensten'))

    old_tax_tags = env['account.account.tag']._get_tax_tags('3bl (omzet)', 'nl')
    if not old_tax_tags:
        return

    goods_tax_tags = env['account.account.tag']._get_tax_tags('3bg (omzet)', 'nl')
    services_tax_tags = env['account.account.tag']._get_tax_tags('3bs (omzet)', 'nl')

    old_plus_tax_tag_id = old_tax_tags.filtered(lambda tag: not tag.tax_negate).id
    old_minus_tax_tag_id = old_tax_tags.filtered(lambda tag: tag.tax_negate).id
    goods_plus_tax_tag_id = goods_tax_tags.filtered(lambda tag: not tag.tax_negate).id
    goods_minus_tax_tag_id = goods_tax_tags.filtered(lambda tag: tag.tax_negate).id
    services_plus_tax_tag_id = services_tax_tags.filtered(lambda tag: not tag.tax_negate).id
    services_minus_tax_tag_id = services_tax_tags.filtered(lambda tag: tag.tax_negate).id

    insert_query_params = [
        (goods_plus_tax_tag_id, goods_taxes.ids, old_plus_tax_tag_id, goods_taxes.invoice_repartition_line_ids.ids),
        (services_plus_tax_tag_id, services_taxes.ids, old_plus_tax_tag_id, services_taxes.invoice_repartition_line_ids.ids),
        (goods_minus_tax_tag_id, goods_taxes.ids, old_minus_tax_tag_id, goods_taxes.refund_repartition_line_ids.ids),
        (services_minus_tax_tag_id, services_taxes.ids, old_minus_tax_tag_id, services_taxes.refund_repartition_line_ids.ids),
    ]
    insert_query_parts = []

    for new_tax_tag_id, tax_ids, old_tax_tag_id, repartition_line_ids in insert_query_params:
        insert_query_parts.append(
            sql.SQL("""
                SELECT tag_aml_rel.account_move_line_id, {new_tax_tag_id}
                FROM account_account_tag_account_move_line_rel tag_aml_rel
                JOIN account_move_line_account_tax_rel aml_at_rel ON aml_at_rel.account_move_line_id = tag_aml_rel.account_move_line_id
                WHERE aml_at_rel.account_tax_id = ANY({tax_ids})
                AND tag_aml_rel.account_account_tag_id = {old_tax_tag_id}
            """).format(
                new_tax_tag_id=sql.Literal(new_tax_tag_id),
                tax_ids=sql.Literal(tax_ids),
                old_tax_tag_id=sql.Literal(old_tax_tag_id),
            )
        )

        cr.execute(
            sql.SQL("""
                UPDATE account_account_tag_account_tax_repartition_line_rel
                SET account_account_tag_id = {new_tax_tag_id}
                WHERE account_tax_repartition_line_id = ANY({repartition_line_ids})
                AND account_account_tag_id = {old_tax_tag_id}
            """).format(
                new_tax_tag_id=sql.Literal(new_tax_tag_id),
                repartition_line_ids=sql.Literal(repartition_line_ids),
                old_tax_tag_id=sql.Literal(old_tax_tag_id),
            )
        )

    cr.execute(
        sql.SQL("""
            INSERT INTO account_account_tag_account_move_line_rel (account_move_line_id, account_account_tag_id)
                {select_statement}
            ON CONFLICT DO NOTHING
        """).format(
            select_statement=sql.SQL(" UNION ").join(insert_query_parts),
        )
    )
