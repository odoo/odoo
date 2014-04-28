from openerp.tests.common import TransactionCase

class TestSearch(TransactionCase):
    """Tests for search on name_search (account.account)

    The name search on account.account is quite complexe, make sure
    we have all the correct results
    """

    def setUp(self):
        super(TestSearch, self).setUp()
        cr, uid = self.cr, self.uid
        self.account_model = self.registry('account.account')
        self.account_type_model = self.registry('account.account.type')
        ac_ids = self.account_type_model.search(cr, uid, [], limit=1)
        self.atax = (int(self.account_model.create(cr, uid, dict(
            name="Tax Received",
            code="121",
            user_type=ac_ids[0],
        ))), "121 Tax Received")

        self.apurchase = (int(self.account_model.create(cr, uid, dict(
            name="Purchased Stocks",
            code="1101",
            user_type=ac_ids[0],
        ))), "1101 Purchased Stocks")

        self.asale = (int(self.account_model.create(cr, uid, dict(
            name="Product Sales",
            code="200",
            user_type=ac_ids[0],
        ))), "200 Product Sales")

        self.all_ids = [self.atax[0], self.apurchase[0], self.asale[0]]

    def test_name_search(self):
        cr, uid = self.cr, self.uid
        atax_ids = self.account_model.name_search(cr, uid, name="Tax", operator='ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.atax[0]]), set([a[0] for a in atax_ids]), "name_search 'ilike Tax' should have returned Tax Received account only")

        atax_ids = self.account_model.name_search(cr, uid, name="Tax", operator='not ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.apurchase[0], self.asale[0]]), set([a[0] for a in atax_ids]), "name_search 'not ilike Tax' should have returned all but Tax Received account")

        apur_ids = self.account_model.name_search(cr, uid, name='1101', operator='ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.apurchase[0]]), set([a[0] for a in apur_ids]), "name_search 'ilike 1101' should have returned Purchased Stocks account only")

        apur_ids = self.account_model.name_search(cr, uid, name='1101', operator='not ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.atax[0], self.asale[0]]), set([a[0] for a in apur_ids]), "name_search 'not ilike 1101' should have returned all but Purchased Stocks account")

        asale_ids = self.account_model.name_search(cr, uid, name='200 Sales', operator='ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.asale[0]]), set([a[0] for a in asale_ids]), "name_search 'ilike 200 Sales' should have returned Product Sales account only")

        asale_ids = self.account_model.name_search(cr, uid, name='200 Sales', operator='not ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.atax[0], self.apurchase[0]]), set([a[0] for a in asale_ids]), "name_search 'not ilike 200 Sales' should have returned all but Product Sales account")

        asale_ids = self.account_model.name_search(cr, uid, name='Product Sales', operator='ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.asale[0]]), set([a[0] for a in asale_ids]), "name_search 'ilike Product Sales' should have returned Product Sales account only")

        asale_ids = self.account_model.name_search(cr, uid, name='Product Sales', operator='not ilike', args=[('id', 'in', self.all_ids)])
        self.assertEqual(set([self.atax[0], self.apurchase[0]]), set([a[0] for a in asale_ids]), "name_search 'not ilike Product Sales' should have returned all but Product Sales account")
