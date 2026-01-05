# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {"lang": "en_US"})

    ChartTemplate = env["account.chart.template"]
    companies = env["res.company"].search([("chart_template", "=", "id")], order="parent_path")

    new_tax_groups = ["l10n_id_tax_group_stlg", "l10n_id_tax_group_non_luxury_goods", "l10n_id_tax_group_luxury_goods", "l10n_id_tax_group_0"]
    new_taxes = [
        "tax_ST4", "tax_PT4",
        "tax_ST5", "tax_PT5",
        "tax_ST6", "tax_ST7",
        "tax_luxury_sales_pemungut_ppn",
        "tax_PT6", "tax_PT7",
    ]

    tax_group_data = {
        xmlid: data
        for xmlid, data in ChartTemplate._get_account_tax_group("id").items()
        if xmlid in new_tax_groups
    }
    tax_data = {
        xmlid: data
        for xmlid, data in ChartTemplate._get_account_tax("id").items()
        if xmlid in new_taxes
    }

    for company in companies:
        new_tax_group_data = {}
        if (tax_group_data):
            new_tax_group_data = {g: data for g, data in tax_group_data.items() if not env.ref(f"account._{company.id}_{g}", raise_if_not_found=False)}

        # =============================
        # Load new tax data
        if new_tax_group_data:
            ChartTemplate.with_company(company)._load_data({
                "account.tax.group": new_tax_group_data,
            })
        if tax_data:
            ChartTemplate.with_company(company)._load_data({
                "account.tax": tax_data,
            })

        # =============================
        # Update existing tax description
        tax_map = {
            "tax_ST0": "VAT Not Collected",
            "tax_PT0": "Zero-Rated",
            "tax_ST2": "Exempt",
            "tax_PT2": "Exempt",
            "tax_ST3": "Taxable Luxury Goods",
            "tax_PT3": "Standard Rate for Luxury Goods & Services",
        }
        for xmlid, new_description in tax_map.items():
            tax = ChartTemplate.with_company(company).ref(xmlid, raise_if_not_found=False)
            if not tax:
                continue
            # Only update description if it hasn't been manually changed
            if tax.description == xmlid.replace("tax_", "").upper():
                tax.description = new_description

        # =============================
        # Archive ST1 and PT1
        for xmlid in ["tax_ST1", "tax_PT1"]:
            tax = ChartTemplate.with_company(company).ref(xmlid, raise_if_not_found=False)
            if tax and not tax.active:
                continue
            if tax:
                tax.active = False

        # =============================
        # Remove l10n_id.ppn_tag from specific taxes
        taxes_to_clean = [
            "tax_ST1", "tax_PT1",
            "tax_ST3", "tax_PT3",
            "tax_luxury_sales",
        ]
        ppn_tag = env.ref("l10n_id.ppn_tag", raise_if_not_found=False)
        if ppn_tag:
            tax_records = env["account.tax"].browse([])
            for xmlid in taxes_to_clean:
                rec = ChartTemplate.with_company(company).ref(xmlid, raise_if_not_found=False)
                if rec:
                    tax_records |= rec

            if tax_records:
                repartition_lines = env["account.tax.repartition.line"].sudo().search([
                    ("tax_id", "in", tax_records.ids),
                    ("tag_ids", "in", [ppn_tag.id]),
                ])
                if repartition_lines:
                    repartition_lines.write({"tag_ids": [(3, ppn_tag.id)]})

        # =============================
        # Update tax_luxury_sales group, description and invoice_label
        old_group = ChartTemplate.with_company(company).ref("l10n_id_tax_group_luxury_goods", raise_if_not_found=False)
        new_group = ChartTemplate.with_company(company).ref("l10n_id_tax_group_stlg", raise_if_not_found=False)
        tax_luxury_sales = ChartTemplate.with_company(company).ref("tax_luxury_sales", raise_if_not_found=False)
        if not (old_group and new_group and tax_luxury_sales):
            continue
        tax_luxury_sales_vals = {}
        if tax_luxury_sales.tax_group_id == old_group:
            tax_luxury_sales_vals['tax_group_id'] = new_group.id
        if tax_luxury_sales.description == "Luxury":
            tax_luxury_sales_vals['description'] = "Sales Tax on Luxury Goods (STLG)"
        if tax_luxury_sales.invoice_label == "Luxury Goods (ID)":
            tax_luxury_sales_vals['invoice_label'] = "20%"
        if tax_luxury_sales.name == "20%":
            tax_luxury_sales_vals['name'] = "20% (STLG)"
        if tax_luxury_sales.is_base_affected:
            tax_luxury_sales['is_base_affected'] = False
        tax_luxury_sales.write(tax_luxury_sales_vals)
