# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command, models
from odoo.addons.base.models.ir_mail_server import extract_rfc2822_addresses
from odoo.addons.base.models.res_partner import Partner
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.exceptions import AccessError, RedirectWarning, UserError, ValidationError
from odoo.tests import Form
from odoo.tests.common import new_test_user, tagged, TransactionCase, users

# samples use effective TLDs from the Mozilla public suffix
# list at http://publicsuffix.org
SAMPLES = [
    ('"Raoul Grosbedon" <raoul@chirurgiens-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@chirurgiens-dentistes.fr'),
    ('ryu+giga-Sushi@aizubange.fukushima.jp', 'ryu+giga-sushi@aizubange.fukushima.jp', 'ryu+giga-sushi@aizubange.fukushima.jp'),
    ('Raoul chirurgiens-dentistes.fr', 'Raoul chirurgiens-dentistes.fr', ''),
    (" Raoul O'hara  <!@historicalsociety.museum>", "Raoul O'hara", '!@historicalsociety.museum'),
    ('Raoul Grosbedon <raoul@CHIRURGIENS-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@chirurgiens-dentistes.fr'),
    ('Raoul megaraoul@chirurgiens-dentistes.fr', 'Raoul', 'megaraoul@chirurgiens-dentistes.fr'),
]


@tagged('res_partner')
class TestPartner(TransactionCaseWithUserDemo):

    @contextmanager
    def mockPartnerCalls(self):
        _original_create = Partner.create
        self._new_partners = self.env['res.partner']

        def _res_partner_create(model, *args, **kwargs):
            records = _original_create(model, *args, **kwargs)
            self._new_partners += records.sudo()
            return records

        with patch.object(Partner, 'create',
                          autospec=True, side_effect=_res_partner_create):
            yield

    def _check_find_or_create(self, test_string, expected_name, expected_email, expected_partner=False):
        with self.mockPartnerCalls():
            partner = self.env['res.partner'].find_or_create(test_string)
        if expected_partner:
            self.assertEqual(
                partner, expected_partner,
                f'Should have found {expected_partner.name} ({expected_partner.id}), found {partner.name} ({partner.id}) instead')
            self.assertFalse(self._new_partners)
        else:
            self.assertEqual(
                partner, self._new_partners,
                f'Should have created a partner, found {partner.name} ({partner.id}) instead'
            )
        self.assertEqual(partner.name, expected_name)
        self.assertEqual(partner.email or '', expected_email)
        return partner

    def test_archive_internal_partners(self):
        test_partner = self.env['res.partner'].create({'name':'test partner'})
        test_user = self.env['res.users'].create({
                                'login': 'test@odoo.com',
                                'partner_id': test_partner.id,
                                })
        # Cannot archive the partner
        with self.assertRaises(RedirectWarning):
            test_partner.with_user(self.env.ref('base.user_admin')).toggle_active()
        with self.assertRaises(ValidationError):
            test_partner.with_user(self.user_demo).toggle_active()

        # Can archive the user but the partner stays active
        test_user.toggle_active()
        self.assertTrue(test_partner.active, 'Parter related to user should remain active')

        # Now we can archive the partner
        test_partner.toggle_active()

        # Activate the user should reactivate the partner
        test_user.toggle_active()
        self.assertTrue(test_partner.active, 'Activating user must active related partner')

    def test_email_formatted(self):
        """ Test various combinations of name / email, notably to check result
        of email_formatted field. """
        # multi create
        new_partners = self.env['res.partner'].create([{
            'name': "Vlad the Impaler",
            'email': f'vlad.the.impaler.{idx:02d}@example.com',
        } for idx in range(2)])
        self.assertEqual(
            sorted(new_partners.mapped('email_formatted')),
            sorted([f'"Vlad the Impaler" <vlad.the.impaler.{idx:02d}@example.com>' for idx in range(2)]),
            'Email formatted should be "name" <email>'
        )

        # test name_create with formatting / multi emails
        for source, (exp_name, exp_email, exp_email_formatted) in [
            (
                'Balázs <vlad.the.negociator@example.com>, vlad.the.impaler@example.com',
                ("Balázs", "vlad.the.negociator@example.com", '"Balázs" <vlad.the.negociator@example.com>')
            ),
            (
                'Balázs <vlad.the.impaler@example.com>',
                ("Balázs", "vlad.the.impaler@example.com", '"Balázs" <vlad.the.impaler@example.com>')
            ),
        ]:
            with self.subTest(source=source):
                new_partner_id = self.env['res.partner'].name_create(source)[0]
                new_partner = self.env['res.partner'].browse(new_partner_id)
                self.assertEqual(new_partner.name, exp_name)
                self.assertEqual(new_partner.email, exp_email)
                self.assertEqual(
                    new_partner.email_formatted, exp_email_formatted,
                    'Name_create should take first found email'
                )

        # check name updates and extract_rfc2822_addresses
        for source, exp_email_formatted, exp_addr in [
            (
                'Vlad the Impaler',
                '"Vlad the Impaler" <vlad.the.impaler@example.com>',
                ['vlad.the.impaler@example.com']
            ), (
                'Balázs', '"Balázs" <vlad.the.impaler@example.com>',
                ['vlad.the.impaler@example.com']
            ),
            # check with '@' in name
            (
                'Bike@Home', '"Bike@Home" <vlad.the.impaler@example.com>',
                ['Bike@Home', 'vlad.the.impaler@example.com']
            ), (
                'Bike @ Home@Home', '"Bike @ Home@Home" <vlad.the.impaler@example.com>',
                ['Home@Home', 'vlad.the.impaler@example.com']
            ), (
                'Balázs <email.in.name@example.com>',
                '"Balázs <email.in.name@example.com>" <vlad.the.impaler@example.com>',
                ['email.in.name@example.com', 'vlad.the.impaler@example.com']
            ),
        ]:
            with self.subTest(source=source):
                new_partner.write({'name': source})
                self.assertEqual(new_partner.email_formatted, exp_email_formatted)
                self.assertEqual(extract_rfc2822_addresses(new_partner.email_formatted), exp_addr)

        # check email updates
        new_partner.write({'name': 'Balázs'})
        for source, exp_email_formatted in [
            # encapsulated email
            (
                "Vlad the Impaler <vlad.the.impaler@example.com>",
                '"Balázs" <vlad.the.impaler@example.com>'
            ), (
                '"Balázs" <balazs@adam.hu>',
                '"Balázs" <balazs@adam.hu>'
            ),
            # multi email
            (
                "vlad.the.impaler@example.com, vlad.the.dragon@example.com",
                '"Balázs" <vlad.the.impaler@example.com,vlad.the.dragon@example.com>'
            ), (
                "vlad.the.impaler.com, vlad.the.dragon@example.com",
                '"Balázs" <vlad.the.dragon@example.com>'
            ), (
                'vlad.the.impaler.com, "Vlad the Dragon" <vlad.the.dragon@example.com>',
                '"Balázs" <vlad.the.dragon@example.com>'
            ),
            # falsy emails
            (False, False),
            ('', False),
            (' ', '"Balázs" <@ >'),
            ('notanemail', '"Balázs" <@notanemail>'),
        ]:
            with self.subTest(source=source):
                new_partner.write({'email': source})
                self.assertEqual(new_partner.email_formatted, exp_email_formatted)

    def test_find_or_create(self):
        original_partner = self.env['res.partner'].browse(
            self.env['res.partner'].name_create(SAMPLES[0][0])[0]
        )
        all_partners = []

        for (text_input, expected_name, expected_email), expected_partner, find_idx in zip(
            SAMPLES,
            [original_partner, False, False, False, original_partner, False,
             # patrick example
             False, False, False,
             # multi email
             False],
            [0, 0, 0, 0, 0, 0, 0, 6, 0, 0],
        ):
            with self.subTest(text_input=text_input):
                if not expected_partner and find_idx:
                    expected_partner = all_partners[find_idx]
                all_partners.append(
                    self._check_find_or_create(
                        text_input, expected_name, expected_email,
                        expected_partner=expected_partner,
                    )
                )

    def test_is_public(self):
        """ Check that base.partner_user is a public partner."""
        self.assertFalse(self.env.ref('base.public_user').active)
        self.assertFalse(self.env.ref('base.public_partner').active)
        self.assertTrue(self.env.ref('base.public_partner').is_public)

    def test_lang_computation_code(self):
        """ Check computation of lang: coming from installed languages, forced
        default value and propagation from parent."""
        default_lang_info = self.env['res.lang'].get_installed()[0]
        default_lang_code = default_lang_info[0]
        self.assertNotEqual(default_lang_code, 'de_DE')  # should not be the case, just to ease test
        self.assertNotEqual(default_lang_code, 'fr_FR')  # should not be the case, just to ease test

        # default is installed lang
        partner = self.env['res.partner'].create({'name': "Test Company"})
        self.assertEqual(partner.lang, default_lang_code)

        # check propagation of parent to child
        child = self.env['res.partner'].create({'name': 'First Child', 'parent_id': partner.id})
        self.assertEqual(child.lang, default_lang_code)

        # activate another languages to test language propagation when being in multi-lang
        self.env['res.lang']._activate_lang('de_DE')
        self.env['res.lang']._activate_lang('fr_FR')

        # default from context > default from installed
        partner = self.env['res.partner'].with_context(default_lang='de_DE').create({'name': "Test Company"})
        self.assertEqual(partner.lang, 'de_DE')
        first_child = self.env['res.partner'].create({'name': 'First Child', 'parent_id': partner.id})
        partner.write({'lang': 'fr_FR'})
        second_child = self.env['res.partner'].create({'name': 'Second Child', 'parent_id': partner.id})

        # check user input is kept
        self.assertEqual(partner.lang, 'fr_FR')
        self.assertEqual(first_child.lang, 'de_DE')
        self.assertEqual(second_child.lang, 'fr_FR')

    def test_name_create(self):
        res_partner = self.env['res.partner']
        for text, expected_name, expected_mail in SAMPLES:
            with self.subTest(text=text):
                partner_id, dummy = res_partner.name_create(text)
                partner = res_partner.browse(partner_id)
                self.assertEqual(expected_name or expected_mail.lower(), partner.name)
                self.assertEqual(expected_mail.lower() or False, partner.email)

        # name_create supports default_email fallback
        partner = self.env['res.partner'].browse(
            self.env['res.partner'].with_context(
                default_email='John.Wick@example.com'
            ).name_create('"Raoulette Vachette" <Raoul@Grosbedon.fr>')[0]
        )
        self.assertEqual(partner.name, 'Raoulette Vachette')
        self.assertEqual(partner.email, 'raoul@grosbedon.fr')

        partner = self.env['res.partner'].browse(
            self.env['res.partner'].with_context(
                default_email='John.Wick@example.com'
            ).name_create('Raoulette Vachette')[0]
        )
        self.assertEqual(partner.name, 'Raoulette Vachette')
        self.assertEqual(partner.email, 'John.Wick@example.com')

    def test_name_search(self):
        res_partner = self.env['res.partner']
        sources = [
            ('"A Raoul Grosbedon" <raoul@chirurgiens-dentistes.fr>', False),
            ('B Raoul chirurgiens-dentistes.fr', True),
            ("C Raoul O'hara  <!@historicalsociety.museum>", True),
            ('ryu+giga-Sushi@aizubange.fukushima.jp', True),
        ]
        for name, active in sources:
            _partner_id, dummy = res_partner.with_context(default_active=active).name_create(name)
        partners = res_partner.name_search('Raoul')
        self.assertEqual(len(partners), 2, 'Incorrect search number result for name_search')
        partners = res_partner.name_search('Raoul', limit=1)
        self.assertEqual(len(partners), 1, 'Incorrect search number result for name_search with a limit')
        self.assertEqual(partners[0][1], 'B Raoul chirurgiens-dentistes.fr', 'Incorrect partner returned, should be the first active')

    def test_name_search_with_user(self):
        """ Check name_search on partner, especially with domain based on auto_join
        user_ids field. Check specific SQL of name_search correctly handle joined tables. """
        test_partner = self.env['res.partner'].create({'name': 'Vlad the Impaler'})
        test_user = self.env['res.users'].create({'name': 'Vlad the Impaler', 'login': 'vlad', 'email': 'vlad.the.impaler@example.com'})

        ns_res = self.env['res.partner'].name_search('Vlad', operator='ilike')
        self.assertEqual(set(i[0] for i in ns_res), set((test_partner | test_user.partner_id).ids))

        ns_res = self.env['res.partner'].name_search('Vlad', args=[('user_ids.email', 'ilike', 'vlad')])
        self.assertEqual(set(i[0] for i in ns_res), set(test_user.partner_id.ids))

        # Check a partner may be searched when current user has no access but sudo is used
        public_user = self.env.ref('base.public_user')
        with self.assertRaises(AccessError):
            test_partner.with_user(public_user).check_access('read')
        ns_res = self.env['res.partner'].with_user(public_user).sudo().name_search('Vlad', args=[('user_ids.email', 'ilike', 'vlad')])
        self.assertEqual(set(i[0] for i in ns_res), set(test_user.partner_id.ids))

    def test_partner_merge_wizard_dst_partner_id(self):
        """ Check that dst_partner_id in merge wizard displays id along with partner name """
        test_partner = self.env['res.partner'].create({'name': 'Radu the Handsome'})
        expected_partner_name = '%s (%s)' % (test_partner.name, test_partner.id)

        partner_merge_wizard = self.env['base.partner.merge.automatic.wizard'].with_context(
            {'partner_show_db_id': True, 'default_dst_partner_id': test_partner}).new()
        self.assertEqual(
            partner_merge_wizard.dst_partner_id.display_name, expected_partner_name,
            "'Destination Contact' name should contain db ID in brackets"
        )

    def test_display_name_translation(self):
        self.env['res.lang']._activate_lang('fr_FR')
        self.env.ref('base.module_base')._update_translations(['fr_FR'])

        res_partner = self.env['res.partner']

        parent_contact = res_partner.create({
            'name': 'Parent',
            'type': 'contact',
        })

        child_contact = res_partner.create({
            'type': 'other',
            'parent_id': parent_contact.id,
        })

        self.assertEqual(child_contact.with_context(lang='en_US').display_name, 'Parent, Other Address')

        self.assertEqual(child_contact.with_context(lang='fr_FR').display_name, 'Parent, Autre adresse')


