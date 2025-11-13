from odoo import models, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template(template='be', model='account.account', demo=True)
    def _l10n_be_account_account_demo(self):
        def link_tag(tag_xml_id):
            return [Command.link(tag.id)] if (tag := self.env.ref(tag_xml_id, raise_if_not_found=False)) else []
        return {
            "a100": {'tag_ids': link_tag('account.demo_capital_account')},
            "a300": {'tag_ids': link_tag('account.demo_stock_account')},
            "a7600": {'tag_ids': link_tag('account.demo_sale_of_land_account')},
            "a6201": {'tag_ids': link_tag('account.demo_ceo_wages_account')},
            "a240000": {'tag_ids': link_tag('account.demo_office_furniture_account')},
        }
