from openerp.addons.account.tests.account_test_users import AccountTestUsers


class TestTax(AccountTestUsers):

    """Tests for taxes (account.tax)

    We don't really need at this point to link taxes to tax codes
    (account.tax.code) nor to companies (base.company) to check computation
    results.
    """

    def test_programmatic_tax(self):
        tax_id = self.tax_model.create(dict(
            name="Programmatic tax",
            type='code',
            python_compute='result = 12.0',
            python_compute_inv='result = 11.0',
        ))

        res = tax_id.compute_all(50.0, 2)

        tax_detail = res['taxes'][0]
        self.assertEquals(tax_detail['amount'], 24.0)
        self.assertEquals(res['total_included'], 124.0)

    def test_percent_tax(self):
        """Test computations done by a 10 percent tax."""
        tax_id = self.tax_model.create(dict(
            name="Percent tax",
            type='percent',
            amount='0.1',
        ))

        res = tax_id.compute_all(50.0, 2)

        tax_detail = res['taxes'][0]
        self.assertEquals(tax_detail['amount'], 10.0)
        self.assertEquals(res['total_included'], 110.0)

        # now the inverse computation
        res = tax_id.compute_inv(55.0, 2)
        self.assertEquals(res[0]['amount'], 10.0)
