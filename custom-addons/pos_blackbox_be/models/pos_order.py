# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _
from datetime import datetime


class PosOrder(models.Model):
    _inherit = "pos.order"

    blackbox_date = fields.Char(
        "Fiscal Data Module date",
        help="Date returned by the Fiscal Data Module.",
        readonly=True,
    )
    blackbox_time = fields.Char(
        "Fiscal Data Module time",
        help="Time returned by the Fiscal Data Module.",
        readonly=True,
    )
    blackbox_pos_receipt_time = fields.Datetime("Receipt time", readonly=True)
    blackbox_ticket_counters = fields.Char(
        "Fiscal Data Module ticket counters",
        help="Ticket counter returned by the Fiscal Data Module (format: counter / total event type)",
        readonly=True,
    )
    blackbox_unique_fdm_production_number = fields.Char(
        "Fiscal Data Module ID",
        help="Unique ID of the blackbox that handled this order",
        readonly=True,
    )
    blackbox_vsc_identification_number = fields.Char(
        "VAT Signing Card ID",
        help="Unique ID of the VAT signing card that handled this order",
        readonly=True,
    )
    blackbox_signature = fields.Char(
        "Electronic signature",
        help="Electronic signature returned by the Fiscal Data Module",
        readonly=True,
    )
    blackbox_tax_category_a = fields.Monetary(
        readonly=True,
        string="Total tax for category A",
        help="This is the total amount of the 21% tax",
    )
    blackbox_tax_category_b = fields.Monetary(
        readonly=True,
        string="Total tax for category B",
        help="This is the total amount of the 12% tax",
    )
    blackbox_tax_category_c = fields.Monetary(
        readonly=True,
        string="Total tax for category C",
        help="This is the total amount of the 6% tax",
    )
    blackbox_tax_category_d = fields.Monetary(
        readonly=True,
        string="Total tax for category D",
        help="This is the total amount of the 0% tax",
    )
    plu_hash = fields.Char(help="Eight last characters of PLU hash")
    pos_version = fields.Char(help="Version of Odoo that created the order")

    def _create_log_description(self, blackbox_order_sequence, custom_data=None):
        currency = self.currency_id
        lines = []
        total = 0
        rounding_applied = 0
        hash_string = ''
        title = ''

        if custom_data:
            for line in custom_data['lines']:
                line = line[2]
                product_name = self.env['product.product'].browse(line['product_id']).name
                line_description = "{qty} x {product_name}: {price}".format(
                    qty=line['qty'],
                    product_name=product_name,
                    price=round(line['price_subtotal_incl'], currency.decimal_places)
                )

                if line['discount']:
                    line_description += " (disc: {discount}%)".format(discount=line['discount'])

                lines.append(line_description)
            total = round(custom_data['amount_total'], currency.decimal_places) if self.state == "draft" else round(custom_data['amount_paid'], currency.decimal_places)
            rounding_applied = 0 if self.state == "draft" else round(custom_data['amount_total'] - custom_data['amount_paid'], currency.decimal_places)
            hash_string = custom_data['blackbox_plu_hash']
            sale_type = ""
            if round(custom_data['amount_total'], currency.decimal_places) > 0:
                sale_type = " SALES"
            elif round(custom_data['amount_total'], currency.decimal_places) < 0:
                sale_type = " REFUNDS"
            else:
                if len(custom_data['lines']) and custom_data['lines'][0][2]['qty'] >= 0:
                    sale_type = " SALES"
                else:
                    sale_type = " REFUNDS"
            title = ("PRO FORMA" if self.state == "draft" else "NORMAL") + sale_type
        else:
            for line in self.lines:
                line_description = f"{line.qty} x {line.product_id.name}: {round(line.price_subtotal_incl, currency.decimal_places)}"

                if line.discount:
                    line_description += f" (disc: {line.discount}%)"

                lines.append(line_description)
            total = round(self.amount_total, currency.decimal_places) if self.state == "draft" else round(self.amount_paid, currency.decimal_places)
            rounding_applied = 0 if self.state == "draft" else round(self.amount_total - self.amount_paid, currency.decimal_places)
            hash_string = self.plu_hash

            sale_type = ""
            rounded_total_amount = round(self.amount_total, currency.decimal_places)
            if rounded_total_amount > 0:
                sale_type = " SALES"
            elif rounded_total_amount < 0:
                sale_type = " REFUNDS"
            else:
                if len(self.lines) and self.lines[0].qty >= 0:
                    sale_type = " SALES"
                else:
                    sale_type = " REFUNDS"

            title = ("PRO FORMA" if self.state == "draft" else "NORMAL") + sale_type

        order_type = self.config_id.name + (' Pro Forma/' if self.state == 'draft' else ' Pos Order/')

        description = """
        {title}
        Date: {create_date}
        Internal Ref: {pos_reference}
        Sequence: {blackbox_sequence}
        Cashier: {cashier_name}
        Order lines: {lines}
        Total: {total}
        Rounding: {rounding_applied}
        Ticket Counter: {ticket_counters}
        Hash: {hash}
        POS Version: {pos_version}
        FDM ID: {fdm_id}
        POS ID: {config_name}
        FDM Identifier: {fdmIdentifier}
        """.format(
            title=title,
            create_date=self.create_date,
            cashier_name=self.employee_id.name or self.user_id.name,
            lines="\n* " + "\n* ".join(lines),
            total=total,
            pos_reference=self.pos_reference,
            blackbox_sequence=order_type + f"{blackbox_order_sequence:05}",
            hash=hash_string,
            pos_version=self.pos_version,
            ticket_counters=custom_data['blackbox_ticket_counters'] if custom_data else self.blackbox_ticket_counters,
            fdm_id=custom_data['blackbox_unique_fdm_production_number'] if custom_data else self.blackbox_unique_fdm_production_number,
            config_name=self.config_id.name,
            fdmIdentifier=self.config_id.certified_blackbox_identifier,
            rounding_applied=rounding_applied,
        )

        return description

    @api.ondelete(at_uninstall=False)
    def unlink_if_blackboxed(self):
        for order in self:
            if order.config_id.iface_fiscal_data_module:
                raise UserError(_("Deleting of registered orders is not allowed."))

    def write(self, values):
        for order in self:
            if order.config_id.iface_fiscal_data_module and order.state != "draft":
                white_listed_fields = [
                    "state",
                    "account_move",
                    "picking_id",
                    "invoice_id",
                    "last_order_preparation_change",
                    "partner_id",
                    "to_invoice"
                ]

                for field in values:
                    if field not in white_listed_fields:
                        raise UserError(_("Modifying registered orders is not allowed."))

        return super(PosOrder, self).write(values)

    @api.model
    def create_from_ui(self, orders, draft=False):
        res = super().create_from_ui(orders, draft)
        if self.env['pos.session'].browse(orders[0]['data']['pos_session_id']).config_id.iface_fiscal_data_module:
            for order in orders:
                for order_res in res:
                    if not order['data'].get('server_id') and order_res['pos_reference'] == order['data']['name']:
                        order['data']['server_id'] = order_res['id']
            self.create_log(orders)
        return res

    @api.model
    def create_log(self, orders, custom_data=False):
        order_ids = self.env['pos.order'].browse([order['data']['server_id'] for order in orders])
        orders_bb_sequence = {order['data']['name']: order['data']['blackbox_order_sequence'] for order in orders if order['data'].get('blackbox_order_sequence')}
        for order in order_ids:
            if order.config_id.iface_fiscal_data_module:
                custom_order = order._get_custom_data(order, orders) if custom_data else None
                self.env["pos_blackbox_be.log"].sudo().create([{
                    "action": "create",
                    "model_name": order._name,
                    "record_name": order.pos_reference,
                    "description": order._create_log_description(orders_bb_sequence[order.pos_reference], custom_data=custom_order),
                }])
                if custom_order:
                    order.session_id._update_pro_forma(order, custom_order)
                else:
                    order.session_id._update_pro_forma(order)

    def _get_custom_data(self, order, orders):
        custom_data = {}
        for order_data in orders:
            if order_data['data']['name'] == order.pos_reference:
                custom_data = order_data['data']
                break
        return custom_data

    @api.model
    def _order_fields(self, ui_order):
        fields = super()._order_fields(ui_order)

        config_id = self.env["pos.session"].browse(fields["session_id"]).config_id

        if config_id.certified_blackbox_identifier:
            date = ui_order.get("blackbox_date")
            time = ui_order.get("blackbox_time")

            update_fields = {
                "blackbox_date": date,
                "blackbox_time": time,
                "blackbox_pos_receipt_time": datetime.strptime(
                    date + " " + time, "%d-%m-%Y %H:%M:%S"
                ) if date else False,
                "blackbox_ticket_counters": ui_order.get("blackbox_ticket_counters"),
                "blackbox_unique_fdm_production_number": ui_order.get("blackbox_unique_fdm_production_number"),
                "blackbox_vsc_identification_number": ui_order.get("blackbox_vsc_identification_number"),
                "blackbox_signature": ui_order.get("blackbox_signature"),
                "blackbox_tax_category_a": ui_order.get("blackbox_tax_category_a"),
                "blackbox_tax_category_b": ui_order.get("blackbox_tax_category_b"),
                "blackbox_tax_category_c": ui_order.get("blackbox_tax_category_c"),
                "blackbox_tax_category_d": ui_order.get("blackbox_tax_category_d"),
                "plu_hash": ui_order.get("blackbox_plu_hash"),
                "pos_version": ui_order.get("blackbox_pos_version"),
            }

            fields.update(update_fields)

        return fields

    def _refund(self):
        for order in self:
            if order.config_id.iface_fiscal_data_module:
                for line in self.lines:
                    if line.product_id in [self.env.ref('pos_blackbox_be.product_product_work_in', raise_if_not_found=False), self.env.ref('pos_blackbox_be.product_product_work_out', raise_if_not_found=False)]:
                        raise UserError(_("Refunding of WORK IN/WORK OUT orders is not allowed."))
        return super()._refund()


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    vat_letter = fields.Selection(
        [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
        help="The VAT letter is related to the amount of the tax. A=21%, B=12%, C=6% and D=0%.",
    )

    def write(self, values):
        if values.get("vat_letter"):
            raise UserError(_("Can't modify fields related to the Fiscal Data Module."))

        return super(PosOrderLine, self).write(values)
