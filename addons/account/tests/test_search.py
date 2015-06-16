from openerp.addons.account.tests.account_test_users import AccountTestUsers


class TestSearch(AccountTestUsers):

    """Tests for search on name_search (account.account)

    The name search on account.account is quite complexe, make sure
    we have all the correct results
    """

    def test_name_search(self):
        ac_ids = self.account_type_model.search([], limit=1)
        self.atax = self.account_model.create(dict(
            name="Tax Received",
            code="X121",
            user_type=ac_ids.id,
            reconcile=True,
        )).id, "X121 Tax Received"

        self.apurchase = self.account_model.create(dict(
            name="Purchased Stocks",
            code="X1101",
            user_type=ac_ids.id,
            reconcile=True,
        )).id, "X1101 Purchased Stocks"

        self.asale = self.account_model.create(dict(
            name="Product Sales",
            code="XX200",
            user_type=ac_ids.id,
            reconcile=True,
        )).id, "XX200 Product Sales"

        self.all_ids = [self.atax[0], self.apurchase[0], self.asale[0]]

        atax_ids = self.account_model.name_search(name="Tax", operator='ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.atax[0]]), set([a[0] for a in atax_ids]), "name_search 'ilike Tax' should have returned Tax Received account only")

        atax_ids = self.account_model.name_search(name="Tax", operator='not ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.apurchase[0], self.asale[0]]), set([a[0] for a in atax_ids]), "name_search 'not ilike Tax' should have returned all but Tax Received account")

        apur_ids = self.account_model.name_search(name='Purchased Stocks', operator='ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.apurchase[0]]), set([a[0] for a in apur_ids]), "name_search 'ilike Purchased Stocks' should have returned Purchased Stocks account only")

        apur_ids = self.account_model.name_search(name='Purchased Stocks', operator='not ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.atax[0], self.asale[0]]), set([a[0] for a in apur_ids]), "name_search 'not ilike X1101' should have returned all but Purchased Stocks account")

        asale_ids = self.account_model.name_search(name='Product Sales', operator='ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.asale[0]]), set([a[0] for a in asale_ids]), "name_search 'ilike 200 Sales' should have returned Product Sales account only")

        asale_ids = self.account_model.name_search(name='Product Sales', operator='not ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.atax[0], self.apurchase[0]]), set([a[0] for a in asale_ids]), "name_search 'not ilike 200 Sales' should have returned all but Product Sales account")

        asale_ids = self.account_model.name_search(name='XX200', operator='ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.asale[0]]), set([a[0] for a in asale_ids]), "name_search 'ilike XX200' should have returned Product Sales account only")

    def test_property_unset_search(self):
        cr, uid = self.cr, self.uid
        res_partner_model = self.registry('res.partner')
        account_payment_term_model = self.registry('account.payment.term')

        a_partner = res_partner_model.create(cr, uid, {'name': 'test partner'})
        a_payment_term = account_payment_term_model.create(cr, uid, {'name': 'test payment term'})

        partner_ids = res_partner_model.search(cr, uid, [('property_payment_term', '=', False), ('id', '=', a_partner)])
        self.assertTrue(partner_ids, "unset property field 'propety_payment_term' should have been found")

        res_partner_model.write(cr, uid, [a_partner], {'property_payment_term': a_payment_term})
        partner_ids = res_partner_model.search(cr, uid, [('property_payment_term', '=', False), ('id', '=', a_partner)])
        self.assertFalse(partner_ids, "set property field 'propety_payment_term' should not have been found")
