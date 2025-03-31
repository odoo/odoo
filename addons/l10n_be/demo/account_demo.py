from odoo import api, models, Command


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = super()._get_demo_data(company)
        if company.chart_template.startswith('be'):
            cid = company.id
            account_data = demo_data.setdefault('account.account', {})
            account_data.update({
                f"account.{cid}_a100": {'tag_ids': [Command.link(self.env.ref('account.demo_capital_account').id)]},
                f"account.{cid}_a300": {'tag_ids': [Command.link(self.env.ref('account.demo_stock_account').id)]},
                f"account.{cid}_a7600": {'tag_ids': [Command.link(self.env.ref('account.demo_sale_of_land_account').id)]},
                f"account.{cid}_a6201": {'tag_ids': [Command.link(self.env.ref('account.demo_ceo_wages_account').id)]},
                f"account.{cid}_a240000": {'tag_ids': [Command.link(self.env.ref('account.demo_office_furniture_account').id)]},
            })

        return demo_data
