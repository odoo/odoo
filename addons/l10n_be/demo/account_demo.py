from odoo import api, models, Command


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = super()._get_demo_data(company)
        if company.account_fiscal_country_id.code == 'BE':
            cid = company.id
            account_data = demo_data.setdefault('account.account', {})
            tags = {
                'account.demo_capital_account': 'Demo Capital Account',
                'account.demo_stock_account': 'Demo Stock Account',
                'account.demo_sale_of_land_account': 'Demo Sale of Land Account',
                'account.demo_ceo_wages_account': 'Demo CEO Wages Account',
                'account.demo_office_furniture_account': 'Office Furniture',
            }
            tag_ids = []
            for ref, tag_name in tags.items():
                tag = self.env.ref(ref, raise_if_not_found=False) or self.env['account.account.tag'].create({'name': tag_name})
                tag_ids.append(tag.id)

            codes = ['a100', 'a300', 'a7600', 'a6201', 'a242']
            for i, code in enumerate(codes):
                account_data.update({
                    f"account.{cid}_{code}": {'tag_ids': [Command.link(tag_ids[i])]}
                })

        return demo_data
