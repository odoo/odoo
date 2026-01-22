from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    tag_cos = env.ref("l10n_nl.account_tag_7")
    tag_cogs = env.ref("l10n_nl.account_tag_10")

    if not (tag_cogs and tag_cos):
        return

    tag_cos.write({"name": "tmp_swap_cost_tag"})
    tag_cogs.write({"name": "Cost of sales"})
    tag_cos.write({"name": "Cost of goods sold"})
