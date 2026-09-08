from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    it_companies = env['res.company'].search([]).filtered(lambda c: c.country_code == 'IT')
    if not it_companies:
        return

    ve38_tag = env['account.account.tag'].search([('name', '=', 've38')], limit=1)

    for company in it_companies:
        ChartTemplate = env['account.chart.template'].with_company(company)

        for xml_id in ['10vsp_group', '5vsp_group', '4vsp_group']:
            tax = ChartTemplate.ref(xml_id, raise_if_not_found=False)
            if tax:
                tax.invoice_label = tax.name

        if ve38_tag:
            storno_taxes = env['account.tax']
            for xml_id in ['22vsp_storno', '10vsp_storno', '5vsp_storno', '4vsp_storno']:
                tax = ChartTemplate.ref(xml_id, raise_if_not_found=False)
                if tax:
                    storno_taxes |= tax

            if storno_taxes:
                storno_taxes.repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax' and ve38_tag in line.tag_ids).tag_ids -= ve38_tag
                storno_taxes.repartition_line_ids.filtered(lambda line: line.repartition_type == 'base' and ve38_tag not in line.tag_ids).tag_ids += ve38_tag
