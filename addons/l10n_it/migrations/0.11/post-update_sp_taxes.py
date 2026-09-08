from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    tax_xmls = ['10vsp_group', '5vsp_group', '4vsp_group']
    storno_tax_xmls = ['22vsp_storno', '10vsp_storno', '5vsp_storno', '4vsp_storno']
    ve38_tag = env['account.account.tag'].search([('name', '=', 've38')], limit=1)

    ChartTemplate = env['account.chart.template']
    for company in env['res.company'].search([('chart_template', '=', 'it')], order="parent_path"):
        CompanyChartTemplate = ChartTemplate.with_company(company)

        for xml_id in tax_xmls:
            tax = CompanyChartTemplate.ref(xml_id, raise_if_not_found=False)
            if tax:
                tax.invoice_label = tax.name

        if ve38_tag:
            storno_taxes = env['account.tax']
            for xml_id in storno_tax_xmls:
                tax = CompanyChartTemplate.ref(xml_id, raise_if_not_found=False)
                if tax:
                    storno_taxes |= tax

            if storno_taxes:
                storno_taxes.repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax' and ve38_tag in line.tag_ids).tag_ids -= ve38_tag
                storno_taxes.repartition_line_ids.filtered(lambda line: line.repartition_type == 'base' and ve38_tag not in line.tag_ids).tag_ids += ve38_tag
