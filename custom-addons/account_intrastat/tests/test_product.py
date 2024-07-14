from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestProduct(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.product = cls.env['product.product'].create({'name': 'A product'})
        cls.intrastat_code = cls.env['account.intrastat.code'].sudo().create({
            'name': 'An Intrastat Code',
            'type': 'commodity',
            'code': 1,
            'supplementary_unit': 'l',
        })

    def test_changing_intrastat_field_values_on_product(self):
        """ Test that check we can modify intrastat values in form view
            for product.product object.
        """
        with Form(self.product) as form:
            form.intrastat_code_id = self.intrastat_code
            form.intrastat_supplementary_unit_amount = 10
            form.intrastat_origin_country_id = self.env.ref('base.nl')

        self.assertRecordValues(
            self.product,
            [{
                'intrastat_code_id': self.intrastat_code.id,
                'intrastat_supplementary_unit': 'l',
                'intrastat_supplementary_unit_amount': 10,
                'intrastat_origin_country_id': self.env.ref('base.nl').id,
            }]
        )

    def test_changing_intrastat_field_values_on_product_template(self):
        """ Test that check we can modify intrastat values in form view
            for product.template object. Modified values should be changed
            in the product.product object related to the template.
            We have to instanciate Form view twice in the test because by
            changing the intrastat_code_id, we set other fields (like
            intrastat_supplementary_unit_amount) to visible.
        """
        with Form(self.product.product_tmpl_id) as form:
            form.intrastat_code_id = self.intrastat_code

        with Form(self.product.product_tmpl_id) as form:
            form.intrastat_supplementary_unit_amount = 10
            form.intrastat_origin_country_id = self.env.ref('base.nl')

        self.assertRecordValues(
            self.product,
            [{
                'intrastat_code_id': self.intrastat_code.id,
                'intrastat_supplementary_unit': 'l',
                'intrastat_supplementary_unit_amount': 10,
                'intrastat_origin_country_id': self.env.ref('base.nl').id,
            }]
        )
