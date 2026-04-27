from odoo.tests import Form, tagged
from ...product_barcodelookup.tests.test_barcodelookup_flow import TestBarcodelookup


@tagged('post_install', '-at_install')
class TestWebsiteBarcodelookup(TestBarcodelookup):

    def test_01_website_barcodelookup_flow(self):
        self.env['product.public.category'].create({'name': 'Barcode Category'})
        with self.mockBarcodelookupAutofill():
            self.start_tour('/', 'test_01_website_barcodelookup_flow', login="admin")
        product = self.env['product.template'].sudo().search([('name', '=', 'Odoo Scale up')], limit=1)
        self._verify_product_data(product, normalized_view=True)
        #  Product created from website should be published by default if category is selected.
        self.assertTrue(product.is_published)

    def test_website_barcodelookup_description_ecommerce(self):
        with self.mockBarcodelookupAutofill():
            templ_form = Form(self.env['product.template'])
            templ_form.description_ecommerce = 'hello world'
            templ_form.barcode = "710535977349"
            self.assertEqual(templ_form.description_ecommerce, 'hello world')

            templ_form = Form(self.env['product.template'])
            templ_form.barcode = "710535977349"
            self.assertEqual(templ_form.description_ecommerce, 'Test Description')
