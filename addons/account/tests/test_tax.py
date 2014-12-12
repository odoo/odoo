from openerp.addons.account.tests.account_test_users import AccountTestUsers


class TestTax(AccountTestUsers):

    """Tests for taxes (account.tax)

    We don't really need at this point to link taxes to tax codes
    (account.tax.code) nor to companies (base.company) to check computation
    results.
    """

    def test_percent_tax(self):
        """Test computations done by a 10 percent tax."""
        percent_tax = self.tax_model.create(dict(
            name="Percent tax",
            amount_type='percent',
            amount=10,
        ))
        self.assertEquals(percent_tax.compute_all(50.0, 2)['taxes'][0]['amount'], 10.0)
        self.assertEquals(percent_tax.compute_all(50.0, 2)['total_included'], 110.0)
