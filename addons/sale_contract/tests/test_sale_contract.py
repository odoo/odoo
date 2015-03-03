# -*- coding: utf-8 -*-
from openerp.addons.sale_contract.tests.common_sale_contract import TestContractCommon
from openerp.tools import mute_logger


class TestContract(TestContractCommon):

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_template(self):
        """ Test behaviour of on_change_template """
        Contract = self.env['account.analytic.account']

        # on_change_template on existing record (present in the db)
        self.contract.write(self.contract.on_change_template(template_id=self.contract_tmpl.id)['value'])
        self.assertEqual(self.contract_tmpl.contract_type, self.contract.contract_type, 'sale_contract: contract_type not copied when changing template')
        self.assertTrue(len(self.contract.recurring_invoice_line_ids.ids) == 0, 'sale_contract: recurring_invoice_line_ids copied on existing account.analytic.account record')

        # on_change_template on cached record (NOT present in the db)
        temp = Contract.new({'name': 'CachedContract',
                             'type': 'contract',
                             'state': 'open',
                             'partner_id': self.user_portal.partner_id.id
                             })
        temp.update(temp.on_change_template(template_id=self.contract_tmpl.id)['value'])
        self.assertEqual(self.contract_tmpl.contract_type, temp.contract_type, 'sale_contract: contract_type not copied when changing template')
        self.assertTrue(temp.recurring_invoice_line_ids.name, 'sale_contract: recurring_invoice_line_ids not copied on new cached account.analytic.account record')

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_sale_order(self):
        """ Test sale order line copying for recurring products on confirm"""
        self.sale_order.action_button_confirm()
        self.assertTrue(len(self.contract.recurring_invoice_line_ids.ids) == 1, 'sale_contract: recurring_invoice_line_ids not created when confirming sale_order with recurring_product')

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_invoice(self):
        """ Test invoice generation"""
        self.contract.write(self.contract.on_change_template(template_id=self.contract_tmpl.id)['value'])
        self.contract.write({'recurring_invoice_line_ids': [(0, 0, {'product_id': self.product.id, 'name': 'TestRecurringLine', 'price_unit': 31415.9, 'uom_id': self.product_tmpl.uom_id.id})]})
        invoice_id = self.contract._recurring_create_invoice()
        invoice = self.env['account.invoice'].browse(invoice_id)
        self.assertEqual(invoice.amount_untaxed, 31415.9, 'sale_contract: recurring invoice generation problem')

    def test_renewal(self):
        """ Test contract renewal """
        res = self.contract.prepare_renewal_order()
        renewal_so_id = res['res_id']
        renewal_so = self.env['sale.order'].browse(renewal_so_id)
        self.assertTrue(renewal_so.update_contract, 'sale_contract: renewal quotation generation is wrong')
        self.contract.write({'recurring_invoice_line_ids': [(0, 0, {'product_id': self.product.id, 'name': 'TestRecurringLine', 'price_unit': 50, 'uom_id': self.product.uom_id.id})]})
        renewal_so.write({'order_line': [(0, 0, {'product_id': self.product.id, 'name': 'TestRenewalLine'})]})
        renewal_so.action_button_confirm()
        lines = [line.name for line in self.contract.recurring_invoice_line_ids]
        self.assertTrue('TestRecurringLine' not in lines, 'sale_contract: old line still present after renewal quotation confirmation')
        self.assertTrue('TestRenewalLine' in lines, 'sale_contract: new line not present after renewal quotation confirmation')
