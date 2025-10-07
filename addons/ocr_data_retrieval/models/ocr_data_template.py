# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
###############################################################################
import io
import os
import pytesseract
import re
import spacy
from pdf2image import convert_from_bytes
from PIL import Image, ImageOps
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class OCRDataTemplate(models.TransientModel):
    """Class to read document and extract the text from JPG, JPEG, PNG and
    PDF files."""

    _name = "ocr.data.template"
    _description = "Data Retrieving Template"
    _rec_name = "file_name"

    image = fields.Binary(
        string="Document", required=True, help="Upload .jpg, .jpeg, .png or .pdf files"
    )
    file_name = fields.Char(string="Document Name", help="Name of document")
    image2 = fields.Image(string="Document", help="Uploaded document", store=True)
    flag = fields.Boolean(
        string="Flag", default=False, help="Flag to check document read or not"
    )
    data = fields.Text(string="Data", readonly=True, help="Content from the document")
    model_name_id = fields.Many2one(
        "ir.model",
        string="Model",
        domain="[('model', 'in', ['res.partner', 'account.move', "
        "'hr.employee', 'hr.expense', 'sale.order', "
        "'purchase.order'])]",
        help="Model to which the data want to map",
    )
    model_field_ids = fields.Many2many(
        "ir.model.fields",
        string="Fields",
        domain="[('model_id', '=', model_name_id)]",
        help="Fields names to map data",
    )

    def data_segmentation(self, img):
        """
        Function to do segmentation for the retrieved data after converting it
        into image
        """
        img = ImageOps.grayscale(img)
        threshold_value = 176
        img = img.point(lambda x: 255 if x > threshold_value else 0, "1")
        img_rgb = ImageOps.invert(img.convert("RGB"))
        segments = []
        segment_bounds = img_rgb.getbbox()
        while segment_bounds:
            segment = img_rgb.crop(segment_bounds)
            if segment.size[0] > 0 and segment.size[1] > 0:
                segments.append(segment)
            img_rgb = ImageOps.crop(img_rgb, segment_bounds)
            segment_bounds = img_rgb.getbbox()
        return segments

    def action_get_data(self):
        """
        Function to get the files in .jpg, .jpeg, .png and .pdf formats
        """
        split_tup = os.path.splitext(self.file_name)
        try:
            # Getting the file path from ir.attachments
            file_attachment = self.env["ir.attachment"].search(
                [
                    "|",
                    ("res_field", "!=", False),
                    ("res_field", "=", False),
                    ("res_id", "=", self.id),
                    ("res_model", "=", "ocr.data.template"),
                ],
                limit=1,
            )
            file_path = file_attachment._full_path(file_attachment.store_fname)
            segmented_data = []
            # Reading files in the format .jpg, .jpeg and .png
            if (
                split_tup[1] == ".jpg"
                or split_tup[1] == ".jpeg"
                or split_tup[1] == ".png"
            ):
                with open(file_path, mode="rb") as f:
                    binary_data = f.read()
                img = Image.open(io.BytesIO(binary_data))
                # Calling the function to do segmentation
                segmented_data = self.data_segmentation(img)
            elif split_tup[1] == ".pdf":
                # Reading files in the format .pdf
                with open(file_path, mode="rb") as f:
                    pdf_data = f.read()
                pages = convert_from_bytes(pdf_data)
                # Making the contents in 2 or more pages into combined page
                max_width = max(page.width for page in pages)
                total_height = sum(page.height for page in pages)
                resized_images = []
                for page in pages:
                    resized_page = page.resize((2400, 1800))
                    resized_images.append(resized_page)
                combined_image = Image.new("RGB", (max_width, total_height))
                y_offset = 0
                for resized_page in resized_images:
                    combined_image.paste(resized_page, (0, y_offset))
                    y_offset += resized_page.height
                # Calling the segmentation function
                segmented_data = self.data_segmentation(combined_image)
        except Exception:
            self.env["ocr.data.template"].search([], order="id desc", limit=1).unlink()
            raise ValidationError(_("Cannot identify data"))
        # Converting the segmented image into text using pytesseract
        text = ""
        for segment in segmented_data:
            try:
                text += pytesseract.image_to_string(segment) + "\n"
                break
            except Exception:
                raise ValidationError(_("Data cannot be read"))
        # Assigning retrieved data into text field
        self.data = text
        self.flag = True

    @api.onchange("model_name_id")
    def onchange_model_name_id(self):
        """Function to update the Many2many field to empty"""
        self.write({"model_field_ids": [(6, 0, [])]})

    def find_person_name(self):
        """
        Function to find person name from the retrieved text using 'spacy'
        """
        person = ""
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(self.data)
        for entity in doc.ents:
            if entity.label_ == "PERSON":
                person = entity.text
                break
        return person

    def get_order_line(self, text):
        """
        Function to find product lines from retrieved data using regex
        """
        product_line_list = []
        quantities = []
        unit_prices = []
        product_regex = r"\[?(.+?)\]?\s*(.+)\n(?:HSN/SAC Code):\s+(\d+)"
        quantity_regex = r"Quantity Unit\n([\d.\s\S]+)"
        unit_price_regex = r"Amount\n([\d.\s\S]+)"
        # Matching the pattern with the data
        quantity_match = re.search(quantity_regex, text)
        price_match = re.search(unit_price_regex, text)
        if quantity_match:
            quantity_unit_text = quantity_match.group(1)
            # If matched finding a particular pattern for quantities
            # form that group
            quantities = re.findall(r"\d+\.\d+", quantity_unit_text)
        if price_match:
            price_unit_text = price_match.group(1)
            # If matched finding a particular pattern for unit price
            # form that group
            unit_prices = re.findall(r"\d+\.\d+", price_unit_text)
        # Finding the data that matches the pattern for products
        products = re.findall(product_regex, text)
        number_of_product = len(products)
        number_of_qty = len(quantities)
        number_of_price = len(unit_prices)
        # Getting the products and its corresponding quantity and price
        if number_of_product == number_of_qty == number_of_price:
            for i in range(number_of_product):
                product_line_list.append(
                    {
                        "product": products[i],
                        "quantity": quantities[i],
                        "price": unit_prices[i],
                    }
                )
        elif number_of_product == number_of_qty:
            for i in range(number_of_product):
                product_line_list.append(
                    {"product": products[i], "quantity": quantities[i]}
                )
        elif number_of_product == number_of_price:
            for i in range(number_of_product):
                product_line_list.append(
                    {"product": products[i], "price": unit_prices[i]}
                )
        elif products:
            for i in range(number_of_product):
                product_line_list.append({"product": products[i]})
        return product_line_list

    def action_process_data(self):
        """
        Function to process the data after fetching it.
        The fetched data are mapping into some models.
        """
        phone_number = ""
        email_address = ""
        person = ""
        phone_pattern = r"\(\d{3}\) \d{3}-\d{4}|\d{3}-\d{3}-\d{4}|\+\d{1}-\d{3}-\d{3}-\d{4}|\d{11}|P \+\d{3} \d{6}"
        email_pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
        if self.model_name_id.name == "Contact":
            # Mapping the data into Contact module by fetching person name,
            # phone number and email id from data
            field_value = False
            non_field_count = 0
            for field in self.model_field_ids:
                if field.name == "name" or field.name == "display_name":
                    person = self.find_person_name()
                    if not person:
                        raise ValidationError(_("Partner name cannot find"))
                    field_value = True
                elif field.name == "phone":
                    phone = re.findall(phone_pattern, self.data)
                    if phone:
                        phone_number = phone[0]
                elif field.name == "email":
                    email = re.findall(email_pattern, self.data)
                    if email:
                        email_address = email[0]
                else:
                    non_field_count = 1
            if not field_value and non_field_count == 1:
                raise ValidationError(_("No data to map into the field"))
            if person:
                partner = self.env["res.partner"].search(
                    [("name", "=", person)], limit=1
                )
                if not partner:
                    # Creating record in res.partner
                    partner_record = self.env["res.partner"].create(
                        {"name": person, "email": email_address, "phone": phone_number}
                    )
                else:
                    raise ValidationError(_("Partner already exist"))
            else:
                raise ValidationError(
                    _("Name field is not chosen to create" " partner")
                )
            if partner_record:
                return {
                    "name": "Partner",
                    "type": "ir.actions.act_window",
                    "view_type": "form",
                    "view_mode": "form",
                    "res_model": "res.partner",
                    "res_id": partner_record.id,
                    "view_id": self.env.ref("base.view_partner_form").id,
                    "target": "current",
                }
        elif self.model_name_id.name == "Journal Entry":
            # Mapping data into Journal Entry. Creating a record in vendor bill
            vendor_bill_flag = False
            for field in self.model_field_ids:
                # Taking the file path from ir.attachment
                if field.name == "invoice_vendor_bill_id":
                    vendor_bill_flag = True
                    try:
                        file_attachment = self.env["ir.attachment"].search(
                            [
                                "|",
                                ("res_field", "!=", False),
                                ("res_field", "=", False),
                                ("res_id", "=", self.id),
                                ("res_model", "=", "ocr.data.template"),
                            ],
                            limit=1,
                        )
                        file_path = file_attachment._full_path(
                            file_attachment.store_fname
                        )
                        with open(file_path, mode="rb") as f:
                            binary_data = f.read()
                        img = Image.open(io.BytesIO(binary_data))
                        # Resizing the image to improve the clarity
                        resized_img = img.resize(
                            (img.width * 2, img.height * 2), resample=Image.BICUBIC
                        )
                    except Exception:
                        raise ValidationError(_("Can't create vendor bill"))
                    # Converting the image into text using OCR python package
                    # pytesseract
                    try:
                        text = pytesseract.image_to_string(resized_img)
                    except Exception:
                        raise ValidationError(_("Can't create vendor bill"))
                    bill = self.env["digitize.bill"]
                    # Calling the function to create vendor bill
                    # from model digitize.bill
                    bill_record = bill.create_record(text)
                    return {
                        "name": "Bill",
                        "type": "ir.actions.act_window",
                        "view_type": "form",
                        "view_mode": "form",
                        "res_model": "account.move",
                        "res_id": bill_record.id,
                        "view_id": self.env.ref("account.view_move_form").id,
                        "target": "current",
                    }
            if not vendor_bill_flag:
                raise ValidationError(_("No data to map into the field"))
        elif self.model_name_id.name == "Employee":
            # Mapping the data into Employee module by fetching person name,
            # phone number and email
            field_value = False
            non_field_count = 0
            for field in self.model_field_ids:
                if (
                    field.name == "name"
                    or field.name == "display_name"
                    or field.name == "emergency_contact"
                ):
                    person = self.find_person_name()
                    if not person:
                        raise ValidationError(_("Employee name cannot find"))
                    field_value = True
                elif (
                    field.name == "work_phone"
                    or field.name == "phone"
                    or field.name == "emergency_phone"
                ):
                    phone = re.findall(phone_pattern, self.data)
                    if phone:
                        phone_number = phone[0]
                elif field.name == "private_email" or field.name == "work_email":
                    email = re.findall(email_pattern, self.data)
                    if email:
                        email_address = email[0]
                else:
                    non_field_count = 1
            if not field_value and non_field_count == 1:
                raise ValidationError(_("No data to map into the field"))
            if person:
                partner = self.env["hr.employee"].search(
                    [("name", "=", person)], limit=1
                )
                if not partner:
                    # Creating a record in hr.employee by mapping the
                    # data into employee name, work phone and work email
                    employee_record = self.env["hr.employee"].create(
                        {
                            "name": person,
                            "work_email": email_address,
                            "work_phone": phone_number,
                        }
                    )
                else:
                    raise ValidationError(_("Employee already exist"))
            else:
                raise ValidationError(_("Name field is not chosen to create employee"))
            if employee_record:
                return {
                    "name": "Employee",
                    "type": "ir.actions.act_window",
                    "view_type": "form",
                    "view_mode": "form",
                    "res_model": "hr.employee",
                    "res_id": employee_record.id,
                    "view_id": self.env.ref("hr.view_employee_form").id,
                    "target": "current",
                }
        elif self.model_name_id.name == "Expense":
            # Mapping the data into Expense module
            expense_product = False
            for field in self.model_field_ids:
                if field.name == "name" or field.name == "product_id":
                    expense_product = True
                    product = self.env["product.product"].search(
                        [("name", "=", "BILL EXPENSE")], limit=1
                    )
                    if not product:
                        product = self.env["product.product"].create(
                            {
                                "name": "BILL EXPENSE",
                            }
                        )
                    expense_record = self.env["hr.expense"].create(
                        {
                            "product_id": product.id,
                        }
                    )
                    return {
                        "name": "Expense",
                        "type": "ir.actions.act_window",
                        "view_type": "form",
                        "view_mode": "form",
                        "res_model": "hr.expense",
                        "res_id": expense_record.id,
                        "view_id": self.env.ref("hr_expense.hr_expense_view_form").id,
                        "target": "current",
                    }
            if not expense_product:
                raise ValidationError(
                    _("Can't create an expense without " "description or category")
                )
        elif self.model_name_id.name == "Sales Order":
            # Mapping the data from PDF with proper format into Sale Order
            sale_order = ""
            partner = False
            field_value = False
            non_field_value = 0
            for field in self.model_field_ids:
                if field.name == "order_line":
                    field_value = True
                    person = self.find_person_name()
                    if person:
                        partner = self.env["hr.employee"].search(
                            [("name", "=", person)], limit=1
                        )
                        if not partner:
                            partner = self.env["hr.employee"].create(
                                {
                                    "name": person,
                                }
                            )
                    # Calling the function to get order lines
                    product_line = self.get_order_line(self.data)
                    sale_order = self.env["sale.order"].create(
                        {
                            "partner_id": partner.id,
                        }
                    )
                    if product_line:
                        for item in product_line:
                            if "quantity" not in item.keys():
                                item.update({"quantity": 0})
                            if "price" not in item.keys():
                                item.update({"price": 0})
                            product = self.env["product.product"].search(
                                [("name", "=", item["product"])], limit=1
                            )
                            if not product:
                                product = self.env["product.product"].create(
                                    {"name": item["product"]}
                                )
                            item.update({"product": product.id})
                            self.env["sale.order.line"].create(
                                {
                                    "order_id": sale_order.id,
                                    "product_id": item["product"],
                                    "product_uom_qty": item["quantity"],
                                    "price_unit": item["price"],
                                }
                            )
                else:
                    non_field_value = 1
                if sale_order:
                    return {
                        "name": "Sale order",
                        "type": "ir.actions.act_window",
                        "view_type": "form",
                        "view_mode": "form",
                        "res_model": "sale.order",
                        "res_id": sale_order.id,
                        "view_id": self.env.ref("sale.view_order_form").id,
                        "target": "current",
                    }
            if not field_value and non_field_value == 1:
                raise ValidationError(_("No data to map into the field"))
        elif self.model_name_id.name == "Purchase Order":
            # Mapping the data from PDF with proper format into Purchase Order
            purchase_order = ""
            field_value = False
            non_field_value = 0
            partner = False
            for field in self.model_field_ids:
                if field.name == "order_line":
                    field_value = True
                    person = self.find_person_name()
                    if person:
                        partner = self.env["hr.employee"].search(
                            [("name", "=", person)], limit=1
                        )
                        if not partner:
                            partner = self.env["hr.employee"].create(
                                {
                                    "name": person,
                                }
                            )
                    # Calling the function to get order lines
                    product_line = self.get_order_line(self.data)
                    purchase_order = self.env["purchase.order"].create(
                        {
                            "partner_id": partner.id,
                        }
                    )
                    if product_line:
                        for item in product_line:
                            if "quantity" not in item.keys():
                                item.update({"quantity": 0})
                            if "price" not in item.keys():
                                item.update({"price": 0})
                            product = self.env["product.product"].search(
                                [("name", "=", item["product"])], limit=1
                            )
                            if not product:
                                product = self.env["product.product"].create(
                                    {"name": item["product"]}
                                )
                            item.update({"product": product.id})
                            self.env["purchase.order.line"].create(
                                {
                                    "order_id": purchase_order.id,
                                    "product_id": item["product"],
                                    "product_uom_qty": item["quantity"],
                                    "price_unit": item["price"],
                                }
                            )
                else:
                    non_field_value = 1
                if purchase_order:
                    return {
                        "name": "Purchase order",
                        "type": "ir.actions.act_window",
                        "view_type": "form",
                        "view_mode": "form",
                        "res_model": "purchase.order",
                        "res_id": purchase_order.id,
                        "view_id": self.env.ref("purchase.purchase_order_form").id,
                        "target": "current",
                    }
            if not field_value and non_field_value == 1:
                raise ValidationError(_("No data to map into the field"))

    @api.onchange("image")
    def _onchange_image(self):
        self.write({"image2": self.image})
