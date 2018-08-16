from odoo.tests import common

class TestFiscalPosition(common.TransactionCase):
    """Tests for fiscal positions in auto apply (account.fiscal.position).
    If a partner has a vat number, the fiscal positions with "vat_required=True"
    are preferred.
    """

    def setUp(self):
        super(TestFiscalPosition, self).setUp()
        self.fp = self.env['account.fiscal.position']

        # reset any existing FP
        self.fp.search([]).write({'auto_apply': False})

        self.res_partner = self.env['res.partner']
        self.be = be = self.env.ref('base.be')
        self.fr = fr = self.env.ref('base.fr')
        self.mx = mx = self.env.ref('base.mx')
        self.eu = eu = self.env.ref('base.europe')
        self.state_fr = self.env['res.country.state'].create(dict(
                                           name="State",
                                           code="ST",
                                           country_id=fr.id))
        self.jc = self.res_partner.create(dict(
                                           name="JCVD",
                                           vat="BE0477472701",
                                           country_id=be.id))
        self.ben = self.res_partner.create(dict(
                                           name="BP",
                                           country_id=be.id))
        self.george = self.res_partner.create(dict(
                                           name="George",
                                           vat="BE0477472701",
                                           country_id=fr.id))
        self.alberto = self.res_partner.create(dict(
                                           name="Alberto",
                                           vat="BE0477472701",
                                           country_id=mx.id))
        self.be_nat = self.fp.create(dict(
                                         name="BE-NAT",
                                         auto_apply=True,
                                         country_id=be.id,
                                         vat_required=False,
                                         sequence=10))
        self.fr_b2c = self.fp.create(dict(
                                         name="EU-VAT-FR-B2C",
                                         auto_apply=True,
                                         country_id=fr.id,
                                         vat_required=False,
                                         sequence=40))
        self.fr_b2b = self.fp.create(dict(
                                         name="EU-VAT-FR-B2B",
                                         auto_apply=True,
                                         country_id=fr.id,
                                         vat_required=True,
                                         sequence=50))

    def test_10_fp_country(self):
        def assert_fp(partner, expected_pos, message):
            self.assertEquals(
                self.fp.get_fiscal_position(partner.id),
                expected_pos.id,
                message)

        george, jc, ben, alberto = self.george, self.jc, self.ben, self.alberto

        # B2B has precedence over B2C for same country even when sequence gives lower precedence
        self.assertGreater(self.fr_b2b.sequence, self.fr_b2c.sequence)
        assert_fp(george, self.fr_b2b, "FR-B2B should have precedence over FR-B2C")
        self.fr_b2b.auto_apply = False
        assert_fp(george, self.fr_b2c, "FR-B2C should match now")
        self.fr_b2b.auto_apply = True

        # Create positions matching on Country Group and on NO country at all
        self.eu_intra_b2b = self.fp.create(dict(
                                         name="EU-INTRA B2B",
                                         auto_apply=True,
                                         country_group_id=self.eu.id,
                                         vat_required=True,
                                         sequence=20))
        self.world = self.fp.create(dict(
                                         name="WORLD-EXTRA",
                                         auto_apply=True,
                                         vat_required=False,
                                         sequence=30))

        # Country match has higher precedence than group match or sequence
        self.assertGreater(self.fr_b2b.sequence, self.eu_intra_b2b.sequence)
        assert_fp(george, self.fr_b2b, "FR-B2B should have precedence over EU-INTRA B2B")

        # B2B has precedence regardless of country or group match
        self.assertGreater(self.eu_intra_b2b.sequence, self.be_nat.sequence)
        assert_fp(jc, self.eu_intra_b2b, "EU-INTRA B2B should match before BE-NAT")

        # Lower sequence = higher precedence if country/group and VAT matches
        self.assertFalse(ben.vat) # No VAT set
        assert_fp(ben, self.be_nat, "BE-NAT should match before EU-INTRA due to lower sequence")

        # Remove BE from EU group, now BE-NAT should be the fallback match before the wildcard WORLD
        self.be.write({'country_group_ids': [(3, self.eu.id)]})
        self.assertTrue(jc.vat) # VAT set
        assert_fp(jc, self.be_nat, "BE-NAT should match as fallback even w/o VAT match")

        # No country = wildcard match only if nothing else matches
        self.assertTrue(alberto.vat) # with VAT
        assert_fp(alberto, self.world, "WORLD-EXTRA should match anything else (1)")
        alberto.vat = False          # or without
        assert_fp(alberto, self.world, "WORLD-EXTRA should match anything else (2)")

        # Zip range
        self.fr_b2b_zip100 = self.fr_b2b.copy(dict(zip_from=0, zip_to=5000, sequence=60))
        george.zip = 6000
        assert_fp(george, self.fr_b2b, "FR-B2B with wrong zip range should not match")
        george.zip = 3000
        assert_fp(george, self.fr_b2b_zip100, "FR-B2B with zip range should have precedence")

        # States
        self.fr_b2b_state = self.fr_b2b.copy(dict(state_ids=[(4, self.state_fr.id)], sequence=70))
        george.state_id = self.state_fr
        assert_fp(george, self.fr_b2b_zip100, "FR-B2B with zip should have precedence over states")
        george.zip = 0
        assert_fp(george, self.fr_b2b_state, "FR-B2B with states should have precedence")

        # Dedicated position has max precedence
        george.property_account_position_id = self.be_nat
        assert_fp(george, self.be_nat, "Forced position has max precedence")


    def test_20_fp_one_tax_2m(self):

        self.src_tax = self.env['account.tax'].create({'name': "SRC", 'amount': 0.0})
        self.dst1_tax = self.env['account.tax'].create({'name': "DST1", 'amount': 0.0})
        self.dst2_tax = self.env['account.tax'].create({'name': "DST2", 'amount': 0.0})

        self.fp2m = self.fp.create({
            'name': "FP-TAX2TAXES",
            'tax_ids': [
                (0,0,{
                    'tax_src_id': self.src_tax.id,
                    'tax_dest_id': self.dst1_tax.id
                }),
                (0,0,{
                    'tax_src_id': self.src_tax.id,
                    'tax_dest_id': self.dst2_tax.id
                })
            ]
        })
        mapped_taxes = self.fp2m.map_tax(self.src_tax)

        self.assertEqual(mapped_taxes, self.dst1_tax | self.dst2_tax)
