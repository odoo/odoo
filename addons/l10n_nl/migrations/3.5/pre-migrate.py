from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    nl = env.ref("base.nl", raise_if_not_found=False)
    if not nl:
        return

    Tag = env["account.account.tag"].with_context(active_test=False, lang="en_US")
    tags = Tag.search(
        [
            ("name", "in", ["Cost of sales", "Cost of goods sold"]),
            ("applicability", "=", "accounts"),
            ("country_id", "=", nl.id),
        ]
    )

    tag_cos = tags.filtered(lambda t: t.name == "Cost of sales")
    tag_cogs = tags.filtered(lambda t: t.name == "Cost of goods sold")

    if not (tag_cos and tag_cogs):
        return

    tag_cos.write({"name": "__tmp__swap_cost_tag__"})
    tag_cogs.write({"name": "Cost of sales"})
    tag_cos.write({"name": "Cost of goods sold"})
