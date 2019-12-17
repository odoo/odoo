from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged
import time


@tagged('post_install', '-at_install')
class TestProductIdChange(AccountingTestCase):
    """Test that when an included tax is mapped by a fiscal position, the included tax must be
    subtracted to the price of the product.
    """

    def setUp(self):
        super(TestProductIdChange, self).setUp()
        self.invoice_model = self.env['account.invoice']
        self.fiscal_position_model = self.env['account.fiscal.position']
        self.fiscal_position_tax_model = self.env['account.fiscal.position.tax']
        self.tax_model = self.env['account.tax']
        self.pricelist_model = self.env['product.pricelist']
        self.res_partner_model = self.env['res.partner']
        self.product_tmpl_model = self.env['product.template']
        self.product_model = self.env['product.product']
        self.invoice_line_model = self.env['account.invoice.line']
        self.account_receivable = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_receivable').id)], limit=1)
        self.account_revenue = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1)

    def test_product_id_change(self):
        partner = self.res_partner_model.create(dict(name="George"))
        tax_include_sale = self.tax_model.create(dict(name="Include tax",
                                                      type_tax_use='sale',
                                                      amount='21.00',
                                                      price_include=True))
        tax_include_purchase = self.tax_model.create(dict(name="Include tax",
                                                          type_tax_use='purchase',
                                                          amount='21.00',
                                                          price_include=True))
        tax_exclude_sale = self.tax_model.create(dict(name="Exclude tax",
                                                 type_tax_use='sale',
                                                 amount='0.00'))
        tax_exclude_purchase = self.tax_model.create(dict(name="Exclude tax",
                                                          type_tax_use='purchase',
                                                          amount='0.00'))
        product_tmpl = self.product_tmpl_model.create(dict(name="Voiture",
                                                           list_price='121',
                                                           taxes_id=[(6, 0, [tax_include_sale.id])],
                                                           supplier_taxes_id=[(6, 0, [tax_include_purchase.id])]))
        product = self.product_model.create(dict(product_tmpl_id=product_tmpl.id,
                                                 standard_price='242'))
        fp = self.fiscal_position_model.create(dict(name="fiscal position", sequence=1))
        fp_tax_sale = self.fiscal_position_tax_model.create(dict(position_id=fp.id,
                                                            tax_src_id=tax_include_sale.id,
                                                            tax_dest_id=tax_exclude_sale.id))
        fp_tax_purchase = self.fiscal_position_tax_model.create(dict(position_id=fp.id,
                                                                     tax_src_id=tax_include_purchase.id,
                                                                     tax_dest_id=tax_exclude_purchase.id))

        out_invoice = self.invoice_model.create({
            'partner_id': partner.id,
            'name': 'invoice to client',
            'account_id': self.account_receivable.id,
            'type': 'out_invoice',
            'date_invoice': time.strftime('%Y') + '-06-26',
            'fiscal_position_id': fp.id,
        })
        out_line = self.invoice_line_model.create({
            'product_id': product.id,
            'quantity': 1,
            'price_unit': 121.0,
            'invoice_id': out_invoice.id,
            'name': 'something out',
            'account_id': self.account_revenue.id,
        })

        in_invoice = self.invoice_model.create({
            'partner_id': partner.id,
            'name': 'invoice to supplier',
            'account_id': self.account_receivable.id,
            'type': 'in_invoice',
            'date_invoice': time.strftime('%Y') + '-06-26',
            'fiscal_position_id': fp.id,
        })
        in_line = self.invoice_line_model.create({
            'product_id': product.id,
            'quantity': 1,
            'price_unit': 242.0,
            'invoice_id': in_invoice.id,
            'name': 'something in',
            'account_id': self.account_revenue.id,
        })
        out_line._onchange_product_id()
        out_line._onchange_uom_id()
        self.assertEquals(100, out_line.price_unit, "The included tax must be subtracted to the price")
        in_line._onchange_product_id()
        self.assertEquals(200, in_line.price_unit, "The included tax must be subtracted to the price")
