# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
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
    blackbox_pos_receipt_time = fields.Datetime("Receipt time", compute="_compute_blackbox_pos_receipt_time")
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
    blackbox_order_sequence = fields.Char(
        "Blackbox order sequence",
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

    @api.depends("blackbox_date", "blackbox_time")
    def _compute_blackbox_pos_receipt_time(self):
        for order in self:
            if order.blackbox_date and order.blackbox_time:
                order.blackbox_pos_receipt_time = datetime.strptime(
                    order.blackbox_date + " " + order.blackbox_time, "%d-%m-%Y %H:%M:%S"
                )
            else:
                order.blackbox_pos_receipt_time = False

    @api.ondelete(at_uninstall=False)
    def unlink_if_blackboxed(self):
        for order in self:
            if order.config_id.certified_blackbox_identifier:
                raise UserError(_("Deleting of registered orders is not allowed."))

    def write(self, values):
        for order in self:
            if order.config_id.certified_blackbox_identifier and order.state != "draft" and not order.lines.filtered(lambda l: l.product_id.id in self.env['pos.config']._get_work_products().ids) and not self.env.context.get('backend_recomputation'):
                white_listed_fields = [
                    "state",
                    "account_move",
                    "picking_id",
                    "invoice_id",
                    "last_order_preparation_change",
                    "partner_id",
                    "to_invoice",
                    "nb_print",
                ]

                for field in values:
                    if field not in white_listed_fields:
                        raise UserError(_("Modifying registered orders is not allowed."))

        return super().write(values)

    @api.model
    def create_log(self, orders):
        for order in orders:
            self.env["pos_blackbox_be.log"].sudo().create([{
                    "action": "create",
                    "model_name": self._name,
                    "record_name": order['pos_reference'],
                    "description": self._create_log_description(order),
                }])
            self.env['pos.session'].browse(order['session_id'])._update_pro_forma(order)

    def _create_log_description(self, order):
        decimal_places = self.env['res.currency'].browse(order['currency_id']).decimal_places
        lines = []
        total = 0
        rounding_applied = 0
        hash_string = ""
        title = ""
        for line in order["lines"]:
            line_description = "{qty} x {product_name}: {price}".format(
                qty=line["qty"],
                product_name=line["product_name"],
                price=round(line["price_subtotal_incl"], decimal_places),
            )

            if line["discount"]:
                line_description += " (disc: {discount}%)".format(
                    discount=line["discount"]
                )

            lines.append(line_description)
        total = (
            round(order["amount_total"], decimal_places)
            if order['state'] == "draft"
            else round(order["amount_paid"], decimal_places)
        )
        rounding_applied = (
            0
            if order['state'] == "draft"
            else round(
                order["amount_total"] - order["amount_paid"],
                decimal_places,
            )
        )
        hash_string = order["plu_hash"]
        sale_type = ""
        if round(order["amount_total"], decimal_places) > 0:
            sale_type = " SALES"
        elif round(order["amount_total"], decimal_places) < 0:
            sale_type = " REFUNDS"
        else:
            if len(order["lines"]) == 0 or order["lines"][0]["qty"] >= 0:
                sale_type = " SALES"
            else:
                sale_type = " REFUNDS"
        title = ("PRO FORMA" if order['state'] == "draft" else "NORMAL") + sale_type

        order_type = order['config_name'] + (
            " Pro Forma/" if order['state'] == "draft" else " Pos Order/"
        )

        description = '''
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
        FDM Signature: {fdmSignature}
        '''.format(
            title=title,
            create_date=order['create_date'],
            cashier_name=order['employee_name'],
            lines="\n* " + "\n* ".join(lines),
            total=total,
            pos_reference=order['pos_reference'],
            blackbox_sequence=order_type + str(order['blackbox_order_sequence']).zfill(5),
            hash=hash_string,
            pos_version=order['pos_version'],
            ticket_counters=order['blackbox_ticket_counters'],
            fdm_id=order['blackbox_unique_fdm_production_number'],
            config_name=order['config_name'],
            fdmIdentifier=order['certified_blackbox_identifier'],
            rounding_applied=rounding_applied,
            fdmSignature=order['blackbox_signature'],
        )

        return description

    def _refund(self):
        work_products_ids = self.env['pos.config']._get_work_products().ids
        for order in self:
            if order.config_id.certified_blackbox_identifier:
                for line in order.lines:
                    if line.product_id.id in work_products_ids:
                        raise UserError(_("Refunding of WORK IN/WORK OUT orders is not allowed."))
        return super()._refund()

    def action_pos_order_cancel(self):
        cancellable_orders = self.filtered(lambda order: order.state == 'draft')
        if cancellable_orders:
            for order in cancellable_orders:
                order.write({
                    'blackbox_tax_category_a': 0,
                    'blackbox_tax_category_b': 0,
                    'blackbox_tax_category_c': 0,
                    'blackbox_tax_category_d': 0,
                })
        return super().action_pos_order_cancel()


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    vat_letter = fields.Selection(
        [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
        help="The VAT letter is related to the amount of the tax. A=21%, B=12%, C=6% and D=0%.",
    )

    def write(self, values):
        if values.get("vat_letter"):
            raise UserError(_("Can't modify fields related to the Fiscal Data Module."))

        return super().write(values)
