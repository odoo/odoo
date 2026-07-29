from odoo.tests.common import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nFrAccountResPartner(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_fr = cls.env.ref('base.fr')
        cls.vat = 'FR23334175221'
        cls.siret_1 = '78467169500087'
        cls.siret_2 = '71204961800739'

        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'FR Company 1',
            'country_id': cls.country_fr.id,
            'vat': cls.vat,
        })
        cls.partner_2 = cls.env['res.partner'].create({
            'name': 'FR Company 2',
            'country_id': cls.country_fr.id,
            'vat': cls.vat,
        })

    def test_same_vat_different_siret(self):
        self.partner_1.l10n_fr_siret = self.siret_1
        self.partner_2.l10n_fr_siret = self.siret_2

        self.assertFalse(self.partner_2.same_vat_partner_id)

    def test_same_vat_same_siret(self):
        self.partner_1.l10n_fr_siret = self.siret_1
        self.partner_2.l10n_fr_siret = self.siret_1

        self.assertEqual(self.partner_2.same_vat_partner_id, self.partner_1)

    def test_same_vat_only_one_siret(self):
        self.partner_1.l10n_fr_siret = self.siret_1
        self.partner_2.l10n_fr_siret = False

        self.assertEqual(self.partner_2.same_vat_partner_id, self.partner_1)

    def test_same_vat_no_siret(self):
        self.partner_1.l10n_fr_siret = False
        self.partner_2.l10n_fr_siret = False

        self.assertEqual(self.partner_2.same_vat_partner_id, self.partner_1)
