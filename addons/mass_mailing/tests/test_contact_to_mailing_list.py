# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests.common import tagged

@tagged('mailing_templates')
@tagged('at_install', '-post_install')
class TestContactToMailingList(MassMailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.mailing_list_1 = cls.env['mailing.list'].create({'name': 'List 1'})
        cls.mailing_list_2 = cls.env['mailing.list'].create({'name': 'List 2'})

        cls.partner_1, cls.partner_2 = cls.env['res.partner'].create([
            {
                'name': 'John Doe',
                'email': 'john.doe@example.com',
                'country_id': cls.env.ref('base.us').id,
            },
            {
                'name': 'Jane Doe',
                'email': 'jane.doe@example.com',
                'country_id': cls.env.ref('base.be').id,
            },
        ])

    def setUp(self):
        super().setUp()
        self.env['mailing.contact'].search([]).unlink()

    def test_action_add_contacts_to_mailing_lists(self):
        def _test_no_contact_in_mailing_lists():
            self.setUp()
            added_count, subs_partner_1, subs_partner_2 = self._execute_action_add_contacts_to_mailing_lists()

            self.assertEqual(2, added_count)
            _assert_contacts_and_subs(subs_partner_1, subs_partner_2)

        def _test_first_contact_in_two_lists_second_contact_out_of_two_list():
            self.setUp()
            self._create_contact_for_partner(self.partner_1, (self.mailing_list_1 | self.mailing_list_2))

            added_count, subs_partner_1, subs_partner_2 = self._execute_action_add_contacts_to_mailing_lists()

            self.assertEqual(1, added_count)
            _assert_contacts_and_subs(subs_partner_1, subs_partner_2)

        def _test_first_contact_in_one_list_second_contact_out_of_two_lists():
            self.setUp()
            self._create_contact_for_partner(self.partner_1, (self.mailing_list_1))

            added_count, subs_partner_1, subs_partner_2 = self._execute_action_add_contacts_to_mailing_lists()

            self.assertEqual(2, added_count)
            _assert_contacts_and_subs(subs_partner_1, subs_partner_2)

        def _test_first_contact_in_one_list_second_contact_in_one_list():
            self.setUp()
            self._create_contact_for_partner(self.partner_1, (self.mailing_list_1))
            self._create_contact_for_partner(self.partner_2, (self.mailing_list_2))

            added_count, subs_partner_1, subs_partner_2 = self._execute_action_add_contacts_to_mailing_lists()

            self.assertEqual(2, added_count)
            _assert_contacts_and_subs(subs_partner_1, subs_partner_2)

        def _test_first_contact_in_one_list_second_contact_in_two_lists():
            self.setUp()
            self._create_contact_for_partner(self.partner_1, (self.mailing_list_1))
            self._create_contact_for_partner(self.partner_2, (self.mailing_list_1 | self.mailing_list_2))

            added_count, subs_partner_1, subs_partner_2 = self._execute_action_add_contacts_to_mailing_lists()

            self.assertEqual(1, added_count)
            _assert_contacts_and_subs(subs_partner_1, subs_partner_2)

        def _test_first_contact_in_two_lists_second_contact_in_two_lists():
            self.setUp()
            self._create_contact_for_partner(self.partner_1, (self.mailing_list_1 | self.mailing_list_2))
            self._create_contact_for_partner(self.partner_2, (self.mailing_list_1 | self.mailing_list_2))

            added_count, subs_partner_1, subs_partner_2 = self._execute_action_add_contacts_to_mailing_lists()

            self.assertEqual(0, added_count)
            _assert_contacts_and_subs(subs_partner_1, subs_partner_2)

        def _assert_contacts_and_subs(subs_partner_1, subs_partner_2):
            self.assertEqual(2, len(subs_partner_1))
            self.assertEqual(2, len(subs_partner_2))
            self.assertTrue(all(self._is_contact_created_for_partner(p) for p in (self.partner_1 | self.partner_2)))

        _test_no_contact_in_mailing_lists()
        _test_first_contact_in_two_lists_second_contact_out_of_two_list()
        _test_first_contact_in_one_list_second_contact_out_of_two_lists()
        _test_first_contact_in_one_list_second_contact_in_one_list()
        _test_first_contact_in_one_list_second_contact_in_two_lists()
        _test_first_contact_in_two_lists_second_contact_in_two_lists()

    def _execute_action_add_contacts_to_mailing_lists(self):
        wizard = self._create_wizard(
            self.partner_1 | self.partner_2,
            self.mailing_list_1 | self.mailing_list_2
        )
        added_count = wizard._add_contacts_to_mailing_lists()
        subs_partner_1 = self._get_subscriptions(
            self.partner_1,
            self.mailing_list_1 | self.mailing_list_2
        )
        subs_partner_2 = self._get_subscriptions(
            self.partner_2,
            self.mailing_list_1 | self.mailing_list_2
        )
        return added_count, subs_partner_1, subs_partner_2

    def _is_contact_created_for_partner(self, partner):
        return self.env['mailing.contact'].search([('id', '=', partner.mailing_contact_id.id)])

    def _get_subscriptions(self, partners, mailing_lists):
        return self.env['mailing.subscription'].search([
            ('contact_id', 'in', partners.mapped('mailing_contact_id').ids),
            ('list_id', 'in', mailing_lists.ids)
        ])

    def _create_contact_for_partner(self, partner, mailing_lists, opt_out=False):
        return self.env['mailing.contact'].create([
        {
            'name': partner.name,
            'email': partner.email,
            'opt_out': opt_out,
            'res_partner_id': partner.id,
            'list_ids': mailing_lists.ids,
        }
    ])

    def _create_wizard(self, partners, mailing_lists):
        return self.env['contact.to.mailing.list'].create({
            'partner_ids': partners.ids,
            'mailing_list_ids': mailing_lists.ids,
        })
