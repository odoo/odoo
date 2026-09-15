from odoo import SUPERUSER_ID, api

SHARED_GROUP_DOMAIN = (
    "['|', ('company_id', '=', False), ('company_id', 'parent_of', company_ids)]"
)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    rule = env.ref(
        "account_depreciation.account_asset_group_multi_company_rule",
        raise_if_not_found=False,
    )
    if rule:
        rule.domain_force = SHARED_GROUP_DOMAIN
