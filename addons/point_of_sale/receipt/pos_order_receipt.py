# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import io
import json
import math
from datetime import datetime
from io import BytesIO

import qrcode
from PIL import Image

from odoo import _, api, models, modules
from odoo.tools.image import image_data_uri
from odoo.tools.misc import format_datetime


def _get_str_notes(note):
    """
    Mirror method of the JS computeChanges in epson_printer.js
    """
    if not note:
        return ""
    if isinstance(note, list):
        return ", ".join(n if isinstance(n, str) else n.get('text', '') for n in note)
    if isinstance(note, str):
        try:
            parsed = json.loads(note)
            if isinstance(parsed, list):
                return ", ".join(n if isinstance(n, str) else n.get('text', '') for n in parsed)
        except (json.JSONDecodeError, ValueError):
            pass
        return note
    return ""


class PosOrderReceipt(models.AbstractModel):
    _name = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    @api.model
    def get_receipt_template_for_pos_frontend(self):
        names = [
            'point_of_sale.pos_order_receipt_header',
            'point_of_sale.pos_order_receipt_style',
            'point_of_sale.company_info_receipt',
            'point_of_sale.pos_orderline_receipt_information',
            'point_of_sale.pos_orderline_receipt',
            'point_of_sale.pos_order_receipt_footer',
            'point_of_sale.pos_order_receipt',
            'point_of_sale.pos_order_change_receipt',
            'point_of_sale.pos_order_change_receipt_zpl',
            'point_of_sale.pos_order_change_receipt_line',
            'point_of_sale.pos_cash_move_receipt',
            'point_of_sale.pos_tip_receipt',
            'point_of_sale.pos_sale_details_receipt',
            'point_of_sale.pos_sale_details_receipt_product_line',
        ]
        return [[name, self.env['ir.qweb']._get_template(name)[1]] for name in names]

    @api.model
    def _order_receipt_format_currency(self, amount):
        return self.currency_id.format(amount).replace('\xa0', ' ')  # Wkhtmltoimage does not support non-breaking spaces

    def _get_common_record_data(self):
        company_fields = self.env['res.company']._load_pos_data_fields(self.config_id)
        partner_fields = self.env['res.partner']._load_pos_data_fields(self.config_id)
        preset_fields = self.env['pos.preset']._load_pos_data_fields(self.config_id)
        order_fields = self.env['pos.order']._load_pos_data_fields(self.config_id)
        config_fields = self.env['pos.config']._load_pos_data_fields(self.config_id)
        return {
            'order': self.read(order_fields, load=False)[0],
            'config': self.config_id.read(config_fields, load=False)[0],
            'company': self.company_id.read(company_fields, load=False)[0],
            'partner': self.partner_id.read(partner_fields, load=False)[0] if self.partner_id else False,
            'preset': self.preset_id.read(preset_fields, load=False)[0] if self.preset_id else False,
        }

    def _get_common_extra_data(self):
        company = self.company_id
        return {
            'vat_label': company.country_id.vat_label or _("Tax ID"),
            'preset_datetime': format_datetime(self.env, self.preset_time) if self.preset_time else False,
            'partner_vat_label': self.partner_id.country_id.vat_label if self.partner_id.country_id else _("Tax ID"),
            'self_invoicing_url': f"{self.env.company.get_base_url()}/pos/ticket",
            'prices': self._order_receipt_generate_taxe_data(),
            'cashier_name': self.user_id.name.split(' ')[0] if self.user_id else '',
            'company_state_name': company.state_id.name if company.state_id else False,
            'company_country_name': company.country_id.name if company.country_id else False,
            'formated_date_order': format_datetime(self.env, self.date_order),
        }

    def _order_receipt_generate_taxe_data(self):
        sign = -1 if self.is_refund_or_negative() else 1
        tax_totals = self._get_order_tax_totals()  # Use account helpers to compute tax totals
        discount_amount = sum(line._get_discount_amount() for line in self.lines.filtered(lambda line: line.discount > 0))
        rounding = tax_totals.get('cash_rounding_base_amount_currency', 0)

        return {
            'same_tax_base': tax_totals['same_tax_base'],
            'discount_amount': self._order_receipt_format_currency(-abs(discount_amount)) if discount_amount else False,
            'rounding_amount': self._order_receipt_format_currency(sign * rounding) if rounding else False,
            'tax_amount': self._order_receipt_format_currency(sign * tax_totals['tax_amount_currency']),
            'total_amount': self._order_receipt_format_currency(sign * tax_totals['total_amount_currency']),
            'subtotal_amount': self._order_receipt_format_currency(sign * tax_totals['base_amount_currency']),
            'taxes': [{
                'name': tax['group_name'],
                'amount': self._order_receipt_format_currency(sign * tax['tax_amount']),
                'amount_base': self._order_receipt_format_currency(sign * tax['base_amount_currency']),
            } for tax in tax_totals['subtotals'][0]['tax_groups']] if len(tax_totals['subtotals']) > 0 else [],
        }

    def _order_receipt_generate_payment_data(self):
        payment_fields = self.env['pos.payment']._load_pos_data_fields(self.config_id)

        payments = []
        for line in self.payment_ids:
            data = line.read(payment_fields, load=False)[0]
            data['payment_method_data'] = {'name': line.payment_method_id.name}
            data['amount'] = self._order_receipt_format_currency(data['amount'])
            payments.append(data)

        return payments

    def _order_receipt_generate_line_data(self):
        lines_fields = self.env['pos.order.line']._load_pos_data_fields(self.config_id)
        product_fields = self.env['product.product']._load_pos_data_fields(self.config_id)
        products = self.lines.product_id.with_context(display_default_code=False).read(product_fields, load=False)
        product_by_id = {product['id']: product for product in products}

        preset_id = self.preset_id
        service_fee_product = preset_id.service_fee_product_id if preset_id else None

        lines = []
        for line in self.lines:
            data = line.read(lines_fields, load=False)[0]
            display_price_incl = line.order_id.config_id.iface_tax_included == 'total'

            data['qty'] = int(line.qty) if float(line.qty).is_integer() else line.qty
            data['product_data'] = product_by_id[data['product_id']]
            data['product_uom_name'] = line.product_id.uom_id.name
            data['price_subtotal_incl'] = self._order_receipt_format_currency(data['price_subtotal_incl'])

            # Compute line unit price
            taxes = line._compute_amount_line_all(1)
            line_unit_price = taxes['price_subtotal_incl'] if display_price_incl else taxes['price_subtotal']
            data['unit_price'] = self._order_receipt_format_currency(line_unit_price)

            # Compute product unit price
            taxes = line.tax_ids.compute_all(data['product_data']['lst_price'], line.order_id.currency_id, 1)
            product_unit_price = taxes['total_included'] if display_price_incl else taxes['total_excluded']
            data['product_unit_price'] = self._order_receipt_format_currency(product_unit_price)

            if service_fee_product and line.product_id.id == service_fee_product.id:
                data['is_service_fee_line'] = True
                data['service_fee_display_info'] = {
                    'amount': (preset_id.service_fee_type == 'percent' and f"{preset_id.service_fee_amount * 100}%") or self._order_receipt_format_currency(line.price_subtotal_incl),
                    'description': (preset_id.service_fee_based_on == 'pre_discount' and _(" (before discount)")) or _(" (after discount)"),
                }
            else:
                data['is_service_fee_line'] = False

            lines.append(data)

        return lines

    def _order_receipt_generate_qr_code(self, qrcode_url):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=4,
            border=0,
        )
        qr.add_data(qrcode_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="transparent")

        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return image_data_uri(buffer.getvalue())

    def order_receipt_generate_data(self, basic_receipt=False):
        self.ensure_one()

        use_qr_code = self.company_id.point_of_sale_ticket_portal_url_display_mode != 'url'
        config_logo = image_data_uri(self.config_id.logo) if self.config_id.logo else False
        qr_code_value = f"{self.env.company.get_base_url()}/pos/ticket?order_uuid={self.uuid}"
        tip_percentage = [self.config_id.tip_percentage_1, self.config_id.tip_percentage_2, self.config_id.tip_percentage_3] if self.config_id.set_tip_after_payment and self.amount_total > 0 else False

        return {
            **self._get_common_record_data(),
            'lines': self._order_receipt_generate_line_data(),
            'payments': self._order_receipt_generate_payment_data(),
            'image': {
                'logo': config_logo,
                'invoice_qr_code': self._order_receipt_generate_qr_code(qr_code_value) if use_qr_code else False,
            },
            'conditions': {
                'basic_receipt': basic_receipt,
                'display_vat': self.company_id.country_id.id in self.env.ref("base.europe").country_ids.ids,
                'display_qr_code': use_qr_code,
                'display_url': self.company_id.point_of_sale_ticket_portal_url_display_mode != 'qr_code',
                'use_self_invoicing': self.company_id.point_of_sale_use_ticket_qr_code,
                'module_pos_restaurant': self.config_id.module_pos_restaurant,
            },
            'extra_data': {
                **self._get_common_extra_data(),
                'tips_configuration': [
                    [f"{p}%", self._order_receipt_format_currency(self.amount_total * (p / 100))]
                    for p in tip_percentage
                ] if tip_percentage else False,
            },
        }

    def order_receipt_generate_html(self, basic_receipt=False):
        last_order = self.env['pos.order'].search([], order='id desc', limit=1)
        report_name = 'point_of_sale.pos_order_receipt'
        return last_order.env['ir.qweb']._render(report_name, values=self.order_receipt_generate_data(basic_receipt))

    def order_receipt_generate_image(self, basic_receipt=False, width=500, height=0):
        content = self.order_receipt_generate_html(basic_receipt)
        return self.env['ir.actions.report']._run_image_engine(
            'wkhtmltopdf',
            [content],
            width,
            height,
        )[0]

    # Order changes receipt generation
    def _generate_preparation_changes_by_printer(self):
        changes = {}
        for printer in self.config_id.preparation_printer_ids:
            categ_set = set(printer.product_categories_ids.ids)
            data = self._generate_preparation_change_for_categories(categ_set)
            changes[printer] = self._generate_preparation_receipt_data(data)
        return changes

    def _generate_preparation_change_for_categories(self, prep_categ_ids):
        changes = {
            "category_count": {},
            "added_quantity": [],
            "removed_quantity": [],
            "note_update": [],
        }

        def _key_maker(prep_line):
            object_key = {
                "product_id": prep_line.product_id.id,
                "combo_parent_id": prep_line.combo_parent_id.id or None,
                "combo_line_ids": sorted(prep_line.combo_line_ids.ids),
                "attribute_value_ids": sorted(prep_line.attribute_value_ids.ids),
            }
            return json.dumps(object_key, sort_keys=True)

        def has_preparation_category(categories):
            product_categ_ids = categories._get_parents().ids
            return any(cat_id in prep_categ_ids for cat_id in product_categ_ids)

        for orderline in self.lines:
            child_categs = orderline.combo_line_ids.product_id.pos_categ_ids
            parent_categs = orderline.product_id.pos_categ_ids
            parent_match = has_preparation_category(parent_categs)
            child_match = has_preparation_category(child_categs)
            has_prepa_category = child_match or parent_match

            if not has_prepa_category:
                continue

            quantity = orderline.prep_line_ids.quantity - orderline.prep_line_ids.cancelled
            quantity_diff = orderline.qty - quantity

            if quantity_diff != 0:
                key = "added_quantity" if quantity_diff > 0 else "removed_quantity"
                data = self._generate_preparation_output_data(orderline, quantity_diff)
                changes[key].append(data)

            elif orderline.note or orderline.customer_note:
                data = self._generate_preparation_output_data(orderline, orderline.qty)
                changes["note_update"].append(data)

        # Detect orderlines deleted from the order since last sent to preparation tools.
        prep_order_lines = self.prep_order_ids.prep_line_ids
        orphan_prep_lines = prep_order_lines.filtered_domain([
            ("pos_order_line_id", "=", False),
        ])

        removed_by_key = {}
        for prep_line in orphan_prep_lines:
            key = _key_maker(prep_line)
            if key not in removed_by_key:
                removed_by_key[key] = {"quantity": 0, "prep_line": prep_line}
            removed_by_key[key]["quantity"] += prep_line.quantity - prep_line.cancelled

        for entry in removed_by_key.values():
            quantity = entry["quantity"]
            prep_line = entry["prep_line"]
            if quantity <= 0:
                continue
            line_data = self._generate_preparation_output_data(prep_line.pos_order_line_id, -quantity)
            changes["removed_quantity"].append(line_data)

        if self.general_customer_note:
            changes["general_customer_note"] = self.general_customer_note

        if self.internal_note:
            changes["internal_note"] = self.internal_note

        return changes

    def _prepare_preparation_grouped_data(self, changes):
        data_changes = changes.get("data") or []
        if data_changes and any(c.get("group") for c in data_changes):
            grouped_data = {}
            for c in data_changes:
                group = c.get("group") or {}
                name = group.get("name", "")
                index = group.get("index", -1)
                if name not in grouped_data:
                    grouped_data[name] = {"name": name, "index": index, "data": []}
                grouped_data[name]["data"].append(c)
            changes["grouped_data"] = sorted(
                grouped_data.values(), key=lambda g: g["index"]
            )
        return changes

    def _generate_preparation_receipt_data(self, order_change):
        is_empty_change = (
            not order_change["added_quantity"]
            and not order_change["removed_quantity"]
            and not order_change["note_update"]
            and not order_change.get("internal_note")
            and not order_change.get("general_customer_note")
        )

        if is_empty_change:
            return []

        receipts_data = []

        if order_change["added_quantity"]:
            receipts_data.append(
                self._prepare_preparation_grouped_data({
                    "title": _("NEW"),
                    "data": order_change["added_quantity"],
                }),
            )

        if order_change["removed_quantity"]:
            receipts_data.append(
                self._prepare_preparation_grouped_data({
                    "title": _("CANCELLED"),
                    "data": order_change["removed_quantity"],
                }),
            )

        if order_change["note_update"]:
            note_update_title = order_change.get("note_update_title")
            print_note_update_data = order_change.get("print_note_update_data", True)
            receipts_data.append(
                self._prepare_preparation_grouped_data({
                    "title": note_update_title or _("NOTE UPDATE"),
                    "data": order_change["note_update"] if print_note_update_data else [],
                }),
            )

        if order_change.get("internal_note") or order_change.get("general_customer_note"):
            receipts_data.append(
                self._prepare_preparation_grouped_data({"title": "", "data": []})
            )

        receipts = []
        for change in receipts_data:
            receipts.append({
                **self._get_common_record_data(),
                "changes": change,
                "extra_data": {
                    **self._get_common_extra_data(),
                    "reprint": False,
                    "time": datetime.now().strftime("%H:%M"),
                    "internal_note": _get_str_notes(change.get("internal_note")) or False,
                    "general_customer_note": _get_str_notes(change.get("general_customer_note")) or False,
                    "employee_name": self.user_id.name,  # PoS HR not needed, this will only be used by self order.
                    "preset_time": self.preset_time.strftime("%H:%M") if self.preset_time else False,
                },
                "conditions": {
                    "module_pos_restaurant": self.config_id.module_pos_restaurant,
                },
            })

        return receipts

    def _generate_preparation_output_data(self, line, quantity):
        product = line.product_id
        attributes = line.attribute_value_ids or self.env["product.template.attribute.value"]
        is_restaurant = self.config_id.module_pos_restaurant
        first_categ = product.pos_categ_ids[:1]

        return {
            "basic_name": product.name if is_restaurant else product.display_name,
            "product_id": product.id,
            "attribute_value_names": attributes.mapped("name"),
            "quantity": quantity,
            "note": _get_str_notes(line.note),
            "customer_note": _get_str_notes(line.customer_note),
            "pos_categ_id": first_categ.id,
            "pos_categ_sequence": first_categ.sequence,
            "group": False,
            "combo_line_ids": line.combo_line_ids.ids,
            "combo_parent_uuid": line.combo_parent_id.uuid,
        }

    # Preparation ticket generation
    def _order_change_receipts_generate_html(self):
        last_order = self.env['pos.order'].search([], order='id desc', limit=1)
        report_name = 'point_of_sale.pos_order_change_receipt'
        changes = self._generate_preparation_changes_by_printer()
        rendered = {}

        for printer, data in changes.items():
            rendered[printer] = [last_order.env['ir.qweb']._render(
                report_name,
                values=change,
            ) for change in data]

        return rendered

    def _order_change_receipt_generate_receipts(self):
        data = self._order_change_receipts_generate_html()
        receipts = {}
        for printer, htmls in data.items():
            images = self.env['ir.actions.report']._run_image_engine(
                'wkhtmltopdf',
                htmls,
                500,
                0,
            )
            rasterified = [self._order_change_receipts_generate_raster(image) for image in images]
            receipts[printer] = rasterified
        return receipts

    def _canvas_to_raster(self, image_bytes):
        """
        Mirror method of the JS computeChanges in epson_printer.js
        """
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        width, height = img.size
        pixels = img.load()

        # Width MUST be a multiple of 8 for Epson ePOS raster format
        padded_width = math.ceil(width / 8) * 8

        errors = [[0.0] * height for _ in range(width)]
        raster_data = []

        for y in range(height):
            row = []
            for x in range(width):
                r, g, b, _ = pixels[x, y]
                old_color = r * 0.299 + g * 0.587 + b * 0.114
                old_color += errors[x][y]
                old_color = min(255.0, max(0.0, old_color))

                if old_color < 128:
                    new_color = 0
                    row.append(1)
                else:
                    new_color = 255
                    row.append(0)

                error = old_color - new_color
                if error:
                    if x < width - 1:
                        errors[x + 1][y] += (7 / 16) * error
                    if x > 0 and y < height - 1:
                        errors[x - 1][y + 1] += (3 / 16) * error
                    if y < height - 1:
                        errors[x][y + 1] += (5 / 16) * error
                    if x < width - 1 and y < height - 1:
                        errors[x + 1][y + 1] += (1 / 16) * error

            # Pad row to multiple of 8 with white (0) pixels
            row += [0] * (padded_width - width)
            raster_data.extend(row)

        return "".join(map(str, raster_data)), padded_width, height

    def _order_change_receipts_generate_raster(self, image_bytes):
        # Wkhtmltoimage doesn't works in tests see def _run_wkhtmltoimage in ir.actions.report
        if modules.module.current_test:
            raster_str = "10101010"
            actual_width = 100
            actual_height = 100
        else:
            raster_str, actual_width, actual_height = self._canvas_to_raster(image_bytes)

        # Pack 8 pixels per byte, mirroring JS encodeRaster()
        encoded = bytearray()
        for i in range(0, len(raster_str), 8):
            byte_str = raster_str[i:i + 8].ljust(8, '0')
            encoded.append(int(byte_str, 2))

        b64 = base64.b64encode(bytes(encoded)).decode('ascii')
        return (
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            f'<s:Body>'
            f'<epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">'
            f'<image width="{actual_width}" height="{actual_height}" align="center">{b64}</image>'
            f'<cut type="feed"/>'
            f'</epos-print>'
            f'</s:Body>'
            f'</s:Envelope>'
        )
