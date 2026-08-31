from odoo import api, SUPERUSER_ID, Command


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    new_values = {
        '00ex': {
            'name': '0% OSS N2.2',
            'invoice_legal_notes': 'Art. 74-sexies DPR 633/1972',
        },
        '00ex7': {
            'name': '0% OSS N7',
            'invoice_legal_notes': 'Art. 74-sexies DPR 633/1972',
        },
    }
    new_xml_ids = ['00exg', '00exs']

    for company in env['res.company'].search([('chart_template', '=', 'it')], order="parent_path"):
        ChartTemplate = env['account.chart.template'].with_company(company)

        # 1. Update 00ex and 00ex7
        for xml_id, new_vals in new_values.items():
            tax = ChartTemplate.with_context(active_test=False).ref(xml_id, raise_if_not_found=False)
            if not tax:
                continue

            tax.write({
                'name': new_vals['name'],
                'invoice_legal_notes': new_vals['invoice_legal_notes'],
                'fiscal_position_ids': [Command.clear()],
                'original_tax_ids': [Command.clear()],
            })

        # 2. Create 00exg and 00exs
        missing = [
            xid for xid in new_xml_ids
            if not ChartTemplate.ref(xid, raise_if_not_found=False)
        ]
        if not missing:
            continue

        template_data = ChartTemplate._get_chart_template_data(company.chart_template)
        tax_data = template_data.get('account.tax', {})

        to_load = {
            xid: vals for xid, vals in tax_data.items()
            if xid.split('.')[-1] in missing
        }
        if to_load:
            ChartTemplate._load_data({'account.tax': to_load})
