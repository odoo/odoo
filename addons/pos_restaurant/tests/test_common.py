from odoo import Command
from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon


class TestPoSRestaurantDataHttpCommon(TestPointOfSaleDataHttpCommon):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.setup_test_printer(self)
        self.edit_test_pos_config(self)
        self.setup_test_floors(self)
        self.setup_test_tables(self)

    def setup_test_tables(self):
        self.env['restaurant.table'].create([{
            'table_number': 5,
            'floor_id': self.main_floor.id,
            'seats': 4,
            'position_h': 100,
            'position_v': 100,
        },
        {
            'table_number': 4,
            'floor_id': self.main_floor.id,
            'seats': 4,
            'shape': 'square',
            'position_h': 350,
            'position_v': 100,
        },
        {
            'table_number': 2,
            'floor_id': self.main_floor.id,
            'seats': 4,
            'position_h': 250,
            'position_v': 100,
        },
        {

            'table_number': 1,
            'floor_id': self.second_floor.id,
            'seats': 4,
            'shape': 'square',
            'position_h': 100,
            'position_v': 150,
        },
        {
            'table_number': 3,
            'floor_id': self.second_floor.id,
            'seats': 4,
            'position_h': 100,
            'position_v': 250,
        }])

    def edit_test_pos_config(self):
        self.pos_config.floor_ids.unlink()
        self.pos_config.write({
            'fiscal_position_ids': [Command.clear()],
            'module_pos_restaurant': True,
            'iface_splitbill': True,
            'iface_printbill': True,
            'is_order_printer': True,
            'printer_ids': [(4, self.printer.id)],
            'iface_tipproduct': False,
        })

    def setup_test_printer(self):
        self.printer = self.env['pos.printer'].create({
            'name': 'Preparation Printer',
            'epson_printer_ip': '127.0.0.1',
            'printer_type': 'epson_epos',
            'product_categories_ids': [self.category_things.id, self.category_items.id],
        })

    def setup_test_floors(self):
        self.main_floor = self.env['restaurant.floor'].create({
            'name': 'Main Floor',
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.second_floor = self.env['restaurant.floor'].create({
            'name': 'Second Floor',
            'pos_config_ids': [(4, self.pos_config.id)],
        })

    def setup_test_products(self):
        super().setup_test_products(self)
        # Unset all taxes for better readability, taxes are tested in main
        # point_of_sale module, also set rounded prices to ease testing
        self.env['product.template'].search([]).write({'taxes_id': [Command.clear()]})
        self.product_awesome_article.write({'list_price': 10.0})
        self.product_awesome_item.write({'list_price': 20.0})
        self.product_awesome_thing.write({'list_price': 30.0})
