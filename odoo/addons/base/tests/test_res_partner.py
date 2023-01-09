# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, UserError


class TestPartner(TransactionCase):

    def test_name_search(self):
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
            test_partner.with_user(public_user).check_access_rule('read')
        ns_res = self.env['res.partner'].with_user(public_user).sudo().name_search('Vlad', args=[('user_ids.email', 'ilike', 'vlad')])
        self.assertEqual(set(i[0] for i in ns_res), set(test_user.partner_id.ids))

    def test_name_get(self):
        """ Check name_get on partner, especially with different context
        Check name_get correctly return name with context. """
        test_partner_jetha = self.env['res.partner'].create({'name': 'Jethala', 'street': 'Powder gali', 'street2': 'Gokuldham Society'})
        test_partner_bhide = self.env['res.partner'].create({'name': 'Atmaram Bhide'})

        res_jetha = test_partner_jetha.with_context(show_address=1).name_get()
        self.assertEqual(res_jetha[0][1], "Jethala\nPowder gali\nGokuldham Society\n  \n", "name should contain comma separated name and address")
        res_bhide = test_partner_bhide.with_context(show_address=1).name_get()
        self.assertEqual(res_bhide[0][1], "Atmaram Bhide\n  \n", "name should contain only name if address is not available, without extra commas")

        res_jetha = test_partner_jetha.with_context(show_address=1, address_inline=1).name_get()
        self.assertEqual(res_jetha[0][1], "Jethala, Powder gali, Gokuldham Society", "name should contain comma separated name and address")
        res_bhide = test_partner_bhide.with_context(show_address=1, address_inline=1).name_get()
        self.assertEqual(res_bhide[0][1], "Atmaram Bhide", "name should contain only name if address is not available, without extra commas")

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

        # check final values (kept from form input)
        self.assertEqual(partner.lang, 'fr_FR')
        self.assertEqual(partner.child_ids.filtered(lambda p: p.name == "First Child").lang, 'de_DE')
        self.assertEqual(partner.child_ids.filtered(lambda p: p.name == "Second Child").lang, 'fr_FR')

    def test_partner_merge_wizard_dst_partner_id(self):
        """ Check that dst_partner_id in merge wizard displays id along with partner name """
        test_partner = self.env['res.partner'].create({'name': 'Radu the Handsome'})
        expected_partner_name = '%s (%s)' % (test_partner.name, test_partner.id)

        partner_merge_wizard = self.env['base.partner.merge.automatic.wizard'].with_context(
            {'partner_show_db_id': True, 'default_dst_partner_id': test_partner}).new()
        self.assertEqual(
            partner_merge_wizard.dst_partner_id.name_get(),
            [(test_partner.id, expected_partner_name)],
            "'Destination Contact' name should contain db ID in brackets"
        )

    def test_partner_is_public(self):
        """ Check that base.partner_user is a public partner."""
        self.assertFalse(self.env.ref('base.public_user').active)
        self.assertFalse(self.env.ref('base.public_partner').active)
        self.assertTrue(self.env.ref('base.public_partner').is_public)

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

    def test_display_address_missing_key(self):
        """ Check _display_address when some keys are missing. As a defaultdict is used, missing keys should be
        filled with empty strings. """
        country = self.env["res.country"].create({"name": "TestCountry", "address_format": "%(city)s %(zip)s"})
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
