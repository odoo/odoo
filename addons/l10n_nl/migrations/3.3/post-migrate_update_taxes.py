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

    old_3bl_tax_tags = env['account.account.tag']._get_tax_tags('3bl (omzet)', 'nl')
    old_3b_tax_tags = env['account.account.tag']._get_tax_tags('3b (omzet)', 'nl')
    if not old_3bl_tax_tags and not old_3b_tax_tags:
        return

    goods_tax_tags = env['account.account.tag']._get_tax_tags('3bg (omzet)', 'nl')
    services_tax_tags = env['account.account.tag']._get_tax_tags('3bs (omzet)', 'nl')

    old_3bl_tax_tags_plus = old_3bl_tax_tags.filtered(lambda tag: not tag.tax_negate).id
    old_3b_tax_tags_plus = old_3b_tax_tags.filtered(lambda tag: not tag.tax_negate).id
    old_plus_tax_tag_ids = []
    if old_3bl_tax_tags_plus:
        old_plus_tax_tag_ids.append(old_3bl_tax_tags_plus)
    if old_3b_tax_tags_plus:
        old_plus_tax_tag_ids.append(old_3b_tax_tags_plus)

    old_3bl_tax_tags_minus = old_3bl_tax_tags.filtered(lambda tag: tag.tax_negate).id
    old_3b_tax_tags_minus = old_3b_tax_tags.filtered(lambda tag: tag.tax_negate).id
    old_minus_tax_tag_ids = []
    if old_3bl_tax_tags_minus:
        old_minus_tax_tag_ids.append(old_3bl_tax_tags_minus)
    if old_3b_tax_tags_minus:
        old_minus_tax_tag_ids.append(old_3b_tax_tags_minus)

    goods_plus_tax_tag_id = goods_tax_tags.filtered(lambda tag: not tag.tax_negate).id
    goods_minus_tax_tag_id = goods_tax_tags.filtered(lambda tag: tag.tax_negate).id
    services_plus_tax_tag_id = services_tax_tags.filtered(lambda tag: not tag.tax_negate).id
    services_minus_tax_tag_id = services_tax_tags.filtered(lambda tag: tag.tax_negate).id

    insert_query_params = [
        (goods_plus_tax_tag_id, goods_taxes.ids, old_plus_tax_tag_ids, goods_taxes.invoice_repartition_line_ids.ids),
        (services_plus_tax_tag_id, services_taxes.ids, old_plus_tax_tag_ids, services_taxes.invoice_repartition_line_ids.ids),
        (goods_minus_tax_tag_id, goods_taxes.ids, old_minus_tax_tag_ids, goods_taxes.refund_repartition_line_ids.ids),
        (services_minus_tax_tag_id, services_taxes.ids, old_minus_tax_tag_ids, services_taxes.refund_repartition_line_ids.ids),
    ]
    insert_query_parts = []

    for new_tax_tag_id, tax_ids, old_tax_tag_ids, repartition_line_ids in insert_query_params:
        insert_query_parts.append(
            sql.SQL(
                cr.mogrify(
                    """
                    SELECT tag_aml_rel.account_move_line_id, %s
                    FROM account_account_tag_account_move_line_rel tag_aml_rel
                    JOIN account_move_line_account_tax_rel aml_at_rel ON aml_at_rel.account_move_line_id = tag_aml_rel.account_move_line_id
                    WHERE aml_at_rel.account_tax_id = ANY(%s)
                    AND tag_aml_rel.account_account_tag_id = ANY(%s)
                    """,
                    [new_tax_tag_id, tax_ids, old_tax_tag_ids]
                ).decode()
            )
        )

        if len(old_tax_tag_ids) > 1:
            cr.execute(
                """
                DELETE FROM account_account_tag_account_tax_repartition_line_rel tag_aml_rel
                WHERE tag_aml_rel.account_account_tag_id = %s
                AND (
                    SELECT COUNT(*)
                    FROM account_account_tag_account_tax_repartition_line_rel sub_tag_aml_rel
                    WHERE sub_tag_aml_rel.account_tax_repartition_line_id = tag_aml_rel.account_tax_repartition_line_id
                    AND sub_tag_aml_rel.account_account_tag_id = %s
                ) >= 1
                """,
                [old_tax_tag_ids[0], old_tax_tag_ids[1]]
            )

        cr.execute(
            """
            UPDATE account_account_tag_account_tax_repartition_line_rel
            SET account_account_tag_id = %s
            WHERE account_tax_repartition_line_id = ANY(%s)
            AND account_account_tag_id = ANY(%s)
            """,
            [new_tax_tag_id, repartition_line_ids, old_tax_tag_ids]
        )

    cr.execute(
        sql.SQL(
            """
            INSERT INTO account_account_tag_account_move_line_rel (account_move_line_id, account_account_tag_id)
                {select_statement}
            ON CONFLICT DO NOTHING
            """
        ).format(select_statement=sql.SQL(" UNION ").join(insert_query_parts)).as_string(cr)
    )
