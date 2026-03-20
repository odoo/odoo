# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

        # TDE: to activate again after freeze
        # self.start_tour("/odoo", 'debug_menu_set_defaults', login="admin")

    def test_vat_label_string(self):
        """ Test changing the vat_label field of the user company_id.
            It should be immediately reflected on partners views.
        """
        partner = self.env['res.partner'].create({'name': 'Jean'})
        self.env.user.company_id.country_id = self.env.ref('base.us')
        self.env.user.company_id.country_id.vat_label = "TVA"
        res = partner.get_views([(False, "form")])

        self.assertEqual(res['models']['res.partner']['fields']['vat']['string'], 'TVA')
