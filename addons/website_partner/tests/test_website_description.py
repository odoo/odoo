# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestWebsiteDescription(TransactionCase):

    def test_text_alteration(self):
        website_description = '''
            <span style="text-decoration-line: line-through;">
                <font style="color: rgb(255, 0, 0);">Crossed</font>
            </span>
        '''
        test_partner = self.env['res.partner'].create({
            'name': 'Partner with text alteration',
            'website_description': website_description,
        })
        self.assertEqual(test_partner.website_description, website_description)

    def test_custom_code(self):
        website_description = '''
            <iframe
                title="The way of the developer"
                src="https://www.youtube.com/embed/dQw4w9WgXcQ">
            </iframe>
        '''
        test_partner = self.env['res.partner'].create({
            'name': 'Partner with an iframe',
            'website_description': website_description,
        })
        self.assertEqual(test_partner.website_description, website_description)

    def test_conditional_visibility_code(self):
        website_description = '''
            <section class="o_snippet_invisible o_conditional_hidden"
                data-visibility="conditional"
                data-visibility-value-logged=\'[{"value":"true","id":1}]\'
                data-visibility-selectors=\'html:not([data-logged="true" ]) body:not(.editor_enable) [data-visibility-id="logged_o_1" ]\'
                data-visibility-id="logged_o_1">
            </section>
        '''
        test_partner = self.env['res.partner'].create({
            'name': 'Partner with a conditional display',
            'website_description': website_description,
        })
        self.assertEqual(test_partner.website_description, website_description)
