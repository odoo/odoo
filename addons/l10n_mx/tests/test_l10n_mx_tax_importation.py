from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestL10nMxInvoiceTaxImportation(AccountingTestCase):

    def test_case_with_tax_importation(self):
        imp_tax = self.env.ref('l10n_mx.tax_importation')
        category = self.env['product.category'].create({
            'name': 'Impuesto',
            'property_account_expense_categ_id': self.ref(
                'l10n_mx.cuenta801_01_99')
        })
        foreign_partner = self.env.ref("base.res_partner_12")
        broker_partner = self.env.ref("base.res_partner_2")
        product = self.env.ref("product.product_product_3")
        invoice = self.env['account.move'].with_context(
            default_type='in_invoice')
        foreign_invoice = invoice.create({
            'partner_id': foreign_partner.id,
            'type': 'in_invoice',
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 1,
                'price_unit': 450.0,
                'product_uom_id': product.uom_id.id,
                'name': product.name,
                'tax_ids': False,
                'account_id': product.product_tmpl_id.get_product_accounts()[
                    'income'].id,
            })],
        })
        foreign_invoice.action_post()
        product = product.copy({
            'name': 'Tax Importation',
            'categ_id': category.id,
            'supplier_taxes_id': [(6, 0, imp_tax.ids)]
        })
        broker_invoice = invoice.create({
            'partner_id': broker_partner.id,
            'type': 'in_invoice',
            'invoice_line_ids': [(0, 0, {
                'tax_ids': [(6, 0, imp_tax.ids)],
                'product_id': product.id,
                'quantity': 0.0,
                'price_unit': 450.00,
                'l10n_mx_invoice_broker_id': foreign_invoice.id,
                'account_id': product.product_tmpl_id.get_product_accounts()[
                    'income'].id,
            })],
        })
        broker_invoice.action_post()
        self.assertTrue(broker_invoice.line_ids.filtered(
            lambda line: line.partner_id == foreign_partner),
            'Lines for broker not found')
