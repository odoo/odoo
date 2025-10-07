from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestWebsiteSaleSearchbar(HttpCase):
    def test_searchbar(self):
        self.car = self.env['product.template'].create({
            'name': 'Car',
            'barcode': '111111111',
            'list_price': '200',
            'description_sale': 'BMW Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industrys standard dummy text ever since the 1500s, when an unknown printer took Mercedes a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Hundai Aldus PageMaker including versions of Lorem Ipsum.',
            'is_published': True
        })
        self.color_attribute = self.env['product.attribute'].create({'name': 'Color', 'sequence': 1, 'display_type': 'color'})
        self.color_red = self.env['product.attribute.value'].create({
            'name': 'Red',
            'attribute_id': self.color_attribute.id,
            'sequence': 1,
            'html_color': '#ff0000'
        })
        self.car_color_attribute_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.car.id,
            'attribute_id': self.color_attribute.id,
            'value_ids': [(6, 0, [self.color_red.id])],
        })
        self.start_tour("/", 'test_searchbar_search_functionality', login="admin")
