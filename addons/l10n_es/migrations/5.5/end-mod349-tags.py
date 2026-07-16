from odoo import Command, SUPERUSER_ID, api

# Taxes added to `es_common_mainland` with the mod349 tags
NEW_TAXES = (
    "account_tax_template_s_iva0_eu_e_t",
    "account_tax_template_s_iva0_eu_e_m",
    "account_tax_template_s_iva0_eu_e_h",
    "account_tax_template_s_iva0_bc",
    "account_tax_template_s_iva_0_bc_tai",
    "account_tax_template_s_iva_0_bc_sus",
)


def migrate(cr, version):
    # The mod349 report is now computed from the `mod349[X]` tags of the taxes instead of a field on the move.
    # Mimic a partial reload of the chart template, restricted to the taxes carrying mod349 tags: add the tags on
    # the existing taxes and create the missing ones.
    env = api.Environment(cr, SUPERUSER_ID, {})
    mod349_tags = env["account.account.tag"].search([
        ("applicability", "=", "taxes"),
        ("country_id", "=", env.ref("base.es").id),
        ("name", "=like", "mod349[%"),
    ])

    def template_mod349_tag_ids(line_vals):
        template_tag_ids = {tag_id for command in line_vals.get("tag_ids") or [] for tag_id in command[2]}
        return [tag_id for tag_id in mod349_tags.ids if tag_id in template_tag_ids]

    companies = env["res.company"].search([("chart_template", "=like", "es%"), ("parent_id", "=", False)])
    for company in companies:
        ChartTemplate = env["account.chart.template"].with_company(company)
        tax_data = {
            xmlid: values
            for xmlid, values in ChartTemplate._get_chart_template_model_data(company.chart_template, "account.tax").items()
            if any(template_mod349_tag_ids(line_vals) for _command, _id, line_vals in values.get("repartition_line_ids", []))
        }

        new_taxes = {}
        for xmlid, values in tax_data.items():
            tax = ChartTemplate.ref(xmlid, raise_if_not_found=False)
            if not tax:
                # Only create the taxes introduced with the mod349 tags, not the ones deleted by the user
                if xmlid in NEW_TAXES:
                    new_taxes[xmlid] = values
                continue
            # Link the tags instead of a standard reload, which would replace the tags set by the user and
            # duplicate the taxes that differ from their template
            for _command, _id, line_vals in values.get("repartition_line_ids", []):
                if tag_ids := template_mod349_tag_ids(line_vals):
                    line_key = (line_vals["document_type"], line_vals["repartition_type"])
                    for rep_line in tax.repartition_line_ids:
                        if (rep_line.document_type, rep_line.repartition_type) == line_key:
                            rep_line.tag_ids = [Command.link(tag_id) for tag_id in tag_ids]

        if new_taxes:
            # Create the new taxes
            data = {"account.tax": new_taxes}
            ChartTemplate._pre_load_data(company.chart_template, company, {}, data)
            ChartTemplate._load_data(data)

    env.flush_all()

    # Set the tags on the existing base lines
    cr.execute(
        """
        WITH base_tags AS (
            SELECT rl.tax_id,
                   rl.document_type,
                   rel.account_account_tag_id AS tag_id
              FROM account_tax_repartition_line rl
              JOIN account_account_tag_account_tax_repartition_line_rel rel
                ON rel.account_tax_repartition_line_id = rl.id
             WHERE rl.repartition_type = 'base'
               AND rel.account_account_tag_id = ANY(%s)
        )
        INSERT INTO account_account_tag_account_move_line_rel (account_move_line_id, account_account_tag_id)
             SELECT aml.id, bt.tag_id
               FROM account_move_line aml
               JOIN account_move m
                 ON m.id = aml.move_id
               JOIN account_move_line_account_tax_rel tr
                 ON tr.account_move_line_id = aml.id
               JOIN base_tags bt
                 ON bt.tax_id = tr.account_tax_id
                AND bt.document_type = CASE WHEN m.move_type IN ('out_refund', 'in_refund') THEN 'refund' ELSE 'invoice' END
              WHERE aml.tax_repartition_line_id IS NULL
                AND m.move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
        ON CONFLICT DO NOTHING
        """,
        [mod349_tags.ids],
    )
    env["account.move.line"].invalidate_model(["tax_tag_ids"])