@tagged('res_partner')
class TestPartnerAddressCompany(TransactionCase):

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
        cls.test_country_state = cls.env['res.country.state'].create([
            {
                'code': 'OD',
                'country_id': cls.env.ref('base.be').id,
                'name': 'Odoo Province',
            },
        ])
        cls.test_industries = cls.env['res.partner.industry'].create([
            {'name': 'Balto Impersonators'},
            {'name': 'Floppy Advisors'},
            {'name': 'Both of the above'},
        ])
        cls.test_address_values_cmp, cls.test_address_values_2_cmp, cls.test_address_values_3_cmp = [
            {
                'city': 'Ramillies',
                'country_id': cls.env.ref('base.be'),
                'state_id': cls.test_country_state,
                'street': 'Test Street',
                'street2': '10 F',
                'zip': '1367',
            }, {
                'city': 'Ramillies 2',
                'country_id': cls.env.ref('base.us'),
                'state_id': cls.env['res.country.state'],
                'street': 'Another Street',
                'street2': False,
                'zip': '013670',
            }, {
                'city': 'Totally Not Ramillies',
                'country_id': cls.env.ref('base.be'),
                'state_id': cls.test_country_state,
                'street': 'Third Street',
                'street2': 'Without number',
                'zip': '1367#Corgi',
            },
        ]
        cls.test_address_values, cls.test_address_values_2, cls.test_address_values_3 = [
            {fname: value.id if isinstance(value, models.Model) else value for fname, value in values.items()}
            for values in (cls.test_address_values_cmp, cls.test_address_values_2_cmp, cls.test_address_values_3_cmp)
        ]

        # pre-existing data
        cls.test_parent = cls.env['res.partner'].create({
            'company_registry': '0477472701',
            'email': 'info@ghoststep.com',
            'industry_id': cls.test_industries[0].id,
            'is_company': True,
            'name': 'GhostStep',
            'phone': '+32455001122',
            'vat': 'BE0477472701',
            'type': 'contact',
            **cls.test_address_values,
        })
        cls.existing = cls.env['res.partner'].create({
            'name': 'Existing Contact',
            'parent_id': cls.test_parent.id,
        })

    @users('employee')
    def test_address(self):
        # check initial data
        for fname, fvalue in self.test_address_values_cmp.items():
            self.assertEqual(self.existing[fname], fvalue)

        # future new child
        ct1 = self.env['res.partner'].browse(
            self.env['res.partner'].name_create('Denis Bladesmith <denis.bladesmith@ghoststep.com>')[0]
        )
        self.assertEqual(ct1.type, 'contact', 'Default type must be "contact"')

        ct2, inv, deli, other = self.env['res.partner'].create([
            {
                'name': 'Address, Future Sibling of P1',
                **self.test_address_values_3,
            }, {
                'name': 'Invoice Child',
                'street': 'Invoice Child Street',
                'type': 'invoice',
            }, {
                'name': 'Delivery Child',
                'street': 'Delivery Child Street',
                'type': 'delivery',
            }, {
                'name': 'Other Child',
                'street': 'Other Child Street',
                'type': 'other',
            },
        ])
        ct1_1, inv_1 = self.env['res.partner'].create([
            {
                'name': 'Address, Child of P1',
                'parent_id': ct1.id,
            }, {
                'name': 'Address, Child of Invoice',
                'parent_id': inv.id,
            },
        ])
        # check creation values
        for fname in self.base_address_fields:
            self.assertFalse(ct1_1[fname])
        self.assertFalse(ct1_1.vat)
        self.assertEqual(inv_1.street, 'Invoice Child Street', 'Should take parent address')
        self.assertFalse(inv_1.vat)

        # sync P1 with parent, check address is update + other fields in write kept
        ct1_phone = '+320455999999'
        ct1.write({
            'phone': ct1_phone,
            'parent_id': self.test_parent.id,
        })
        for fname, fvalue in self.test_address_values_cmp.items():
            self.assertEqual(ct1[fname], fvalue)
            # Note: update is done only for direct children of parent
            self.assertFalse(ct1_1[fname], 'Descendants are not updated, only direct children')
        self.assertEqual(ct1.email, 'denis.bladesmith@ghoststep.com', 'Email should be preserved after sync')
        self.assertEqual(ct1.phone, ct1_phone, 'Phone should be preserved after address sync')
        self.assertEqual(ct1.type, 'contact', 'Type should be preserved after address sync')
        self.assertEqual(ct1.vat, 'BE0477472701', 'VAT should come from parent')
        self.assertEqual(ct1.industry_id, self.test_industries[0], 'Industry should come from parent')
        self.assertEqual(ct1.company_registry, '0477472701', 'Company registry should come from parent')

        # turn off sync: do what you want
        ct1_street = 'Different street, 42'
        ct1.write({
            'street': ct1_street,
            'state_id': False,
            'type': 'invoice',
        })
        self.assertEqual(ct1.street, ct1_street, 'Address fields must not be synced after turning sync off')
        self.assertEqual(ct1.zip, '1367', 'Address fields not changed in write should have kept their value')
        for fname in self.base_address_fields:
            # Note: only updated values are sync
            if fname == 'street':
                self.assertEqual(ct1_1[fname], ct1_street)
            else:
                self.assertFalse(ct1_1[fname])
        self.assertEqual(ct1.type, 'invoice')
        self.assertEqual(ct1.parent_id, self.test_parent, 'Changing address should not break hierarchy')
        self.assertNotEqual(self.test_parent.street, ct1_street, 'Parent address must not be touched')

        # turn on sync again: should reset address to parent
        ct1.write({'type': 'contact'})
        for fname, fvalue in self.test_address_values_cmp.items():
            self.assertEqual(ct1[fname], fvalue)
            # Note: update is done only for direct children of parent
            if fname == 'street':
                self.assertEqual(ct1_1[fname], ct1_street)
            else:
                self.assertFalse(ct1_1[fname])
        self.assertEqual(ct1.type, 'contact', 'Type should be preserved after address sync')

        # set P2 as sibling of P1 -> should update address
        ct2.write({'parent_id': self.test_parent.id})
        for fname, fvalue in self.test_address_values_cmp.items():
            self.assertEqual(ct2[fname], fvalue)

        # DOWNSTREAM: parent -> children
        # ------------------------------------------------------------
        self.test_parent.write(self.test_address_values_2)
        for fname, fvalue in self.test_address_values_2_cmp.items():
            self.assertEqual(ct1[fname], fvalue)
            self.assertEqual(ct2[fname], fvalue)
            self.assertEqual(self.existing[fname], fvalue)
        # but child of P3 is not updated, as only 1 level is updated
        for fname in self.base_address_fields:
            if fname == 'street':
                self.assertEqual(ct1_1[fname], ct1_street, 'Updated only through P1 direct update')
            else:
                self.assertFalse(ct1_1[fname], 'Still holding base creation values, no descendants update')
        # and not-contacts are not updated
        for child in inv, deli, other:
            self.assertEqual(child.street, f'{child.name} Street', 'Should not be updated')

        # UPSTREAM: child -> parent update: not done currently, consider contact is readonly
        # ------------------------------------------------------------
        ct1.write(self.test_address_values_3)
        for fname, fvalue in self.test_address_values_2_cmp.items():
            self.assertEqual(self.test_parent[fname], fvalue)
            self.assertEqual(ct2[fname], fvalue)
            self.assertEqual(self.existing[fname], fvalue)
        for fname, fvalue in self.test_address_values_3_cmp.items():
            self.assertEqual(ct1[fname], fvalue)
            self.assertEqual(ct1_1[fname], fvalue)

    @users('employee')
    def test_address_first_contact_sync(self):
        """ Test initial creation of company/contact pair where contact address gets copied to
        company """
        (
            void_parent_ct, void_parent_comp, full_parent_ct, full_parent_comp,
            void_parent_withparent, full_parent_withparent,
        ) = self.env['res.partner'].create([
            {  # contact parents
                'name': 'Void Ct',
                'is_company': False,
            }, {
                'name': 'Void Comp',
                'is_company': True,
            }, {  # company parents
                'name': 'Full Ct',
                'is_company': False,
                **self.test_address_values_2,
            }, {
                'name': 'Full Comp',
                'is_company': False,
                **self.test_address_values_2,
            }, {  # parent being itself a child of another partner
                'name': 'Void Ct With Parent',
                'parent_id': self.test_parent.id,
            }, {
                'name': 'Full Ct With Parent',
                'parent_id': self.test_parent.id,
                **self.test_address_values_2,
            },
        ])
        for parent in (void_parent_ct + void_parent_comp + full_parent_ct + full_parent_comp):
            with self.subTest(parent_name=parent.name):
                p1 = self.env['res.partner'].create(dict(
                    {
                    'name': 'Micheline Brutijus',
                    'parent_id': parent.id,
                    }, **self.test_address_values_3)
                )
                self.assertEqual(p1.type, 'contact', 'Default type must be "contact", not the copied parent type')
                if parent in (void_parent_ct, void_parent_comp):
                    for fname, fvalue in self.test_address_values_3_cmp.items():
                        self.assertEqual(p1[fname], fvalue, 'Creation value taken')
                        self.assertEqual(parent[fname], fvalue, 'Should sync void parent to first contact')
                elif parent in (full_parent_ct, full_parent_comp):
                    for fname, fvalue in self.test_address_values_2_cmp.items():
                        self.assertEqual(p1[fname], fvalue, 'Parent wins over creation values')
                        self.assertEqual(parent[fname], fvalue, 'Should not sync parent with address to first contact')
                elif parent == full_parent_withparent:
                    for fname, fvalue in self.test_address_values_cmp.items():
                        self.assertEqual(p1[fname], fvalue)
                        self.assertEqual(parent[fname], fvalue, 'Should not sync parent that is not root to first contact')
                elif parent == void_parent_withparent:
                    for fname, fvalue in self.test_address_values_cmp.items():
                        self.assertEqual(p1[fname], fvalue)
                        self.assertFalse(parent[fname], 'Should not sync parent that is not root to first contact, event when void')

    def test_address_get(self):
        """ Test address_get address resolution mechanism: it should first go down through descendants,
        stopping when encountering another is_copmany entity, then go up, stopping again at the first
        is_company entity or the root ancestor and if nothing matches, it should use the provided partner
        itself """
        res_partner = self.env['res.partner']
        elmtree = res_partner.browse(res_partner.name_create('Elmtree')[0])
        branch1 = res_partner.create({'name': 'Branch 1',
                                      'parent_id': elmtree.id,
                                      'is_company': True})
        leaf10 = res_partner.create({'name': 'Leaf 10',
                                     'parent_id': branch1.id,
                                     'type': 'invoice'})
        branch11 = res_partner.create({'name': 'Branch 11',
                                       'parent_id': branch1.id,
                                       'type': 'other'})
        leaf111 = res_partner.create({'name': 'Leaf 111',
                                      'parent_id': branch11.id,
                                      'type': 'delivery'})
        branch11.write({'is_company': False})  # force is_company after creating 1rst child
        branch2 = res_partner.create({'name': 'Branch 2',
                                      'parent_id': elmtree.id,
                                      'is_company': True})
        leaf21 = res_partner.create({'name': 'Leaf 21',
                                     'parent_id': branch2.id,
                                     'type': 'delivery'})
        leaf22 = res_partner.create({'name': 'Leaf 22',
                                     'parent_id': branch2.id})
        leaf23 = res_partner.create({'name': 'Leaf 23',
                                     'parent_id': branch2.id,
                                     'type': 'contact'})

        # go up, stop at branch1
        self.assertEqual(leaf111.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf111.id,
                          'invoice': leaf10.id,
                          'contact': branch1.id,
                          'other': branch11.id}, 'Invalid address resolution')
        self.assertEqual(branch11.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf111.id,
                          'invoice': leaf10.id,
                          'contact': branch1.id,
                          'other': branch11.id}, 'Invalid address resolution')

        # go down, stop at at all child companies
        self.assertEqual(elmtree.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': elmtree.id,
                          'invoice': elmtree.id,
                          'contact': elmtree.id,
                          'other': elmtree.id}, 'Invalid address resolution')

        # go down through children
        self.assertEqual(branch1.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf111.id,
                          'invoice': leaf10.id,
                          'contact': branch1.id,
                          'other': branch11.id}, 'Invalid address resolution')

        self.assertEqual(branch2.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf21.id,
                          'invoice': branch2.id,
                          'contact': branch2.id,
                          'other': branch2.id}, 'Invalid address resolution. Company is the first encountered contact, therefore default for unfound addresses.')

        # go up then down through siblings
        self.assertEqual(leaf21.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf21.id,
                          'invoice': branch2.id,
                          'contact': branch2.id,
                          'other': branch2.id}, 'Invalid address resolution, should scan commercial entity ancestor and its descendants')
        self.assertEqual(leaf22.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf21.id,
                          'invoice': leaf22.id,
                          'contact': leaf22.id,
                          'other': leaf22.id}, 'Invalid address resolution, should scan commercial entity ancestor and its descendants')
        self.assertEqual(leaf23.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf21.id,
                          'invoice': leaf23.id,
                          'contact': leaf23.id,
                          'other': leaf23.id}, 'Invalid address resolution, `default` should only override if no partner with specific type exists')

        # empty adr_pref means only 'contact'
        self.assertEqual(elmtree.address_get([]),
                        {'contact': elmtree.id}, 'Invalid address resolution, no contact means commercial entity ancestor')
        self.assertEqual(leaf111.address_get([]),
                        {'contact': branch1.id}, 'Invalid address resolution, no contact means finding contact in ancestors')
        branch11.write({'type': 'contact'})
        self.assertEqual(leaf111.address_get([]),
                        {'contact': branch11.id}, 'Invalid address resolution, branch11 should now be contact')

    def test_commercial_partner_nullcompany(self):
        """ The commercial partner is the first/nearest ancestor-or-self which
        is a company or doesn't have a parent
        """
        P = self.env['res.partner']
        p0 = P.create({'name': '0', 'email': '0'})
        self.assertEqual(p0.commercial_partner_id, p0, "partner without a parent is their own commercial partner")

        p1 = P.create({'name': '1', 'email': '1', 'parent_id': p0.id})
        self.assertEqual(p1.commercial_partner_id, p0, "partner's parent is their commercial partner")
        p12 = P.create({'name': '12', 'email': '12', 'parent_id': p1.id})
        self.assertEqual(p12.commercial_partner_id, p0, "partner's GP is their commercial partner")

        p2 = P.create({'name': '2', 'email': '2', 'parent_id': p0.id, 'is_company': True})
        self.assertEqual(p2.commercial_partner_id, p2, "partner flagged as company is their own commercial partner")
        p21 = P.create({'name': '21', 'email': '21', 'parent_id': p2.id})
        self.assertEqual(p21.commercial_partner_id, p2, "commercial partner is closest ancestor with themselves as commercial partner")

        p3 = P.create({'name': '3', 'email': '3', 'is_company': True})
        self.assertEqual(p3.commercial_partner_id, p3, "being both parent-less and company should be the same as either")

        notcompanies = p0 | p1 | p12 | p21
        self.env.cr.execute('update res_partner set is_company=null where id = any(%s)', [notcompanies.ids])
        for parent in notcompanies:
            p = P.create({
                'name': parent.name + '_sub',
                'email': parent.email + '_sub',
                'parent_id': parent.id,
            })
            self.assertEqual(
                p.commercial_partner_id,
                parent.commercial_partner_id,
                "check that is_company=null is properly handled when looking for ancestor"
            )

    def test_commercial_field_sync(self):
        """Check if commercial fields are synced properly: testing with VAT field"""
        company_1, company_2 = self.env['res.partner'].create([
            {
                'company_registry': '123456789',
                'industry_id': self.test_industries[0].id,
                'is_company': True,
                'name': 'company 1',
                'vat': 'BE013456789',
            }, {
                'company_registry': '9876543210',
                'industry_id': self.test_industries[0].id,
                'is_company': True,
                'name': 'company 2',
                'vat': 'BE9876543210',
            },
        ])

        contact = self.env['res.partner'].create({'name': 'someone', 'is_company': False, 'parent_id': company_1.id})
        self.assertEqual(contact.commercial_partner_id, company_1, "Commercial partner should be recomputed")
        for fname in ('company_registry', 'industry_id', 'vat'):
            self.assertEqual(contact[fname], company_1[fname], "Commercial field should be inherited from the company 1")

        # create a delivery address and a child for the partner
        contact_dlr = self.env['res.partner'].create({'name': 'somewhere', 'type': 'delivery', 'parent_id': contact.id})
        self.assertEqual(contact_dlr.commercial_partner_id, company_1, "Commercial partner should be recomputed")
        for fname in ('company_registry', 'industry_id', 'vat'):
            self.assertEqual(contact_dlr[fname], company_1[fname], "Commercial field should be inherited from the company 1")
        contact_ct = self.env['res.partner'].create({'name': 'child someone', 'parent_id': contact.id})
        self.assertEqual(contact_dlr.commercial_partner_id, company_1, "Commercial partner should be recomputed")
        for fname in ('company_registry', 'industry_id', 'vat'):
            self.assertEqual(contact_dlr[fname], company_1[fname], "Commercial field should be inherited from the company 1")

        # move the partner to another company
        contact.write({'parent_id': company_2.id})
        self.assertEqual(contact.commercial_partner_id, company_2, "Commercial partner should be recomputed")
        for fname in ('company_registry', 'industry_id', 'vat'):
            self.assertEqual(contact[fname], company_2[fname], "Commercial field should be inherited from the company 2")
        self.assertEqual(contact_dlr.commercial_partner_id, company_2, "Commercial partner should be recomputed on delivery")
        for fname in ('company_registry', 'industry_id', 'vat'):
            self.assertEqual(contact_dlr[fname], company_2[fname], "Commecial field should be inherited from the company 2 to delivery")
        self.assertEqual(contact_ct.commercial_partner_id, company_2, "Commercial partner should be recomputed on delivery")
        for fname in ('company_registry', 'industry_id', 'vat'):
            self.assertEqual(contact_ct[fname], company_2[fname], "Commecial field should be inherited from the company 2 to delivery")

        # check using embedded 2many commands
        company_2.write({'child_ids': [(0, 0, {'name': 'Alrik Greenthorn', 'email': 'agr@sunhelm.com'})]})
        contact2 = self.env['res.partner'].search([('email', '=', 'agr@sunhelm.com')])
        for fname in ('company_registry', 'industry_id', 'vat'):
            self.assertEqual(contact2[fname], company_2[fname], "Commercial field should be inherited from the company 2")

        # DOWNSTREAM update to descendants
        company_2.write({'company_registry': 'new', 'industry_id': self.test_industries[1].id, 'vat': 'BEnew'})
        for partner in contact + contact_dlr + contact_ct + contact2:
            for fname, fvalue in (('company_registry', 'new'), ('industry_id', self.test_industries[1]), ('vat', 'BEnew')):
                self.assertEqual(partner[fname], fvalue, "Commercial field should be updated from the company 2")

        # UPSTREAM: not supported (but desyncs it)
        contactvat = 'BE445566'
        contact.write({'vat': contactvat})
        for partner in company_2 + contact_dlr + contact_ct + contact2:
            self.assertEqual(partner.vat, 'BEnew', 'Sync to children should only work downstream and on commercial entities')
        for partner in contact:
            self.assertEqual(partner.vat, contactvat, 'Sync to children should only work downstream and on commercial entities')

        # MISC PARENT MANIPULATION
        # promote p1 to commercial entity
        contact.write({
            'parent_id': company_1.id,
            'is_company': True,
            'name': 'Sunhelm Subsidiary',
        })
        self.assertEqual(contact.vat, contactvat, 'Setting is_company should stop auto-sync of commercial fields')
        self.assertEqual(contact.commercial_partner_id, contact, 'Incorrect commercial entity resolution after setting is_company')
        self.assertEqual(company_1.vat, 'BE013456789', 'Should not impact parent')
        self.assertEqual(contact_dlr.vat, 'BEnew', 'Promotion not propagated')
        self.assertEqual(contact_ct.vat, 'BEnew', 'Promotion not propagated')

        # change parent of commercial entity
        (contact_dlr + contact_ct).write({'vat': contactvat})
        contact.write({'parent_id': company_2.id})
        self.assertEqual(contact.vat, contactvat, 'Setting is_company should stop auto-sync of commercial fields')
        self.assertEqual(contact.commercial_partner_id, contact, 'Incorrect commercial entity resolution after setting is_company')
        self.assertEqual(company_2.vat, 'BEnew', 'Should not impact parent')
        self.assertEqual(contact_dlr.vat, contactvat, 'Parent company stop auto sync')
        self.assertEqual(contact_ct.vat, contactvat, 'Parent company stop auto sync')

        # writing on parent should not touch child commercial entities
        sunhelmvat2 = 'BE0112233453'
        company_2.write({'vat': sunhelmvat2})
        for partner in contact + contact_ct + contact_dlr:
            self.assertEqual(contact.vat, contactvat, 'Setting is_company should stop auto-sync of commercial fields')
        for partner in contact2:
            self.assertEqual(partner.vat, sunhelmvat2, 'Commercial fields must be automatically synced')

    def test_company_dependent_commercial_sync(self):
        ResPartner = self.env['res.partner']

        company_1, company_2 = self.env['res.company'].create([
            {'name': 'company_1'},
            {'name': 'company_2'},
        ])

        test_partner_company = ResPartner.create({
            'name': 'This company',
            'barcode': 'Main Company',
            'is_company': True,
        })
        test_partner_company.with_company(company_1).barcode = 'Company 1'
        test_partner_company.with_company(company_2).barcode = 'Company 2'

        commercial_fields = ResPartner._commercial_fields()
        with patch.object(
            ResPartner.__class__,
            '_commercial_fields',
            lambda self: commercial_fields + ['barcode'],
        ), patch.object(ResPartner.__class__, '_validate_fields'):  # skip _check_barcode_unicity
            child_address = ResPartner.create({
                'name': 'Contact',
                'parent_id': test_partner_company.id,
            })
            self.assertEqual(child_address.barcode, 'Main Company')
            self.assertEqual(child_address.with_company(company_1).barcode, 'Company 1')
            self.assertEqual(child_address.with_company(company_2).barcode, 'Company 2')

    def test_company_change_propagation(self):
        """ Check propagation of company_id across children """
        User = self.env['res.users']
        Partner = self.env['res.partner']
        Company = self.env['res.company']

        company_1 = Company.create({'name': 'company_1'})
        company_2 = Company.create({'name': 'company_2'})

        test_partner_company = Partner.create({'name': 'This company'})
        test_user = User.create({'name': 'This user', 'login': 'thisu', 'email': 'this.user@example.com', 'company_id': company_1.id, 'company_ids': [company_1.id]})
        test_user.partner_id.write({'parent_id': test_partner_company.id})

        test_partner_company.write({'company_id': company_1.id})
        self.assertEqual(test_user.partner_id.company_id.id, company_1.id, "The new company_id of the partner company should be propagated to its children")

        test_partner_company.write({'company_id': False})
        self.assertFalse(test_user.partner_id.company_id.id, "If the company_id is deleted from the partner company, it should be propagated to its children")

        with self.assertRaises(UserError, msg="You should not be able to update the company_id of the partner company if the linked user of a child partner is not an allowed to be assigned to that company"), self.cr.savepoint():
            test_partner_company.write({'company_id': company_2.id})

    def test_display_address_missing_key(self):
        """ Check _display_address when some keys are missing. As a defaultdict is used, missing keys should be
        filled with empty strings. """
        country = self.env["res.country"].create({"name": "TestCountry", "address_format": "%(city)s %(zip)s", "code": "ZV"})
        partner = self.env["res.partner"].create({
            "name": "TestPartner",
            "country_id": country.id,
            "city": "TestCity",
            "zip": "12345",
        })
        before = partner._display_address()
        # Manually update the country address_format because placeholders are checked by create
        self.env.cr.execute(
            "UPDATE res_country SET address_format ='%%(city)s %%(zip)s %%(nothing)s' WHERE id=%s",
            [country.id]
        )
        self.env["res.country"].invalidate_model()
        self.assertEqual(before, partner._display_address().strip())

    def test_display_name(self):
        """ Check display_name on partner, especially with different context
        Check display_name correctly return name with context. """
        test_partner_jetha = self.env['res.partner'].create({'name': 'Jethala', 'street': 'Powder gali', 'street2': 'Gokuldham Society'})
        test_partner_bhide = self.env['res.partner'].create({'name': 'Atmaram Bhide'})

        res_jetha = test_partner_jetha.with_context(show_address=1).display_name
        self.assertEqual(res_jetha, "Jethala\nPowder gali\nGokuldham Society", "name should contain comma separated name and address")
        res_bhide = test_partner_bhide.with_context(show_address=1).display_name
        self.assertEqual(res_bhide, "Atmaram Bhide", "name should contain only name if address is not available, without extra commas")

        res_jetha = test_partner_jetha.with_context(show_address=1, address_inline=1).display_name
        self.assertEqual(res_jetha, "Jethala, Powder gali, Gokuldham Society", "name should contain comma separated name and address")
        res_bhide = test_partner_bhide.with_context(show_address=1, address_inline=1).display_name
        self.assertEqual(res_bhide, "Atmaram Bhide", "name should contain only name if address is not available, without extra commas")

    def test_accessibility_of_company_partner_from_branch(self):
        """ Check accessibility of company partner from branch. """
        company = self.env['res.company'].create({'name': 'company'})
        branch = self.env['res.company'].create({
            'name': 'branch',
            'parent_id': company.id
        })
        partner = self.env['res.partner'].create({
            'name': 'partner',
            'company_id': company.id
        })
        user = self.env['res.users'].create({
            'name': 'user',
            'login': 'user',
            'company_id': branch.id,
            'company_ids': [branch.id]
        })
        record = self.env['res.partner'].with_user(user).search([('id', '=', partner.id)])
        self.assertEqual(record.id, partner.id)


