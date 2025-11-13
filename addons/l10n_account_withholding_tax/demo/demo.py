from odoo import models, Command

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _withholding_tax_get_demo_account_ref(self, template_code):
        for data in self._get_account_tax(template_code).values():
            if data['type_tax_use'] == 'purchase':
                for line in data.get('repartition_line_ids', []):
                    if line[2]['repartition_type'] == 'tax' and line[2].get('account_id'):
                        return line[2]['account_id']
        return None

    @template(model='account.tax', demo=True)
    def _withholding_tax_account_tax_demo(self, template_code):
        if not (account_ref := self._withholding_tax_get_demo_account_ref(template_code)):
            return {}
        return {
            'withholding_demo_tax': {
                'name': '2% WTH',
                'tax_group_id': 'withholding_demo_tax_group',
                'type_tax_use': 'purchase',
                'is_withholding_tax_on_payment': True,
                'amount_type': 'percent',
                'amount': -2,
                'price_include_override': 'tax_excluded',
                'invoice_repartition_line_ids': [
                    Command.create({
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'repartition_type': 'tax',
                        'account_id': account_ref,
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.create({
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'repartition_type': 'tax',
                        'account_id': account_ref,
                    }),
                ],
                'withholding_sequence_id': 'purchase_wth_sequence',
            },
        }

    @template(model='account.tax.group', demo=True)
    def _withholding_tax_account_tax_group_demo(self, template_code):
        if not self._withholding_tax_get_demo_account_ref(template_code):
            return {}
        return {
            'withholding_demo_tax_group': {
                'name': 'WTH',
            },
        }

    @template(model='ir.sequence', demo=True)
    def _withholding_tax_ir_sequence_demo(self, template_code):
        if not self._withholding_tax_get_demo_account_ref(template_code):
            return {}
        return {
            'purchase_wth_sequence': {
                'name': 'Purchase wth sequence',
                'padding': 1,
                'number_increment': 1,
                'implementation': 'standard',
            },
        }

    @template(model='product.product', demo=True)
    def _withholding_tax_product_product(self, template_code):
        if not self._withholding_tax_get_demo_account_ref(template_code):
            return {}
        return {
            'product.product_product_1': {'supplier_taxes_id': [Command.link('withholding_demo_tax')]},
            'product.product_product_2': {'supplier_taxes_id': [Command.link('withholding_demo_tax')]},
        }
