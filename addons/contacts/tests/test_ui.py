# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from lxml import etree

import odoo.tests


@odoo.tests.tagged('-at_install', 'post_install')
class TestUi(odoo.tests.HttpCase):
    def test_set_defaults(self):
        """Tests the "Set Defaults" feature of the debug menu on the res.partner form.

        Set a user-defined default on the computed (with inverse) field `company_type`
        so the default "Company" becomes "Indivdual".
        """
        # Ensure the requirements of the test:
        # The tour assumptions are currently that `res.partner.company_type` is a non-readonly computed field
        # currently defaulting to "company" in the `res.partner` form.
        # If the below assertions change in the future, the tour needs to be adapted, as well as these assertions.
        company_type_field = self.env['res.partner']._fields['company_type']
        self.assertTrue(company_type_field.compute)
        self.assertFalse(company_type_field.readonly)
        action_context = literal_eval(self.env.ref('contacts.action_contacts').context)
        self.assertTrue(action_context.get('default_is_company'))
        # Make sure there is currently no user-defined default on res.partner.company_type
        # so "Company" is the default value for the field res.partner.company_type
        self.env['ir.default'].search([
            ('field_id', '=', self.env.ref('base.field_res_partner__company_type').id),
        ]).unlink()
        self.assertEqual(self.env['res.partner'].with_context(**action_context).new().company_type, "company")

        self.start_tour("/odoo", 'debug_menu_set_defaults', login="admin")

    def test_vat_label_string(self):
        """ Test changing the vat_label field of the user company_id.
            It be immediately reflected on partners views.
        """
        partner = self.env['res.partner'].create({'name': 'Jean'})
        # call get view to warm the cache
        partner.get_view()

        self.env.user.company_id.country_id = self.env.ref('base.us')
        self.env.user.company_id.country_id.vat_label = "TVA"
        view = partner.get_view()

        arch = etree.fromstring(view['arch'])
        for node in arch.iterfind(".//field[@name='vat']"):
            self.assertEqual(node.get("string"), 'TVA')
        for node in arch.iterfind(".//label[@for='vat']"):
            self.assertEqual(node.get("string"), 'TVA')
