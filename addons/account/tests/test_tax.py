from openerp.addons.account.tests.account_test_users import AccountTestUsers


class TestTax(AccountTestUsers):

    def test_percent_tax(self):
        """Test computations done by a 10 percent tax."""
        percent_tax = self.tax_model.create(dict(
            name="Percent tax",
            amount_type='percent',
            amount=10,
        ))
        self.assertEquals(percent_tax.compute_all(50.0, self.currency_euro)['taxes'][0]['amount'], 10.0)
        self.assertEquals(percent_tax.compute_all(50.0, self.currency_euro)['total_included'], 110.0)
