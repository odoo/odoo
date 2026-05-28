# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import io
import json
import math
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

    def _order_receipt_generate_taxe_data(self):
        sign = -1 if self.is_refund else 1
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

        company_fields = self.env['res.company']._load_pos_data_fields(self.config_id)
        partner_fields = self.env['res.partner']._load_pos_data_fields(self.config_id)
        preset_fields = self.env['pos.preset']._load_pos_data_fields(self.config_id)
        order_fields = self.env['pos.order']._load_pos_data_fields(self.config_id)
        config_fields = self.env['pos.config']._load_pos_data_fields(self.config_id)

        use_qr_code = self.company_id.point_of_sale_ticket_portal_url_display_mode != 'url'
        company = self.company_id
        config_logo = image_data_uri(self.config_id.logo) if self.config_id.logo else False
        qr_code_value = f"{self.env.company.get_base_url()}/pos/ticket?order_uuid={self.uuid}"
        tip_percentage = [self.config_id.tip_percentage_1, self.config_id.tip_percentage_2, self.config_id.tip_percentage_3] if self.config_id.set_tip_after_payment and self.amount_total > 0 else False

        return {
            'order': self.read(order_fields, load=False)[0],
            'config': self.config_id.read(config_fields, load=False)[0],
            'company': self.company_id.read(company_fields, load=False)[0],
            'partner': self.partner_id.read(partner_fields, load=False)[0] if self.partner_id else False,
            'preset': self.preset_id.read(preset_fields, load=False)[0] if self.preset_id else False,
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
                'vat_label': self.company_id.country_id.vat_label or _("Tax ID"),
                'preset_datetime': format_datetime(self.env, self.preset_time) if self.preset_time else False,
                'partner_vat_label': self.partner_id.country_id.vat_label if self.partner_id.country_id else _("Tax ID"),
                'self_invoicing_url': f"{self.env.company.get_base_url()}/pos/ticket",
                'prices': self._order_receipt_generate_taxe_data(),
                'cashier_name': self.user_id.name.split(' ')[0] if self.user_id else '',
                'company_state_name': company.state_id.name if company.state_id else False,
                'company_country_name': company.country_id.name if company.country_id else False,
                'formated_date_order': format_datetime(self.env, self.date_order),
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
        return self.env['ir.actions.report']._run_wkhtmltoimage(
            [content],
            width,
            height,
        )[0]

    # Order changes receipt generation
    def _order_change_has_prep_category(self, product, prep_categ_ids):
        if not prep_categ_ids:
            return False

        for categ in product.pos_categ_ids:
            while categ:
                if categ.id in prep_categ_ids:
                    return True
                categ = categ.parent_id

        return False

    def _order_change_get_line_details(self, line, quantity_diff):
        product = line.product_id
        first_categ = product.pos_categ_ids[:1]
        return {
            'uuid': line.uuid,
            'name': line.full_product_name or product.display_name,
            'basic_name': product.name,
            'isCombo': bool(line.combo_line_ids),
            'combo_parent_uuid': line.combo_parent_id.uuid if line.combo_parent_id else False,
            'product_id': product.id,
            'attribute_value_names': line.attribute_value_ids.mapped('name'),
            'quantity': int(quantity_diff) if float(quantity_diff).is_integer() else quantity_diff,
            'note': _get_str_notes(line.note),
            'customer_note': line.customer_note or '',
            'pos_categ_id': first_categ.id if first_categ else 0,
            'pos_categ_sequence': first_categ.sequence if first_categ else 0,
            'display_name': product.display_name,
        }

    def _order_change_compute_changes(self, prep_categ_ids=None):
        """
        Mirror method of the JS computeChanges in order_change.js
        """
        try:
            last_change_data = json.loads(self.last_order_preparation_change)
        except (TypeError, ValueError, json.JSONDecodeError):
            last_change_data = {}

        old_lines = last_change_data.get('lines', {})
        changes = {}
        note_update = {}

        def has_prep(product):
            return self._order_change_has_prep_category(product, prep_categ_ids)

        for line in self.lines:
            product = line.product_id
            line_key = line.uuid

            line_has_prep = (
                has_prep(product)
                or (line.combo_parent_id and has_prep(line.combo_parent_id.product_id))
                or any(has_prep(cl.product_id) for cl in line.combo_line_ids)
            )
            if not line_has_prep:
                continue

            # The key may differ from uuid when a note was updated
            related_key = next((k for k in old_lines if k.startswith(line.uuid)), line_key)
            old_line = old_lines.get(related_key)

            old_quantity = old_line['quantity'] if old_line else 0
            quantity_diff = (line.qty - old_quantity) if old_line else line.qty

            note_changed = old_line and (
                _get_str_notes(old_line.get('note', '')) != _get_str_notes(line.note)
                or old_line.get('customer_note', '') != (line.customer_note or '')
            )

            line_details = self._order_change_get_line_details(line, quantity_diff)

            if quantity_diff:
                changes[line_key] = line_details
                if note_changed:
                    note_details = dict(line_details)
                    note_details['quantity'] = old_quantity
                    note_update[line_key] = note_details
            elif note_changed:
                line_details['quantity'] = line.qty
                note_update[line_key] = line_details

        current_uuids = {line.uuid for line in self.lines}
        for line_key, line_resume in old_lines.items():
            if line_resume.get('uuid') not in current_uuids:
                try:
                    old_qty = float(line_resume.get('quantity', 0))
                    old_qty = 0.0 if math.isnan(old_qty) else old_qty
                except (TypeError, ValueError):
                    old_qty = 0.0
                if line_key not in changes:
                    changes[line_key] = {
                        'uuid': line_resume.get('uuid'),
                        'product_id': line_resume.get('product_id'),
                        'name': line_resume.get('name', ''),
                        'basic_name': line_resume.get('basic_name') or line_resume.get('name', ''),
                        'display_name': line_resume.get('display_name', ''),
                        'isCombo': bool(line_resume.get('isCombo')),
                        'combo_parent_uuid': line_resume.get('combo_parent_uuid', False),
                        'note': _get_str_notes(line_resume.get('note', '')),
                        'customer_note': line_resume.get('customer_note', ''),
                        'attribute_value_names': line_resume.get('attribute_value_names', []),
                        'quantity': -old_qty,
                    }
                else:
                    changes[line_key]['quantity'] -= old_qty

        new_lines = []
        cancelled_lines = []
        for line_change in changes.values():
            line_change['note'] = _get_str_notes(line_change.get('note', ''))
            if line_change['quantity'] > 0:
                new_lines.append(line_change)
            else:
                line_change['quantity'] = abs(line_change['quantity'])
                cancelled_lines.append(line_change)

        result = {
            'new': new_lines,
            'cancelled': cancelled_lines,
            'noteUpdate': list(note_update.values()),
        }

        current_general_note = self.general_customer_note or ''
        if last_change_data.get('general_customer_note', '') != current_general_note:
            result['general_customer_note'] = current_general_note

        current_internal_note = self.internal_note or ''
        if last_change_data.get('internal_note', '') != current_internal_note:
            result['internal_note'] = current_internal_note

        return result

    def _prepare_preparation_grouped_data(self, changes):
        """Mirror of JS preparePreparationGroupedData"""
        data = changes.get('data', [])
        if data and any(c.get('group') for c in data):
            grouped = {}
            for c in data:
                group = c.get('group') or {}
                name = group.get('name', '')
                index = group.get('index', -1)
                if name not in grouped:
                    grouped[name] = {'name': name, 'index': index, 'data': []}
                grouped[name]['data'].append(c)
            changes['groupedData'] = sorted(grouped.values(), key=lambda g: g['index'])
        return changes

    def _order_change_receipt_generate_data(self, prep_categ_ids=None):
        """Mirror of JS generatePreparationData"""
        self.ensure_one()

        order_changes = self._order_change_compute_changes(prep_categ_ids)
        receipts_data = []

        if order_changes['new']:
            receipts_data.append(self._prepare_preparation_grouped_data({
                'title': _("NEW"),
                'data': order_changes['new'],
            }))

        if order_changes['cancelled']:
            receipts_data.append(self._prepare_preparation_grouped_data({
                'title': _("CANCELLED"),
                'data': order_changes['cancelled'],
            }))

        if order_changes.get('noteUpdate'):
            receipts_data.append(self._prepare_preparation_grouped_data({
                'title': _("NOTE UPDATE"),
                'data': order_changes['noteUpdate'],
            }))

        if order_changes.get('internal_note') or order_changes.get('general_customer_note'):
            receipts_data.append(self._prepare_preparation_grouped_data({
                'title': '',
                'data': [],
            }))

        order_fields = self.env['pos.order']._load_pos_data_fields(self.config_id)
        config_fields = self.env['pos.config']._load_pos_data_fields(self.config_id)
        preset_fields = self.env['pos.preset']._load_pos_data_fields(self.config_id)
        preset = self.preset_id if self.preset_id else False
        preset_time = self.preset_time or False

        base = {
            'order': self.read(order_fields, load=False)[0],
            'config': self.config_id.read(config_fields, load=False)[0],
            'company': self.company_id.read([], load=False)[0],
            'partner': self.partner_id.read([], load=False)[0] if self.partner_id else False,
            'preset': preset.read(preset_fields, load=False)[0] if preset else False,
            'extra_data': {
                'time': format_datetime(self.env, self.date_order),
                'employee_name': self.user_id.name if self.user_id else '',
                'preset_time': format_datetime(self.env, preset_time) if preset_time else False,
                'reprint': False,
                'internal_note': _get_str_notes(order_changes.get('internal_note', '')),
                'general_customer_note': order_changes.get('general_customer_note', ''),
            },
            'conditions': {
                'module_pos_restaurant': self.config_id.module_pos_restaurant,
            },
        }

        return [
            {**base, 'changes': changes}
            for changes in receipts_data
        ]

    def _order_change_receipts_generate_html(self, prep_categ_ids=None):
        last_order = self.env['pos.order'].search([], order='id desc', limit=1)
        report_name = 'point_of_sale.pos_order_change_receipt'
        data = self._order_change_receipt_generate_data(prep_categ_ids)
        rendered = []
        for d in data:
            rendered.append(last_order.env['ir.qweb']._render(report_name, values=d))
        return rendered

    def _order_change_receipt_generate_images(self, prep_categ_ids=None):
        content = self._order_change_receipts_generate_html(prep_categ_ids)
        images = []
        for c in content:
            image = self.env['ir.actions.report']._run_wkhtmltoimage([c], 500, 0)[0]
            images.append(image)
        return images

    def _canvas_to_raster(self, image_bytes: bytes):
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

    def _order_change_receipts_generate_raster(self, prep_categ_ids=None):
        images = self._order_change_receipt_generate_images(prep_categ_ids)
        processed = []

        # Wkhtmltoimage doesn't works in tests see def _run_wkhtmltoimage in ir.actions.report
        for image_bytes in images:
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
            xml = (
                f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
                f'<s:Body>'
                f'<epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">'
                f'<image width="{actual_width}" height="{actual_height}" align="center">{b64}</image>'
                f'<cut type="feed"/>'
                f'</epos-print>'
                f'</s:Body>'
                f'</s:Envelope>'
            )
            processed.append(xml)

        return processed