@tagged('res_partner', 'post_install', '-at_install')
class TestPartnerForm(TransactionCase):
    # those tests are made post-install because they need module 'web' for the
    # form view to work properly

    def test_lang_computation_form_view(self):
        """ Check computation of lang: coming from installed languages, forced
        default value and propagation from parent."""
        default_lang_info = self.env['res.lang'].get_installed()[0]
        default_lang_code = default_lang_info[0]
        self.assertNotEqual(default_lang_code, 'de_DE')  # should not be the case, just to ease test
        self.assertNotEqual(default_lang_code, 'fr_FR')  # should not be the case, just to ease test

        # default is installed lang
        partner_form = Form(self.env['res.partner'], 'base.view_partner_form')
        partner_form.name = "Test Company"
        self.assertEqual(partner_form.lang, default_lang_code, "New partner's lang should be default one")
        partner = partner_form.save()
        self.assertEqual(partner.lang, default_lang_code)

        # check propagation of parent to child
        with partner_form.child_ids.new() as child:
            child.name = "First Child"
            self.assertEqual(child.lang, default_lang_code, "Child contact's lang should have the same as its parent")
        partner = partner_form.save()
        self.assertEqual(partner.child_ids.lang, default_lang_code)

        # activate another languages to test language propagation when being in multi-lang
        self.env['res.lang']._activate_lang('de_DE')
        self.env['res.lang']._activate_lang('fr_FR')

        # default from context > default from installed
        partner_form = Form(
            self.env['res.partner'].with_context(default_lang='de_DE'),
            'base.view_partner_form'
        )
        # <field name="is_company" invisible="1"/>
        # <field name="company_type" widget="radio" options="{'horizontal': true}"/>
        # @api.onchange('company_type')
        # def onchange_company_type(self):
        #     self.is_company = (self.company_type == 'company')
        partner_form.company_type = 'company'
        partner_form.name = "Test Company"
        self.assertEqual(partner_form.lang, 'de_DE', "New partner's lang should take default from context")
        with partner_form.child_ids.new() as child:
            child.name = "First Child"
            self.assertEqual(child.lang, 'de_DE', "Child contact's lang should be the same as its parent.")
        partner_form.lang = 'fr_FR'
        self.assertEqual(partner_form.lang, 'fr_FR', "New partner's lang should take user input")
        with partner_form.child_ids.new() as child:
            child.name = "Second Child"
            self.assertEqual(child.lang, 'fr_FR', "Child contact's lang should be the same as its parent.")
        partner = partner_form.save()
        self.assertEqual(partner.child_ids.mapped('lang'), ['de_DE', 'fr_FR'])

        # check final values (kept from form input)
        self.assertEqual(partner.lang, 'fr_FR')
        self.assertEqual(partner.child_ids.filtered(lambda p: p.name == "First Child").lang, 'de_DE')
        self.assertEqual(partner.child_ids.filtered(lambda p: p.name == "Second Child").lang, 'fr_FR')

    def test_onchange_parent_sync_user(self):
        company_1 = self.env['res.company'].create({'name': 'company_1'})
        test_user = self.env['res.users'].create({
            'name': 'This user',
            'login': 'thisu',
            'email': 'this.user@example.com',
            'company_id': company_1.id,
            'company_ids': [company_1.id],
        })
        test_parent_partner = self.env['res.partner'].create({
            'company_type': 'company',
            'name': 'Micheline',
            'user_id': test_user.id,
        })
        with Form(self.env['res.partner']) as partner_form:
            partner_form.parent_id = test_parent_partner
            partner_form.company_type = 'person'
            partner_form.name = 'Philip'
            self.assertEqual(partner_form.user_id, test_parent_partner.user_id)


