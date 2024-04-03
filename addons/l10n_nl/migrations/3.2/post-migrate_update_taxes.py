# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    nl_country_id = env.ref('base.nl').id
    tags_3b = env['account.account.tag']._get_tax_tags('3b (omzet)', nl_country_id)
    if not tags_3b:
        return
    tags_3bl = env['account.account.tag']._get_tax_tags('3bl (omzet)', nl_country_id)
    tag_3b_plus = tags_3b.filtered(lambda tag: not tag.tax_negate)
    tag_3bl_plus = tags_3bl.filtered(lambda tag: not tag.tax_negate)
    tag_3bl_minus = tags_3bl.filtered(lambda tag: tag.tax_negate)
    params = [
        tag_3b_plus.id or -1,
        tag_3bl_plus.id,
        tag_3bl_minus.id,
        tuple(tags_3b.ids),
    ]
    query = """
    INSERT INTO account_account_tag_account_move_line_rel (account_move_line_id, account_account_tag_id)
        SELECT tag_aml_rel.account_move_line_id, CASE WHEN tag_aml_rel.account_account_tag_id = %s THEN %s ELSE %s END
        FROM account_account_tag_account_move_line_rel tag_aml_rel
        WHERE tag_aml_rel.account_account_tag_id IN %s
    ON CONFLICT DO NOTHING
    """
    cr.execute(query, params)
