# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from io import BytesIO
from odoo import models, api, _
from odoo.tools.misc import format_datetime, format_date

import qrcode


class PosOrderReceipt(models.AbstractModel):
    _name = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    @api.model
    def get_receipt_template_for_pos_frontend(self):
        names = [
            'point_of_sale.pos_order_receipt_header',
            'point_of_sale.pos_order_receipt_style',
            'point_of_sale.pos_orderline_receipt_information',
            'point_of_sale.pos_orderline_receipt',
            'point_of_sale.pos_order_receipt_footer',
            'point_of_sale.pos_order_receipt',
        ]
        return [[name, self.env['ir.qweb']._get_template(name)[1]] for name in names]

    @api.model
    def _order_receipt_format_currency(self, amount):
        return self.currency_id.format(amount).replace('\xa0', ' ')  # Wkhtmltoimage does not support non-breaking spaces

    def _order_receipt_generate_taxe_data(self):
        tax_totals = self._get_order_tax_totals()  # Use account helpers to compute tax totals
        discount_amount = sum(line._get_discount_amount() for line in self.lines)
        rounding = tax_totals.get('cash_rounding_base_amount_currency', 0)

        return {
            'same_tax_base': tax_totals['same_tax_base'],
            'discount_amount': self._order_receipt_format_currency(-abs(discount_amount)) if discount_amount else False,
            'rounding_amount': self._order_receipt_format_currency(rounding) if rounding else False,
            'tax_amount': self._order_receipt_format_currency(tax_totals['tax_amount_currency']),
            'total_amount': self._order_receipt_format_currency(tax_totals['total_amount_currency']),
            'subtotal_amount': self._order_receipt_format_currency(tax_totals['base_amount_currency']),
            'taxes': [{
                'name': tax['group_name'],
                'amount': self._order_receipt_format_currency(tax['tax_amount']),
                'amount_base': self._order_receipt_format_currency(tax['base_amount_currency']),
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
            data['lot_names'] = line.pack_lot_ids.mapped('lot_name') if line.pack_lot_ids else False
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

        img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
        datas = img.getdata()
        newData = []

        # Make white background fully transparent
        for item in datas:
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                newData.append((255, 255, 255, 0))
                continue
            newData.append(item)

        img.putdata(newData)

        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode("utf-8")

    def order_receipt_generate_data(self, basic_receipt=False):
        self.ensure_one()

        company_fields = self.env['res.company']._load_pos_data_fields(self.config_id)
        partner_fields = self.env['res.partner']._load_pos_data_fields(self.config_id)
        preset_fields = self.env['pos.preset']._load_pos_data_fields(self.config_id)
        order_fields = self.env['pos.order']._load_pos_data_fields(self.config_id)
        config_fields = self.env['pos.config']._load_pos_data_fields(self.config_id)

        use_qr_code = self.company_id.point_of_sale_ticket_portal_url_display_mode != 'url'
        company = self.company_id
        config_logo = 'data:image/png;base64,' + base64.b64encode(base64.b64decode(self.config_id.logo)).decode('utf-8')
        qr_code_value = f"{self.env.company.get_base_url()}/pos/ticket?order_uuid={self.uuid}"

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
                'preset_datetime': format_datetime(self.env, self.preset_time) if self.preset_time else False,
                'partner_vat_label': company.country_id.vat_label or _("Tax ID"),
                'self_invoicing_url': f"{self.env.company.get_base_url()}/pos/ticket",
                'prices': self._order_receipt_generate_taxe_data(),
                'cashier_name': self.user_id.name.split(' ')[0] if self.user_id else '',
                'company_state_name': company.state_id.name if company.state_id else False,
                'company_country_name': company.country_id.name if company.country_id else False,
                'formated_date_order': format_datetime(self.env, self.date_order),
                'formated_shipping_date': format_date(self.env, self.shipping_date) if self.shipping_date else False
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
