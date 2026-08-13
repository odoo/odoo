# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time

from odoo.addons.stock.tests.test_generate_serial_numbers import StockGenerateCommon
from odoo.tools.misc import get_lang


class TestStockLot(StockGenerateCommon):

    def _import_lots(self, lots, move):
        location_id = move.location_id
        move_lines_vals = move.split_lots(lots)
        move_lines_commands = move._generate_serial_move_line_commands(move_lines_vals, location_dest_id=location_id)
        move.update({'move_line_ids': move_lines_commands})

    def test_set_multiple_lot_name_with_expiration_date_01(self):
        """ In a move line's `lot_name` field, pastes a list of lots and expiration dates.
        Checks the values are correctly interpreted and the expiration dates are correctly created
        depending of the user lang's date format.
        """
        product_lot = self.env['product.product'].create({
            'name': 'Tracked by Lot Numbers',
            'tracking': 'lot',
            'is_storable': True,
            'use_expiration_date': True,
        })
        user_lang = self.env['res.lang'].browse([get_lang(self.env).id])
        # Try first with the "day/month/year" date format.
        user_lang.date_format = "%d/%m/%y"
        list_lot_and_qty = [
            {'lot_name': "ln01", "date": "03/05/25", "datetime": datetime.strptime('2025-05-03', "%Y-%m-%d")},
            {'lot_name': "ln02", "date": "06/05/25", "datetime": datetime.strptime('2025-05-06', "%Y-%m-%d")},
            {'lot_name': "ln03", "date": "03/06/25", "datetime": datetime.strptime('2025-06-03', "%Y-%m-%d")},
            {'lot_name': "ln04", "date": "06/06/25", "datetime": datetime.strptime('2025-06-06', "%Y-%m-%d")},
            {'lot_name': "ln05", "date": "03/07/25", "datetime": datetime.strptime('2025-07-03', "%Y-%m-%d")},
        ]
        list_as_string = '\n'.join([f'{line["lot_name"]};{line["date"]}' for line in list_lot_and_qty])
        move = self.get_new_move(product=product_lot)
        self._import_lots(list_as_string, move)
        self.assertEqual(len(move.move_line_ids), len(list_lot_and_qty))
        for i, move_line in enumerate(move.move_line_ids):
            self.assertEqual(move_line.lot_name, list_lot_and_qty[i]['lot_name'])
            self.assertEqual(move_line.quantity, 1)
            self.assertEqual(move_line.expiration_date, list_lot_and_qty[i]["datetime"])

        # Same test but with with the "month/day/year" date format this time.
        user_lang.date_format = "%m/%d/%y"
        list_lot_and_qty = [
            {'lot_name': "ln01", "date": "03/05/25", "datetime": datetime.strptime('2025-03-05', "%Y-%m-%d")},
            {'lot_name': "ln02", "date": "06/05/25", "datetime": datetime.strptime('2025-06-05', "%Y-%m-%d")},
            {'lot_name': "ln03", "date": "03/06/25", "datetime": datetime.strptime('2025-03-06', "%Y-%m-%d")},
            {'lot_name': "ln04", "date": "06/06/25", "datetime": datetime.strptime('2025-06-06', "%Y-%m-%d")},
            {'lot_name': "ln05", "date": "03/07/25", "datetime": datetime.strptime('2025-03-07', "%Y-%m-%d")},
        ]
        list_as_string = '\n'.join([f'{line["lot_name"]};{line["date"]}' for line in list_lot_and_qty])
        move = self.get_new_move(product=product_lot)
        self._import_lots(list_as_string, move)
        self.assertEqual(len(move.move_line_ids), len(list_lot_and_qty))
        for i, move_line in enumerate(move.move_line_ids):
            self.assertEqual(move_line.lot_name, list_lot_and_qty[i]['lot_name'])
            self.assertEqual(move_line.quantity, 1)
            self.assertEqual(move_line.expiration_date, list_lot_and_qty[i]["datetime"])

    def test_set_multiple_lot_name_with_expiration_date_02_product_dont_use_expiration_date(self):
        """ In a move line's `lot_name` field, pastes a list of lots and expiration dates.
        Checks the values are correctly interpreted and since the product doesn't use expiration
        date, the expiration dates should be ignored.
        """
        product_lot = self.env['product.product'].create({
            'name': 'Tracked by Lot Numbers',
            'tracking': 'lot',
            'is_storable': True,
        })
        user_lang = self.env['res.lang'].browse([get_lang(self.env).id])
        # Try first with the "day/month/year" date format.
        user_lang.date_format = "%d/%m/%y"
        list_lot_and_qty = [
            {'lot_name': "ln01", "date": "03/05/25", "datetime": datetime.strptime('2025-05-03', "%Y-%m-%d")},
            {'lot_name': "ln02", "date": "06/05/25", "datetime": datetime.strptime('2025-05-06', "%Y-%m-%d")},
            {'lot_name': "ln03", "date": "03/06/25", "datetime": datetime.strptime('2025-06-03', "%Y-%m-%d")},
            {'lot_name': "ln04", "date": "06/06/25", "datetime": datetime.strptime('2025-06-06', "%Y-%m-%d")},
            {'lot_name': "ln05", "date": "03/07/25", "datetime": datetime.strptime('2025-07-03', "%Y-%m-%d")},
        ]
        list_as_string = '\n'.join([f'{line["lot_name"]};{line["date"]}' for line in list_lot_and_qty])
        move = self.get_new_move(product=product_lot)
        self._import_lots(list_as_string, move)
        self.assertEqual(len(move.move_line_ids), len(list_lot_and_qty))
        for i, move_line in enumerate(move.move_line_ids):
            self.assertEqual(move_line.lot_name, list_lot_and_qty[i]['lot_name'])
            self.assertEqual(move_line.quantity, 1)
            self.assertEqual(move_line.expiration_date, False)

    def test_set_multiple_lot_name_with_expiration_date_03_adaptive_date_format(self):
        """ Checks if the given dates don't follow the user lang's date format, the created expiration
        date will follow the first given date's format (at least in the scope of the limitations).
        """
        product_lot = self.env['product.product'].create({
            'name': 'Tracked by Lot Numbers',
            'tracking': 'lot',
            'is_storable': True,
            'use_expiration_date': True,
        })
        user_lang = self.env['res.lang'].browse([get_lang(self.env).id])
        # Month first in the system but day in the first place in the given dates.
        user_lang.date_format = "%m/%d/%y"
        list_lot_and_qty = [
            {'lot_name': "ln01", "date": "30/05/25", "datetime": datetime.strptime('2025-05-30', "%Y-%m-%d")},
            {'lot_name': "ln02", "date": "06/05/25", "datetime": datetime.strptime('2025-05-06', "%Y-%m-%d")},
            {'lot_name': "ln03", "date": "01/06/25", "datetime": datetime.strptime('2025-06-01', "%Y-%m-%d")},
            {'lot_name': "ln04", "date": "06/06/25", "datetime": datetime.strptime('2025-06-06', "%Y-%m-%d")},
            {'lot_name': "ln05", "date": "01/07/25", "datetime": datetime.strptime('2025-07-01', "%Y-%m-%d")},
        ]
        list_as_string = '\n'.join([f'{line["lot_name"]};{line["date"]}' for line in list_lot_and_qty])
        move = self.get_new_move(product=product_lot)
        self._import_lots(list_as_string, move)
        self.assertEqual(len(move.move_line_ids), len(list_lot_and_qty))
        for i, move_line in enumerate(move.move_line_ids):
            self.assertEqual(move_line.lot_name, list_lot_and_qty[i]['lot_name'])
            self.assertEqual(move_line.quantity, 1)
            self.assertEqual(move_line.expiration_date, list_lot_and_qty[i]["datetime"])

        # Now, tries with day first but the year is at the first place in the given dates.
        user_lang.date_format = "%d/%m/%y"
        list_lot_and_qty = [
            {'lot_name': "ln01", "date": "89/05/04", "datetime": datetime.strptime('1989-05-04', "%Y-%m-%d")},
            {'lot_name': "ln02", "date": "10/05/06", "datetime": datetime.strptime('2010-05-06', "%Y-%m-%d")},
            {'lot_name': "ln03", "date": "12/06/15", "datetime": datetime.strptime('2012-06-15', "%Y-%m-%d")},
            {'lot_name': "ln04", "date": "30/06/06", "datetime": datetime.strptime('2030-06-06', "%Y-%m-%d")},
            {'lot_name': "ln05", "date": "04/07/08", "datetime": datetime.strptime('2004-07-08', "%Y-%m-%d")},
        ]
        list_as_string = '\n'.join([f'{line["lot_name"]};{line["date"]}' for line in list_lot_and_qty])
        move = self.get_new_move(product=product_lot)
        self._import_lots(list_as_string, move)
        self.assertEqual(len(move.move_line_ids), len(list_lot_and_qty))
        for i, move_line in enumerate(move.move_line_ids):
            self.assertEqual(move_line.lot_name, list_lot_and_qty[i]['lot_name'])
            self.assertEqual(move_line.quantity, 1)
            self.assertEqual(move_line.expiration_date, list_lot_and_qty[i]["datetime"])

    def test_set_multiple_lot_name_with_expiration_date_04_written_months(self):
        """ Checks the expiration date is correctly created when the month is written in letters.
        """
        product_lot = self.env['product.product'].create({
            'name': 'Tracked by Lot Numbers',
            'tracking': 'lot',
            'is_storable': True,
            'use_expiration_date': True,
        })
        list_lot_and_qty = [
            {'lot_name': "ln01", "date": "01 march 2077", "datetime": datetime.strptime('2077-03-01', "%Y-%m-%d")},
            {'lot_name': "ln02", "date": "11 april 2077", "datetime": datetime.strptime('2077-04-11', "%Y-%m-%d")},
            {'lot_name': "ln03", "date": "10 december 2077", "datetime": datetime.strptime('2077-12-10', "%Y-%m-%d")},
        ]
        list_as_string = '\n'.join([f'{line["lot_name"]};{line["date"]}' for line in list_lot_and_qty])
        move = self.get_new_move(product=product_lot)
        self._import_lots(list_as_string, move)
        self.assertEqual(len(move.move_line_ids), len(list_lot_and_qty))
        for i, move_line in enumerate(move.move_line_ids):
            self.assertEqual(move_line.lot_name, list_lot_and_qty[i]['lot_name'])
            self.assertEqual(move_line.quantity, 1)
            self.assertEqual(move_line.expiration_date, list_lot_and_qty[i]["datetime"])

    @freeze_time('2023-04-17')
    def test_set_multiple_lot_name_with_expiration_date_05_wrong_given_date(self):
        """ This test ensure when the given dates aren't correctly written, the
        full string is used as the lot's name.
        """
        today = datetime(day=17, month=4, year=2023)
        product_lot = self.env['product.product'].create({
            'name': 'Tracked by Lot Numbers',
            'tracking': 'lot',
            'is_storable': True,
            'use_expiration_date': True,
        })
        list_lot_and_qty = [
            "ln01\t31/12",  # Day is missing but the date is valid.
            "ln02\t1989-04",  # Day is missing but the date is valid.
            "ln03\t01",  # Single number: will be used as the quantity.
            "ln04\t1989",  # Single number: will be used as the quantity.
            "ln05\t1989.04",  # Signle number (with decimal): will be used as the quantity.
            "ln06\t1989+04",  # Wrong, all the string will be used as the lot name.
            "ln07\tdacember",  # Typo, all the string will be used as the lot name.
            "ln08\tdecember",  # Day and year are missing but the date is valid.
        ]
        list_as_string = '\n'.join(list_lot_and_qty)
        move = self.get_new_move(product=product_lot)
        self._import_lots(list_as_string, move)
        self.assertEqual(len(move.move_line_ids), len(list_lot_and_qty))

        self.assertEqual(move.move_line_ids[0].lot_name, "ln01")
        self.assertEqual(move.move_line_ids[0].quantity, 1)
        self.assertEqual(move.move_line_ids[0].expiration_date, datetime(day=31, month=12, year=2023))

        self.assertEqual(move.move_line_ids[1].lot_name, "ln02")
        self.assertEqual(move.move_line_ids[1].quantity, 1)
        self.assertEqual(move.move_line_ids[1].expiration_date, datetime(day=17, month=4, year=1989))

        self.assertEqual(move.move_line_ids[2].lot_name, "ln03")
        self.assertEqual(move.move_line_ids[2].quantity, 1)
        self.assertEqual(move.move_line_ids[2].expiration_date, today)

        self.assertEqual(move.move_line_ids[3].lot_name, "ln04")
        self.assertEqual(move.move_line_ids[3].quantity, 1989)
        self.assertEqual(move.move_line_ids[3].expiration_date, today)

        self.assertEqual(move.move_line_ids[4].lot_name, "ln05")
        self.assertEqual(move.move_line_ids[4].quantity, 1989.04)
        self.assertEqual(move.move_line_ids[4].expiration_date, today)

        self.assertEqual(move.move_line_ids[5].lot_name, "ln06\t1989+04")
        self.assertEqual(move.move_line_ids[5].quantity, 1)
        self.assertEqual(move.move_line_ids[5].expiration_date, today)

        self.assertEqual(move.move_line_ids[6].lot_name, "ln07\tdacember")
        self.assertEqual(move.move_line_ids[6].quantity, 1)
        self.assertEqual(move.move_line_ids[6].expiration_date, today)

        self.assertEqual(move.move_line_ids[7].lot_name, "ln08")
        self.assertEqual(move.move_line_ids[7].quantity, 1)
        self.assertEqual(move.move_line_ids[7].expiration_date, datetime(day=17, month=12, year=2023))

    def test_set_multiple_lot_name_with_expiration_date_06_one_line(self):
        """ Checks the pasted data are correctly parsed even if the user pastes only one line.
        """
        product_lot = self.env['product.product'].create({
            'name': 'Tracked by Lot Numbers',
            'tracking': 'lot',
            'is_storable': True,
            'use_expiration_date': True,
        })
        user_lang = self.env['res.lang'].browse([get_lang(self.env).id])
        user_lang.date_format = "%d/%m/%y"
        for lot_name in ["lot-001;20;4 Aug 2048", "lot-001\t04/08/2048\t20"]:
            move = self.get_new_move(product=product_lot)
            self._import_lots(lot_name, move)
            self.assertEqual(move.move_line_ids.lot_name, "lot-001")
            self.assertEqual(move.move_line_ids.quantity, 20)
            self.assertEqual(move.move_line_ids.expiration_date, datetime(day=4, month=8, year=2048))
