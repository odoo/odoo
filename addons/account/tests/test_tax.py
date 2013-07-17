from openerp.tests.common import TransactionCase

class TestTax(TransactionCase):
    """Tests for taxes (account.tax)

    We don't really need at this point to link taxes to tax codes
    (account.tax.code) nor to companies (base.company) to check computation
    results.
    """

    def setUp(self):
        super(TestTax, self).setUp()
        self.tax_model = self.registry('account.tax')

    def test_programmatic_tax(self):
        cr, uid = self.cr, self.uid
        tax_id = self.tax_model.create(cr, uid, dict(
                name="Programmatic tax",
                type='code',
                python_compute='result = 12.0',
                python_compute_inv='result = 11.0',
                ))

        tax_records = self.tax_model.browse(cr, uid, [tax_id])
        res = self.tax_model.compute_all(cr, uid, tax_records, 50.0, 2)

        tax_detail = res['taxes'][0]
        self.assertEquals(tax_detail['amount'], 24.0)
        self.assertEquals(res['total_included'], 124.0)

    def test_percent_tax(self):
        """Test computations done by a 10 percent tax."""
        cr, uid = self.cr, self.uid
        tax_id = self.tax_model.create(cr, uid, dict(
                name="Percent tax",
                type='percent',
                amount='0.1',
                ))

        tax_records = self.tax_model.browse(cr, uid, [tax_id])
        res = self.tax_model.compute_all(cr, uid, tax_records, 50.0, 2)

        tax_detail = res['taxes'][0]
        self.assertEquals(tax_detail['amount'], 10.0)
        self.assertEquals(res['total_included'], 110.0)

        # now the inverse computation
        res = self.tax_model.compute_inv(cr, uid, tax_records, 55.0, 2)
        self.assertEquals(res[0]['amount'], 10.0)