@tagged('res_partner')
class TestPartnerRecursion(TransactionCase):

    def setUp(self):
        super(TestPartnerRecursion, self).setUp()
        res_partner = self.env['res.partner']
        self.p1 = res_partner.browse(res_partner.name_create('Elmtree')[0])
        self.p2 = res_partner.create({'name': 'Elmtree Child 1', 'parent_id': self.p1.id})
        self.p3 = res_partner.create({'name': 'Elmtree Grand-Child 1.1', 'parent_id': self.p2.id})

    def test_100_res_partner_recursion(self):
        self.assertFalse(self.p3._has_cycle())
        self.assertFalse((self.p1 + self.p2 + self.p3)._has_cycle())

        # special case: empty recordsets don't lead to cycles
        self.assertFalse(self.env['res.partner']._has_cycle())

    # split 101, 102, 103 tests to force SQL rollback between them

    def test_101_res_partner_recursion(self):
        with self.assertRaises(ValidationError):
            self.p1.write({'parent_id': self.p3.id})

    def test_102_res_partner_recursion(self):
        with self.assertRaises(ValidationError):
            self.p2.write({'parent_id': self.p3.id})

    def test_103_res_partner_recursion(self):
        with self.assertRaises(ValidationError):
            self.p3.write({'parent_id': self.p3.id})

    def test_104_res_partner_recursion_indirect_cycle(self):
        """ Indirect hacky write to create cycle in children """
        p3b = self.p1.create({'name': 'Elmtree Grand-Child 1.2', 'parent_id': self.p2.id})
        with self.assertRaises(ValidationError):
            self.p2.write({'child_ids': [Command.update(self.p3.id, {'parent_id': p3b.id}),
                                         Command.update(p3b.id, {'parent_id': self.p3.id})]})

    def test_105_res_partner_recursion(self):
        with self.assertRaises(ValidationError):
            # p3 -> p2 -> p1 -> p2
            (self.p3 + self.p1).parent_id = self.p2

    def test_110_res_partner_recursion_multi_update(self):
        """ multi-write on several partners in same hierarchy must not trigger a false cycle detection """
        ps = self.p1 + self.p2 + self.p3
        self.assertTrue(ps.write({'phone': '123456'}))

    def test_111_res_partner_recursion_infinite_loop(self):
        """ The recursion check must not loop forever """
        self.p2.parent_id = False
        self.p3.parent_id = False
        self.p1.parent_id = self.p2
        with self.assertRaises(ValidationError):
            (self.p3|self.p2).write({'parent_id': self.p1.id})


@tagged('res_partner')
class TestPartnerCategory(TransactionCase):

    def test_name_search(self):
        category = self.env['res.partner.category'].create({'name': 'buggy_test'})
        result = self.env['res.partner.category'].name_search('buggy_test')
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [(category.id, category.display_name)])
