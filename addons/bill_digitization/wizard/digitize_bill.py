# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Sruthi Renjith (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
import io
import pytesseract
import re
from PIL import Image
from odoo import Command, fields, models, _
from odoo.exceptions import ValidationError


class DigitizeBill(models.TransientModel):
    """ To read documents and to convert into vendor bills """
    _name = "digitize.bill"
    _description = "Digitize Bill"

    bill = fields.Binary(string="Document", required=True,
                         help="Choose a scanned document")
    file_name = fields.Char(string="File Name", help="Name of the file")

    def record_lines(self, product_lines_newline_name_qty_price_amount,
                     product_lines_name_qty_amount,
                     product_lines_qty_name_amount,
                     product_lines_name_qty_price_amount1,
                     product_lines_name_price_qty_amount_with_dollar,
                     product_lines_name_price_qty_amount,
                     product_lines_name_amount,
                     product_lines_name_qty_price_amount2,
                     product_lines_double_line_name,
                     product_lines_code_name,
                     product_lines_quantity_part,
                     product_lines_vendor_bill_pattern,
                     product_lines_quantity_price_amount_pattern,
                     product_lines_quantity_price_amount_pattern2,
                     product_line_name_with_extra_line):
        """ Function to extract bill data from text read by pytesseract """
        products = []
        price = []
        subtotal = []
        quantity = []
        if (product_lines_newline_name_qty_price_amount or
                product_lines_name_qty_price_amount1 or
                product_lines_name_qty_price_amount2):
            if product_lines_name_qty_price_amount1:
                product_lines_newline_name_qty_price_amount = (
                    product_lines_name_qty_price_amount1)
            if product_lines_name_qty_price_amount2:
                product_lines_newline_name_qty_price_amount = (
                    product_lines_name_qty_price_amount2)
            # Fetching products and create new ones
            products = [self.env['product.product'].search(
                [('name', '=', line[0])], limit=1) or
                        self.env['product.product'].create(
                            {'name': line[0]})
                        for line in
                        product_lines_newline_name_qty_price_amount]
            # Creating lists for prices and subtotals
            price = [line[2] for line in
                     product_lines_newline_name_qty_price_amount]
            subtotal = [line[3] for line in
                        product_lines_newline_name_qty_price_amount]
        elif product_lines_name_qty_amount:
            # Fetching products and create new ones
            products = [
                self.env['product.product'].search([('name', '=', line[0])],
                                                   limit=1) or
                self.env['product.product'].create({'name': line[0]})
                for line in product_lines_name_qty_amount]
            # Calculating unit prices
            price = [
                float(line[2]) / float(line[1]) if float(line[1]) != 0 else 0
                for line in product_lines_name_qty_amount]
            # Creating a list for subtotals
            subtotal = [line[2] for line in product_lines_name_qty_amount]
        elif product_lines_qty_name_amount:
            # Fetching products and create new ones
            products = [
                self.env['product.product'].search([('name', '=', line[1])],
                                                   limit=1) or
                self.env['product.product'].create({'name': line[1]})
                for line in product_lines_qty_name_amount]
            # Calculating unit prices
            price = [
                float(line[2]) / float(line[0]) if float(line[0]) != 0 else 0
                for line in product_lines_qty_name_amount]
            # Creating a list for subtotals
            subtotal = [line[2] for line in product_lines_qty_name_amount]
        elif (product_lines_name_price_qty_amount_with_dollar or
              product_lines_name_price_qty_amount):
            if product_lines_name_price_qty_amount:
                product_lines_name_price_qty_amount_with_dollar = (
                    product_lines_name_price_qty_amount)
            # Fetching products and create new ones
            products = [
                self.env['product.product'].search([('name', '=', line[0])],
                                                   limit=1) or
                self.env['product.product'].create({'name': line[0]})
                for line in product_lines_name_price_qty_amount_with_dollar]
            # Extracting item prices and amounts
            price = [line[1].replace('$', '') if '$' in line[1] else line[1]
                     for line in
                     product_lines_name_price_qty_amount_with_dollar]
            subtotal = [line[3].replace('$', '') if '$' in line[3] else line[3]
                        for line in
                        product_lines_name_price_qty_amount_with_dollar]
        elif product_lines_name_amount:
            # Fetching products and create new ones
            products = [
                self.env['product.product'].search([('name', '=', line[0])],
                                                   limit=1) or
                self.env['product.product'].create({'name': line[0]})
                for line in product_lines_name_amount]
            # Extracting item amounts and create a list for subtotals
            subtotal = [line[1].replace('$', '') if '$' in line[1] else line[1]
                        for line in product_lines_name_amount]
        elif product_lines_code_name:
            name_list_one = []
            if product_line_name_with_extra_line:
                for code, name in product_line_name_with_extra_line:
                    product_info = f"{code} {name}"
                    name_list_one.append(product_info)
            names = [item.strip() for item in
                     product_lines_code_name[0].split('\n') if item.strip()]
            if name_list_one and len(name_list_one) > len(names):
                names = name_list_one
            if product_lines_quantity_part:
                order_lines = [line.strip() for line in
                               product_lines_quantity_part[0].split('\n') if
                               line.strip()]
            elif product_lines_quantity_price_amount_pattern:
                order_lines = [line.strip() for line in
                               product_lines_quantity_price_amount_pattern[
                                   0].split('\n') if
                               line.strip()]
            elif product_lines_quantity_price_amount_pattern2:
                order_lines = [line.strip() for line in
                               product_lines_quantity_price_amount_pattern2[
                                   0].split('\n') if
                               line.strip()]
            else:
                order_lines = []
            # Create the 'products' list
            products = [
                self.env['product.product'].search([('name', '=', name)],
                                                   limit=1) or
                self.env['product.product'].create({'name': name})
                for name in names]
            # Creating the unit price list
            price = [float(line.split()[1].replace(',', '')) if line else 0 for
                     line in order_lines]
            # Calculating and Creating the 'subtotal' list
            subtotal = [float(line.split()[1].replace(',', '')) * float(
                line.split()[0]) if line else 0 for line in order_lines]
            # Creating the quantity list
            quantity = [float(line.split()[0]) if line else 0 for line in
                        order_lines]
        elif product_lines_vendor_bill_pattern:
            products = [
                self.env['product.product'].search([('name', '=', item[0])],
                                                   limit=1) or
                self.env['product.product'].create({'name': item[0]})
                for item in product_lines_vendor_bill_pattern]
            quantity = [float(item[1]) for item in
                        product_lines_vendor_bill_pattern]
            price = [float(item[2]) for item in
                     product_lines_vendor_bill_pattern]
            subtotal = [float(item[2]) * float(item[1]) for item in
                        product_lines_vendor_bill_pattern]
        if product_lines_double_line_name:
            for line in product_lines_double_line_name:
                product_name = line[0] + ' ' + line[1]
                product = self.env['product.product'].search(
                    [('name', '=', product_name)], limit=1)
                if not product:
                    product = self.env['product.product'].create({
                        'name': product_name
                    })
                products.append(product)
                if '$' in line[5]:
                    line[5] = line[5].replace('$', '')
                subtotal.append(line[5])
                item_price = line[4].replace('$', '') if '$' in line[4] else \
                    line[4]
                price.append(item_price)
        if bool(quantity):
            # Looping lists to create product line values
            move_line_vals = [
                (0, 0, {
                    'product_id': product.id,
                    'name': 'Outside Bill',
                    'price_unit': price_amount,
                    'price_subtotal': total_amount,
                    'quantity': qty,
                    'tax_ids': [Command.set([])],
                    'move_id': self.id,
                })
                for product, price_amount, total_amount, qty in
                zip(products, price, subtotal, quantity)
            ]
        elif bool(price):
            # Looping three lists to create product line values
            move_line_vals = [
                (0, 0, {
                    'product_id': product.id,
                    'name': 'Outside Bill',
                    'price_unit': price_amount,
                    'price_subtotal': total_amount,
                    'tax_ids': [Command.set([])],
                    'move_id': self.id,
                })
                for product, price_amount, total_amount in
                zip(products, price, subtotal)
            ]
        else:
            move_line_vals = [
                (0, 0, {
                    'product_id': product.id,
                    'name': 'Outside Bill',
                    'price_subtotal': total_amount,
                    'tax_ids': [Command.set([])],
                    'move_id': self.id,
                })
                for product, total_amount in zip(products, subtotal)
            ]
        return move_line_vals

    def create_record(self, text):
        """ Function to create vendor bill """
        # Different patterns or regular expressions to identify the data
        # from the text
        newline_name_qty_price_amount = \
            r'\n([A-Za-z ]+) (\d+) (\d+\.\d{2}) (\d+\.\d{2})'
        name_qty_amount = r'\n([A-Za-z ]+) (\d+) (\d+\.\d{2})'
        qty_name_amount = r'\n(\d+) ([A-Za-z ]+) (\d+\.\d{2})'
        name_qty_price_amount1 = r'\s*([A-Za-z() \d]+) (\d+) (\d+) (\d+)'
        name_price_qty_amount_with_dollar = \
            r'\n(\$?\w+(?: \w+)*) (\$[\d.]+) (\d+) (\$[\d.]+)'
        name_price_qty_amount = \
            r'\n(\$?\w+(?: \w+)*) (\[\d.]+) (\d+) (\[\d.]+)'
        name_amount = r'\n(\$?\w+(?: \w+)*) (\d+\.\d{2})'
        name_qty_price_amount2 = r"([\w\s]+)\s+(\d+)\s+(\d+)\s+\$(\d+)"
        double_line_name = \
            r'([\w\s]+)\s([\w\s]+)\s*([\w\s]+)\s*(\d+)\s*(\$\d+' \
            r'\.\d{2})\s*(\d+\.\d{2})'
        code_name = r'Description\n([\s\S]*?)(?=\n\n)'
        quantity_price_pattern = r'Quantity Unit Price Taxes\n([\s\S]*?)(?=\n\n)'
        vendor_bill_pattern = r'\[[A-Z0-9-]+\] (.+?) (\d+\.\d+) (\d+\.\d+) (\d+\.\d+%?) \$ (\d+\.\d+)'
        quantity_price_amount_pattern = r'Quantity Unit Price Taxes Amount\n((?:\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+% \$\s+\d+\.\d+\n)+)'
        quantity_price_amount_pattern2 = r'Quantity Unit Price Taxes Amount([\s\S]*?)(?:Untaxed Amount|Tax|Total|$)'
        name_with_extra_line = r'\[([A-Z0-9-]+)\] (.+)'

        # Pattern to match date and bill number from the text
        date_pattern = r'\d{1,2}/\d{1,2}/\d{2,4}'
        bill_no_pattern = r'Bill\sNo\.: (\d{4})'
        # Pattern to match the year format of date
        # (two digit or four digit format)
        year_pattern = re.compile(r'\d{2}')
        # Matching each pattern with the text and fetching the matching
        # data from it
        try:
            product_lines_newline_name_qty_price_amount = re.findall(
                newline_name_qty_price_amount, text)
            product_lines_name_qty_amount = re.findall(name_qty_amount, text)
            product_lines_qty_name_amount = re.findall(qty_name_amount, text)
            product_lines_name_qty_price_amount1 = re.findall(
                name_qty_price_amount1, text)
            product_lines_name_price_qty_amount_with_dollar = re.findall(
                name_price_qty_amount_with_dollar,
                text)
            product_lines_name_price_qty_amount = re.findall(
                name_price_qty_amount, text)
            product_lines_name_amount = re.findall(name_amount, text)
            product_lines_name_qty_price_amount2 = re.findall(
                name_qty_price_amount2, text)
            product_lines_double_line_name = re.findall(double_line_name, text)
            date_match = re.search(date_pattern, text)
            bill_no_match = re.search(bill_no_pattern, text)
            product_lines_code_name = re.findall(code_name, text)
            product_lines_quantity_part = re.findall(
                quantity_price_pattern, text)
            product_lines_vendor_bill_pattern = re.findall(
                vendor_bill_pattern, text)
            product_lines_quantity_price_amount_pattern = re.findall(
                quantity_price_amount_pattern, text)
            product_lines_quantity_price_amount_pattern2 = re.findall(
                quantity_price_amount_pattern2, text)
            product_line_name_with_extra_line = re.findall(
                name_with_extra_line, text)
        except Exception:
            raise ValidationError(_("Cannot find the pattern"))
        date_object = ''
        if date_match:
            # Reading the date value if the date pattern match any data
            date_value = date_match.group()
            match = year_pattern.search(date_value)
            if date_value == '%d/%m/%y' or date_value == '%d/%m/%Y':
                date_object = fields.datetime.strptime(
                    date_value, '%d/%m/%y') if match and len(
                    date_value.split('/')[
                        -1]) == 2 else fields.datetime.strptime(
                    date_value, '%d/%m/%Y')
            elif date_value == '%m/%d/%y' or date_value == '%m/%d/%Y':
                date_object = fields.datetime.strptime(
                    date_value, '%m/%d/%y') if match and len(
                    date_value.split('/')[
                        -1]) == 2 else fields.datetime.strptime(
                    date_value, '%m/%d/%Y')
            date = date_object.strftime(
                '%Y-%m-%d') if date_object else fields.Date.today()
        else:
            date = fields.Date.today()
        # Fetching the bill number if te pattern matches
        bill_no = bill_no_match.group(1) if bill_no_match else ''
        # Calling the function to get the product lines of the bill
        move_line_vals = self.record_lines(
            product_lines_newline_name_qty_price_amount,
            product_lines_name_qty_amount,
            product_lines_qty_name_amount,
            product_lines_name_qty_price_amount1,
            product_lines_name_price_qty_amount_with_dollar,
            product_lines_name_price_qty_amount,
            product_lines_name_amount, product_lines_name_qty_price_amount2,
            product_lines_double_line_name,
            product_lines_code_name,
            product_lines_quantity_part,
            product_lines_vendor_bill_pattern,
            product_lines_quantity_price_amount_pattern,
            product_lines_quantity_price_amount_pattern2,
            product_line_name_with_extra_line)
        # After getting all the data, creating a record in the
        # vendor bill
        bill_record = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'ref': bill_no,
            'date': date,
            'invoice_date': date,
            'invoice_line_ids': move_line_vals,
        }])
        return bill_record

    def action_add_document(self):
        """ Function that reading the file in the format .jpg, .jpeg and .png
        and converting into text using OCR python package """
        try:
            file_attachment = self.env["ir.attachment"].search(
                ['|', ('res_field', '!=', False), ('res_field', '=', False),
                 ('res_id', '=', self.id),
                 ('res_model', '=', 'digitize.bill')],
                limit=1)
            file_path = file_attachment._full_path(file_attachment.store_fname)
            with open(file_path, mode='rb') as file:
                binary_data = file.read()
            img = Image.open(io.BytesIO(binary_data))
            # Resizing the image to improve the clarity
            resized_img = img.resize((img.width * 2, img.height * 2),
                                     resample=Image.BICUBIC)
        except Exception:
            raise ValidationError(_("Cannot identify data"))
        # Converting the image into text using OCR python package
        # pytesseract
        try:
            text = pytesseract.image_to_string(resized_img)
        except Exception:
            raise ValidationError(_("Data cannot read"))
        # Calling the function to create vendor bill
        bill_record = self.create_record(text)
        # Opening the vendor bill using its id
        return {
            'name': "Invoice",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': bill_record.id,
            'view_id': self.env.ref('account.view_move_form').id,
            'target': 'current',
        }
