# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

import odoo.tests


@odoo.tests.tagged('-at_install', 'post_install')
class TestUi(odoo.tests.HttpCase):
    def test_set_defaults(self):
        """Tests the "Set Defaults" feature of the debug menu on the res.partner form.

        Set a user-defined default on the field `function`,
        so the default value of Job Postion becomes "Default Position".
        """
        # Make sure it's editable field
        function_field = self.env['res.partner']._fields['function']
        self.assertFalse(function_field.readonly)
        # Make sure there is currently no user-defined default on res.partner.function
        # so there is no default value for the field res.partner.function
        self.env['ir.default'].search([
            ('field_id', '=', self.env.ref('base.field_res_partner__function').id),
        ]).unlink()
        self.assertEqual(self.env['res.partner'].new().function, False)

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
