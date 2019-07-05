# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models, tools
from odoo.tools.mimetypes import guess_mimetype


class PosOrderTicket(models.TransientModel):
    _name = 'pos.order.ticket'
    _description = 'Pos Order Ticket Reprint'

    pos_name = fields.Many2one('pos.config', string="POS Name", required=True)
    proxy_ip = fields.Char(related="pos_name.proxy_ip")
    ip_url = fields.Char(compute="_compute_ip_url")

    @api.depends('pos_name')
    def _compute_ip_url(self):
        for box in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if box.proxy_ip:
                if base_url[:5] == "https":
                    box.ip_url = "https://" + box.proxy_ip
                else:
                    box.ip_url = "http://" + box.proxy_ip + ":8069"

    def _amount_by_group(self, order_line):
        res = {}
        for line in order_line.lines:
            price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
            taxes = line.tax_ids_after_fiscal_position.compute_all(price_reduce, quantity=line.qty, product=line.product_id)['taxes']
            for tax in line.tax_ids_after_fiscal_position:
                group = tax.tax_group_id
                res.setdefault(group, {'amount': 0.0, 'base': 0.0})
                for t in taxes:
                    if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
                        res[group]['amount'] += t['amount']
                        res[group]['base'] += t['base']
        res = sorted(res.items(), key=lambda l: l[0].sequence)
        return [(l[0].name, l[1]['amount'], l[1]['base']) for l in res]

    def _generate_wrapped_product_name(self, product_name):
        MAX_LENGTH = 24
        wrapped = []
        name = product_name.split("]")[1]
        current_line = ""

        while (len(name) > 0):
            space_index = name.find(" ")
            if (space_index == -1):
                space_index = len(name)

            if (len(current_line) + space_index > MAX_LENGTH):
                if (len(current_line)):
                    wrapped.append(current_line)
                current_line = ""

            current_line += name[0:space_index + 1]
            name = name[space_index + 1:]

        if (len(current_line)):
            wrapped.append(current_line)
        return wrapped

    @api.multi
    def print_ticket(self):
        self.ensure_one()
        rec = self.env['pos.order'].browse(self.env.context.get('active_id', False))
        total = 0.0
        orderlines = []
        taxes = []
        statement_ids = []
        if rec.statement_ids:
            for statement in rec.statement_ids:
                if statement.amount < 0:
                    change = statement.amount
                    total = 0.0
                else:
                    total += statement.amount
                journal = statement.statement_id.journal_id.display_name
            statement_ids.append({
                "amount": total,
                "name": journal
            })
        img = base64.b64decode(rec.company_id.logo)
        mimetype = guess_mimetype(img, default='image/png')
        company = {
            "name": rec.company_id.name,
            "contact_address": rec.company_id.name,
            "phone": rec.company_id.phone,
            "vat": rec.company_id.vat,
            "email": rec.company_id.email,
            "website": rec.company_id.website,
            "logo": 'data:%s;base64,' % mimetype + rec.company_id.logo.decode('utf-8')
        }
        price_total = 0.0
        total_disc = 0.0
        for line in rec.lines:
            price_total += line.price_subtotal
            total_disc += line.price_unit * (line.discount/100) * line.qty
            orderlines.append({
                "quantity": line.qty,
                "price": line.price_unit,
                "discount": line.discount,
                "product_name": line.product_id.display_name,
                "product_name_wrapped": self._generate_wrapped_product_name(line.product_id.display_name),
                "price_display": line.price_subtotal,
                "price_with_tax": line.price_subtotal_incl,
                "unit_name": line.product_id.uom_name,
                "tax": [{
                    "name": tax.display_name,
                    "amount": tax.amount
                } for tax in line.tax_ids_after_fiscal_position],
            })
        tax_details = self._amount_by_group(rec)
        for tax in tax_details:
            taxes.append({
                'name': tax[0],
                'amount': tax[1]
            })
        product_price = self.env.ref('product.decimal_price')
        product_uom = self.env.ref('product.decimal_product_uom')
        report_data = {
            "receipt": {
                "cashier": rec.user_id.display_name,
                "orderlines": orderlines,
                "paymentlines": statement_ids,
                "total_with_tax": rec.amount_total,
                "total_tax": rec.amount_tax,
                "name": rec.pos_reference,
                "date": {"localestring": rec.date_order},
                "company": company,
                "subtotal": price_total,
                "discount": total_disc,
                "change": abs(change) if rec.statement_ids and change else 0.0,
                "tax_details": taxes
                },
            "pos": {
                "currency": {"decimals": rec.pricelist_id.currency_id.decimal_places},
                "dp": {
                    product_price.name: product_price.digits,
                    product_uom.name: product_uom.digits
                    }
                }
        }
        return {
            'type': 'ir.actions.client',
            'tag': 'print_ticket_action',
            'params': {'receipt_data': report_data, 'iot_box_url': self.ip_url},
        }
