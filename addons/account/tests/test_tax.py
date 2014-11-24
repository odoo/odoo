from openerp.tests.common import TransactionCase

class TestTax(TransactionCase):
    """Tests for taxes (account.tax)

    We don't really need at this point to link taxes to tax codes
    (account.tax.code) nor to companies (base.company) to check computation
    results.
    """

    def setUp(self):
        super(TestTax, self).setUp()
        self.account_tax = self.env['account.tax']

    def test_programmatic_tax(self):
        # Test computations done by Programmatic tax
        compute_programmatic_tax = self.account_tax.create({
            'name': "Programmatic tax",
            'type': 'code',
            'python_compute': 'result = 12.0',
            'python_compute_inv':'result = 11.0',
        }).compute_all(50.0, 2)

        self.assertEquals(compute_programmatic_tax['taxes'][0]['amount'], 24.0)
        self.assertEquals(compute_programmatic_tax['total_included'], 124.0)
    
    def test_percent_tax(self):
        #Test computations done by a 10 percent tax."""
        percent_tax = self.account_tax.create({
            'name': "Percent tax",
            'type': 'percent',
            'amount': '0.1',
        })
        
        self.assertEquals(percent_tax.compute_all(50.0, 2)['taxes'][0]['amount'], 10.0)
        self.assertEquals(percent_tax.compute_all(50.0, 2)['total_included'], 110.0)

        # now the inverse computation
        self.assertEquals(percent_tax.compute_inv(55.0, 2)[0]['amount'], 10.0)
