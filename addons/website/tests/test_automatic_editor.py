from odoo.tests import tagged
from odoo.addons.website.tests.test_configurator import TestConfiguratorCommon

@tagged('post_install', '-at_install')
class TestAutomaticEditor(TestConfiguratorCommon):

    def test_01_automatic_editor_on_new_website(self):
        # We create a lang because if the new website is displayed in this lang
        # instead of the website's default one, the editor won't automatically
        # start.
        # If not enabled (like in demo data), landing on res.config will try
        # to disable module_sale_quotation_builder and raise an issue
        group_order_template = self.env.ref('sale_management.group_sale_order_template', raise_if_not_found=False)
        if group_order_template:
            self.env.ref('base.group_user').write({"implied_ids": [(4, group_order_template.id)]})
        self.env['res.lang'].create({
            'name': 'Parseltongue',
            'code': 'pa_GB',
            'iso_code': 'pa_GB',
            'url_code': 'pa_GB',
        })
        self.start_tour('/', 'automatic_editor_on_new_website', login='admin')
