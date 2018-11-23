import odoo.tests
# Part of Odoo. See LICENSE file for full copyright and licensing details.

@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_sale_tour(self):
        self.phantom_js("/web", "odoo.__DEBUG__.services['web_tour.tour'].run('sale_tour')", "odoo.__DEBUG__.services['web_tour.tour'].tours.sale_tour.ready", login="admin")

    def test_02_product_configurator(self):
        # group_product_variant: use the product configurator
        # group_sale_pricelist: display the pricelist to determine when it is changed after choosing
        #                       the partner
        self.env.ref('base.user_admin').write({
            'groups_id': [
                (4, self.env.ref('product.group_product_variant').id),
                (4, self.env.ref('product.group_sale_pricelist').id),
            ],
        })

        self.phantom_js("/web", "odoo.__DEBUG__.services['web_tour.tour'].run('sale_product_configurator_tour')", "odoo.__DEBUG__.services['web_tour.tour'].tours.sale_product_configurator_tour.ready", login="admin")

    def test_03_product_configurator_advanced(self):
        # group_product_variant: use the product configurator
        # group_sale_pricelist: display the pricelist to determine when it is changed after choosing
        #                       the partner
        self.env.ref('base.user_admin').write({
            'groups_id': [
                (4, self.env.ref('product.group_product_variant').id),
                (4, self.env.ref('product.group_sale_pricelist').id),
            ],
        })

        # Prepare relevant test data
        # This is not included in demo data to avoid useless noise
        product_attributes = self.env['product.attribute'].create([{
            'name': 'PA1',
            'type': 'radio',
            'create_variant': 'dynamic'
        }, {
            'name': 'PA2',
            'type': 'radio',
            'create_variant': 'always'
        }, {
            'name': 'PA3',
            'type': 'radio',
            'create_variant': 'dynamic'
        }, {
            'name': 'PA4',
            'type': 'select',
            'create_variant': 'no_variant'
        }, {
            'name': 'PA5',
            'type': 'select',
            'create_variant': 'no_variant'
        }, {
            'name': 'PA7',
            'type': 'color',
            'create_variant': 'no_variant'
        }, {
            'name': 'PA8',
            'type': 'radio',
            'create_variant': 'no_variant'
        }])

        product_attribute_values = self.env['product.attribute.value'].create([{
            'name': 'PAV' + str(i),
            'is_custom': i == 9,
            'attribute_id': product_attribute.id
        } for i in range(1, 11) for product_attribute in product_attributes])

        product_template_attribute_lines = self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attribute.id,
            'product_tmpl_id': self.env.ref("product.product_product_4").id,
            'value_ids': [(6, 0, product_attribute_values.filtered(
                lambda product_attribute_value: product_attribute_value.attribute_id == product_attribute
            ).ids)]
        } for product_attribute in product_attributes])

        self.env.ref("product.product_product_4").update({
            'attribute_line_ids': [(4, product_template_attribute_line.id) for product_template_attribute_line in product_template_attribute_lines]
        })

        self.phantom_js("/web", "odoo.__DEBUG__.services['web_tour.tour'].run('sale_product_configurator_advanced_tour')", "odoo.__DEBUG__.services['web_tour.tour'].tours.sale_product_configurator_advanced_tour.ready", login="admin")
