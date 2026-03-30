from odoo import models
from odoo.tests.common import new_test_user, tagged, TransactionCase, users


@tagged('res_partner', 'res_partner_address', 'post_install', 'post_install_l10n', '-at_install')
class TestResPartner(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # test user
        cls.test_user = new_test_user(
            cls.env,
            email='emp@test.mycompany.com',
            groups='base.group_user,base.group_partner_manager',
            login='employee',
            name='Employee',
            password='employee',
        )

        # test addresses
        cls.base_address_fields = {'street', 'street2', 'zip', 'city', 'state_id', 'country_id'}
        cls.test_industries = cls.env['res.partner.industry'].create([
            {'name': 'Balto Impersonators'},
            {'name': 'Floppy Advisors'},
            {'name': 'Both of the above'},
        ])
        cls.test_address_values_cmp, cls.test_address_values_2_cmp = [
            {
                'city': 'Lille',
                'country_id': cls.env.ref('base.fr'),
                'state_id': cls.env['res.country.state'],
                'street': 'Rue de la Clef',
                'street2': '36',
                'zip': '59000',
            }, {
                'city': 'Lille',
                'country_id': cls.env.ref('base.fr'),
                'state_id': cls.env['res.country.state'],
                'street': 'Rue Nationale',
                'street2': '78',
                'zip': '59800',
            },
        ]
        cls.test_address_values, cls.test_address_values_2 = [
            {
                fname: value.id if isinstance(value, models.Model) else value for fname, value in values.items()
            }
            for values in (
                cls.test_address_values_cmp, cls.test_address_values_2_cmp,
            )
        ]

        # pre-existing data
        cls.test_company_fr = cls.env['res.partner'].create({
            'company_registry': '73282932000074',
            'email': 'grimgor@waaagh.example.com',
            'industry_id': cls.test_industries[0].id,
            'name': 'Grimgor Boitenfer',
            'phone': '+33745751531',
            'vat': 'FR44732829320',
            'type': 'contact',
            **cls.test_address_values,
        })
        cls.test_company_fr_contact = cls.env['res.partner'].create({
            'name': 'Skarsnik Contact',
            'parent_id': cls.test_company_fr.id,
            'type': 'contact',
        })

    @users('employee')
    def test_l10n_fr_is_french(self):
        test_company, test_contact = (self.test_company_fr + self.test_company_fr_contact).with_env(self.env)
        self.assertTrue(test_company.l10n_fr_is_french)
        self.assertTrue(test_contact.l10n_fr_is_french)
        test_company.write({'country_id': self.env.ref('base.be').id})
        self.assertFalse(test_company.l10n_fr_is_french)
        self.assertFalse(test_contact.l10n_fr_is_french, 'Should be propagated')

    @users('employee')
    def test_partner_siret_from_company_registry(self):
        """ Test validation and check of siret / siren """
        for company_registry, (is_valid, siren, institution, vat) in zip(
            [
                '73282932000074',  # valid
                '63286832909047',  # valid
                '63286832909021',  # valid, same siren
                '63286832909022',  # valid checksum (luhn algorithm)
                '12345678900001',  # invalid (does not respect luhn algorithm)
                'coincoin',  # invalid
            ],
            [
                (True, '732829320', '00074', '44732829320'),
                (True, '632868329', '09047', '40632868329'),
                (True, '632868329', '09021', '40632868329'),
                (False, '', '', ''),
                (False, '', '', ''),
                (False, '', '', ''),
            ],
            strict=True,
        ):
            with self.subTest(company_registry=company_registry):
                partner = self.env['res.partner'].create({
                    'company_registry': company_registry,
                    'country_id': self.env.ref('base.fr').id,
                    'name': 'Ici Blabla',
                })
                self.assertEqual(partner._l10nfr_is_company_registry_siret_valid(), is_valid)
                self.assertEqual(partner._l10nfr_get_siren(), siren)
                self.assertEqual(partner._l10nfr_get_institution(), institution)
                self.assertEqual(partner._l10nfr_siren_to_vat(partner.company_registry), vat)

    @users('employee')
    def test_contact_sync(self):
        """ Test l10n_fr specific requirements for sync, notably siret / siren
        propagation. """
        test_company, test_contact = (self.test_company_fr + self.test_company_fr_contact).with_env(self.env)
        brother_contact = self.env['res.partner'].create({
            'name': 'Brother',
            'parent_id': test_company.id,
        })
        self.assertEqual(brother_contact.company_registry, '73282932000074', 'New siret should be propagated')

        # new siret, new siren -> propagate
        test_contact.write({
            'company_registry': '63286832909047',
        })
        self.assertEqual(brother_contact.company_registry, '63286832909047', 'New siret should be propagated')
        self.assertEqual(test_company.company_registry, '63286832909047', 'New siret should be propagated')
        self.assertEqual(test_contact.company_registry, '63286832909047', 'New siret should be propagated')

        # same siren, just changing institution
        test_contact.write({
            'company_registry': '63286832909021',
        })
        self.assertEqual(brother_contact.company_registry, '63286832909047', 'Contact changing institution should not change parent siret')
        self.assertEqual(test_company.company_registry, '63286832909047', 'Contact changing institution should not change parent siret')
        self.assertEqual(test_contact.company_registry, '63286832909021', 'Contact changing institution should not change parent siret')

        # invalid stuff
        test_contact.write({
            'company_registry': 'boudin, pommes, frites',
        })
        self.assertEqual(brother_contact.company_registry, '63286832909047', 'Contact changing institution should not change parent siret')
        self.assertEqual(test_company.company_registry, '63286832909047', 'Contact changing institution should not change parent siret')
        self.assertEqual(test_contact.company_registry, 'boudin, pommes, frites', 'Contact changing institution should not change parent siret')
