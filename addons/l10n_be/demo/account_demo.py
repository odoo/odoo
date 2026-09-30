from odoo import api, models, Command


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        def link_tag(tag_xml_id):
            tag = self.env.ref(tag_xml_id, raise_if_not_found=False)
            return [Command.link(tag.id)] if tag else []

        demo_data = super()._get_demo_data(company)
        if company.chart_template.startswith('be'):
            cid = company.id
            account_data = demo_data.setdefault('account.account', {})
            account_tag_map = {
                'a100': 'account.demo_capital_account',
                'a300': 'account.demo_stock_account',
                'a7600': 'account.demo_sale_of_land_account',
                'a6201': 'account.demo_ceo_wages_account',
                'a240000': 'account.demo_office_furniture_account',
            }
            account_data.update({
                f"account.{cid}_{account}": {'tag_ids': link_tag(tag)}
                for account, tag in account_tag_map.items()
            })

        return demo_data
