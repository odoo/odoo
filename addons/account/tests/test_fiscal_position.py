from openerp.tests.common import TransactionCase

class TestFiscalPosition(TransactionCase):
    """Tests for fiscal positions in auto apply (account.fiscal.position).
    If a partner has a vat number, the fiscal positions with "vat_required=True"
    are prefered.
    """

    def setUp(self):
        super(TestFiscalPosition, self).setUp()
        self.fiscal_position_model = self.registry('account.fiscal.position')
        self.res_partner_model = self.registry('res.partner')
        self.res_country_model = self.registry('res.country')

    def test_fiscal_position(self):
        cr, uid = self.cr, self.uid
        company_id = 1
        country_id = self.res_country_model.search(cr, uid, [('name', '=', 'France')])[0]
        partner_id = self.res_partner_model.create(cr, uid, dict(
                                                   name="George",
                                                   vat_subjected=True,
                                                   notify_email="always",
                                                   country_id=country_id))
        fp_b2c_id = self.fiscal_position_model.create(cr, uid, dict(name="EU-VAT-FR-B2C",
                                                                    auto_apply=True,
                                                                    country_id=country_id,
                                                                    vat_required=False,
                                                                    sequence=1))
        fp_b2b_id = self.fiscal_position_model.create(cr, uid, dict(name="EU-VAT-FR-B2B",
                                                                    auto_apply=True,
                                                                    country_id=country_id,
                                                                    vat_required=True,
                                                                    sequence=2))
        res = self.fiscal_position_model.get_fiscal_position(cr, uid, company_id, partner_id)
        self.assertEquals(fp_b2b_id, res,
                          "Fiscal position detection should pick B2B position as 1rst match")

        self.fiscal_position_model.write(cr, uid, [fp_b2b_id], {'auto_apply': False})
        res = self.fiscal_position_model.get_fiscal_position(cr, uid, company_id, partner_id)
        self.assertEquals(fp_b2c_id, res,
                          "Fiscal position detection should pick B2C position as 1rst match")
