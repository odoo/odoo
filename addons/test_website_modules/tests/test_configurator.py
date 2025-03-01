# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

import odoo.tests
from odoo.addons.website.tests.test_configurator import TestConfiguratorCommon


@odoo.tests.common.tagged('post_install', '-at_install')
class TestConfigurator(TestConfiguratorCommon):

    def test_01_configurator_flow(self):
        # If not enabled (like in demo data), landing on res.config will try
        # to disable module_sale_quotation_builder and raise an issue
        group_order_template = self.env.ref('sale_management.group_sale_order_template', raise_if_not_found=False)
        if group_order_template:
            self.env.ref('base.group_user').write({"implied_ids": [(4, group_order_template.id)]})
        self.start_tour('/web#action=website.action_website_configuration', 'configurator_flow', login="admin")

    def test_02_configurator_with_filters(self):
        # Patch team snippet to use filters and shapes
        self.env['ir.ui.view'].create({
            'name': "Patch",
            'type': 'qweb',
            'inherit_id': self.env.ref('website.s_company_team').id,
            'mode': 'extension',
            'arch': """<data>
<xpath expr="(//img)[2]" position="attributes">
    <attribute name="src"/>
    <attribute name="data-original-src">/web/image/website.s_company_team_image_2</attribute>
    <attribute name="data-gl-filter">blur</attribute>
</xpath>
<xpath expr="(//img)[3]" position="attributes">
    <attribute name="src">/web_editor/image_shape/website.s_company_team_image_3/web_editor/pattern/pattern_waves_3.svg?c1=o-color-1&amp;c2=o-color-2&amp;c3=o-color-3&amp;c5=o-color-1</attribute>
    <attribute name="data-shape">web_editor/pattern/pattern_waves_3</attribute>
    <attribute name="data-original-mimetype">image/jpeg</attribute>
    <attribute name="data-file-name">s_text_image.svg</attribute>
    <attribute name="data-shape-colors">o-color-1;o-color-2;o-color-3;;o-color-1</attribute>
</xpath>
<xpath expr="(//img)[4]" position="attributes">
    <attribute name="src"/>
    <attribute name="data-original-src">/web_editor/image_shape/website.s_company_team_image_4/web_editor/pattern/pattern_waves_3.svg?c1=o-color-1&amp;c2=o-color-2&amp;c3=o-color-3&amp;c5=o-color-1</attribute>
    <attribute name="data-gl-filter">1977</attribute>
    <attribute name="data-shape">web_editor/pattern/pattern_waves_3</attribute>
    <attribute name="data-original-mimetype">image/jpeg</attribute>
    <attribute name="data-file-name">s_text_image.svg</attribute>
    <attribute name="data-shape-colors">o-color-1;o-color-2;o-color-3;;o-color-1</attribute>
</xpath>
            </data>"""
        })
        self.start_tour('/web#action=website.action_website_configuration', 'configurator_flow', login="admin")
        website = self.env['website'].search([('name', '=', 'Website Test')])
        page = self.env['website.page'].search([('website_id', '=', website.id), ('name', '=', 'About Us')])
        body = html.fromstring(page.arch)
        for image in body.xpath('//section.s_company_team/img'):
            self.assertTrue(image.attrib['src'], "Source must have been set by configurator")
