from collections import defaultdict

from odoo import Command, _, api, fields, models


class PurchaseOrderGroup(models.Model):
    _name = "purchase.order.group"
    _description = "Technical model to group PO for call to tenders"

    order_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="purchase_group_id",
    )

    def write(self, vals):
        res = super().write(vals)
        self.filtered(lambda g: len(g.order_ids) <= 1).unlink()
        return res


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="Agreement",
        index="btree_not_null",
        copy=False,
    )
    requisition_type = fields.Selection(related="requisition_id.requisition_type")

    purchase_group_id = fields.Many2one(
        comodel_name="purchase.order.group",
        index="btree_not_null",
    )
    alternative_po_ids = fields.One2many(
        comodel_name="purchase.order",
        related="purchase_group_id.order_ids",
        string="Alternative POs",
        readonly=False,
        domain="[('id', '!=', id), ('state', '=', 'draft')]",
        check_company=True,
        help="Other potential purchase orders for purchasing products",
    )

    @api.onchange("requisition_id")
    def _onchange_requisition_id(self):
        if not self.requisition_id:
            return

        self = self.with_company(self.company_id)
        requisition = self.requisition_id
        if self.partner_id:
            partner = self.partner_id
        else:
            partner = requisition.vendor_id
        payment_term = partner.property_supplier_payment_term_id

        FiscalPosition = self.env["account.fiscal.position"]
        fpos = FiscalPosition.with_company(self.company_id)._get_fiscal_position(
            partner
        )

        self.partner_id = partner.id
        self.fiscal_position_id = fpos.id
        self.payment_term_id = payment_term.id
        self.company_id = requisition.company_id.id
        self.currency_id = requisition.currency_id.id
        if not self.origin or requisition.name not in self.origin.split(", "):
            if self.origin:
                if requisition.name:
                    self.origin = self.origin + ", " + requisition.name
            else:
                self.origin = requisition.name
        self.notes = requisition.description
        if requisition.date_start:
            self.date_order = max(
                fields.Datetime.now(),
                fields.Datetime.to_datetime(requisition.date_start),
            )
        else:
            self.date_order = fields.Datetime.now()

        if self.state != "draft":
            return
        order_lines = []
        for line in requisition.line_ids:
            product_lang = line.product_id.with_context(
                lang=partner.lang or self.env.user.lang, partner_id=partner.id
            )
            name = product_lang.display_name
            if product_lang.description_purchase:
                name += "\n" + product_lang.description_purchase

            taxes_ids = fpos.map_tax(
                line.product_id.supplier_taxes_id.filtered(
                    lambda tax: any(
                        tax._serves_company(c)
                        for c in requisition.company_id.parent_ids
                    )
                )
            ).ids

            product_qty = (
                line.product_qty
                if requisition.requisition_type == "purchase_template"
                else 0
            )
            order_line_values = line._prepare_purchase_order_line(
                name=name,
                product_qty=product_qty,
                price_unit=line.price_unit,
                taxes_ids=taxes_ids,
            )
            order_lines.append((0, 0, order_line_values))
        self.line_ids = order_lines

    def action_confirm(self):
        if self.alternative_po_ids and not self.env.context.get(
            "skip_alternative_check", False
        ):
            alternative_po_ids = self.alternative_po_ids.filtered(
                lambda po: po.state == "draft" and po.id not in self.ids
            )
            if alternative_po_ids:
                view = self.env.ref(
                    "purchase_requisition.purchase_requisition_alternative_warning_form"
                )
                return {
                    "name": _("What about the alternative Requests for Quotations?"),
                    "type": "ir.actions.act_window",
                    "view_mode": "form",
                    "res_model": "purchase.requisition.alternative.warning",
                    "views": [(view.id, "form")],
                    "target": "new",
                    "context": dict(
                        self.env.context,
                        default_alternative_po_ids=alternative_po_ids.ids,
                        default_po_ids=self.ids,
                    ),
                }
        return super().action_confirm()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        if self.env.context.get("origin_po_id"):
            origin_po_id = self.env["purchase.order"].browse(
                self.env.context.get("origin_po_id")
            )
            if origin_po_id.purchase_group_id:
                origin_po_id.purchase_group_id.order_ids |= orders
            else:
                self.env["purchase.order.group"].create(
                    {"order_ids": [Command.set(origin_po_id.ids + orders.ids)]}
                )
        for order in orders:
            if order.requisition_id:
                order.message_post_with_source(
                    "mail.message_origin_link",
                    render_values={"self": order, "origin": order.requisition_id},
                    subtype_xmlid="mail.mt_note",
                )
        return orders

    def write(self, vals):
        if vals.get("purchase_group_id", False):
            orig_purchase_group = self.purchase_group_id
        result = super().write(vals)
        if vals.get("requisition_id"):
            for order in self:
                order.message_post_with_source(
                    "mail.message_origin_link",
                    render_values={
                        "self": order,
                        "origin": order.requisition_id,
                        "edit": True,
                    },
                    subtype_xmlid="mail.mt_note",
                )
        if vals.get("alternative_po_ids", False):
            if not self.purchase_group_id and len(self.alternative_po_ids + self) > len(
                self
            ):
                self.env["purchase.order.group"].create(
                    {"order_ids": [Command.set(self.ids + self.alternative_po_ids.ids)]}
                )
            elif self.purchase_group_id and len(self.alternative_po_ids + self) <= 1:
                self.purchase_group_id.unlink()
        if vals.get("purchase_group_id", False):
            additional_groups = orig_purchase_group - self.purchase_group_id
            if additional_groups:
                additional_pos = (
                    additional_groups.order_ids - self.purchase_group_id.order_ids
                )
                additional_groups.unlink()
                if additional_pos:
                    self.purchase_group_id.order_ids |= additional_pos

        return result

    def action_create_alternative(self):
        ctx = dict(**self.env.context, default_origin_po_id=self.id)
        return {
            "name": _("Create alternative"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "purchase.requisition.create.alternative",
            "view_id": self.env.ref(
                "purchase_requisition.purchase_requisition_create_alternative_form"
            ).id,
            "target": "new",
            "context": ctx,
        }

    def action_compare_alternative_lines(self):
        ctx = dict(
            self.env.context,
            search_default_groupby_product=True,
            purchase_order_id=self.id,
        )
        view_id = self.env.ref(
            "purchase_requisition.purchase_order_line_compare_tree"
        ).id
        return {
            "name": _("Compare Order Lines"),
            "type": "ir.actions.act_window",
            "view_mode": "list",
            "res_model": "purchase.order.line",
            "views": [(view_id, "list")],
            "domain": [
                ("order_id", "in", (self | self.alternative_po_ids).ids),
                ("display_type", "=", False),
            ],
            "context": ctx,
        }

    def get_tender_best_lines(self):
        product_to_best_price_line = defaultdict(
            lambda: self.env["purchase.order.line"]
        )
        product_to_best_date_line = defaultdict(lambda: self.env["purchase.order.line"])
        product_to_best_price_unit = defaultdict(
            lambda: self.env["purchase.order.line"]
        )
        po_alternatives = self | self.alternative_po_ids

        for line in po_alternatives.line_ids:
            if (
                not line.product_qty
                or not line.price_total_cc
                or line.state in ["done", "cancel"]
            ):
                continue

            if not product_to_best_price_line[line.product_id]:
                product_to_best_price_line[line.product_id] = line
                product_to_best_price_unit[line.product_id] = line
            else:
                price_subtotal = line.price_total_cc
                price_unit = line.price_total_cc / line.product_qty
                current_price_subtotal = product_to_best_price_line[line.product_id][
                    0
                ].price_total_cc
                current_price_unit = (
                    product_to_best_price_unit[line.product_id][0].price_total_cc
                    / product_to_best_price_unit[line.product_id][0].product_qty
                )

                if current_price_subtotal > price_subtotal:
                    product_to_best_price_line[line.product_id] = line
                elif current_price_subtotal == price_subtotal:
                    product_to_best_price_line[line.product_id] |= line
                if current_price_unit > price_unit:
                    product_to_best_price_unit[line.product_id] = line
                elif current_price_unit == price_unit:
                    product_to_best_price_unit[line.product_id] |= line

            if (
                not product_to_best_date_line[line.product_id]
                or product_to_best_date_line[line.product_id][0].date_commitment
                > line.date_commitment
            ):
                product_to_best_date_line[line.product_id] = line
            elif (
                product_to_best_date_line[line.product_id][0].date_commitment
                == line.date_commitment
            ):
                product_to_best_date_line[line.product_id] |= line

        best_price_ids = set()
        best_date_ids = set()
        best_price_unit_ids = set()
        for lines in product_to_best_price_line.values():
            best_price_ids.update(lines.ids)
        for lines in product_to_best_date_line.values():
            best_date_ids.update(lines.ids)
        for lines in product_to_best_price_unit.values():
            best_price_unit_ids.update(lines.ids)
        return list(best_price_ids), list(best_date_ids), list(best_price_unit_ids)

    def _prepare_grouped_data(self, rfq):
        match_fields = super()._prepare_grouped_data(rfq)
        return match_fields + (rfq.requisition_id.id,)

    def _merge_alternative_po(self, rfqs):
        if self.alternative_po_ids:
            super()._merge_alternative_po(rfqs)
            self.alternative_po_ids += rfqs.mapped("alternative_po_ids")


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    price_total_cc = fields.Monetary(
        string="Company Subtotal",
        currency_field="company_currency_id",
        compute="_compute_price_total_cc",
        store=True,
    )
    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
    )

    @api.depends("price_subtotal", "order_id.currency_rate")
    def _compute_price_total_cc(self):
        for line in self:
            line.price_total_cc = line.price_subtotal / line.order_id.currency_rate

    def _get_requisition_line(self):
        self.check_singleton()
        matched = None
        for req_line in self.order_id.requisition_id.line_ids:
            if req_line.product_id != self.product_id:
                continue
            matched = req_line
            if req_line.product_uom_id == self.product_uom_id:
                break
        return matched or self.env["purchase.requisition.line"]

    def _get_line_description_from_product(self, product_lang):
        name = super()._get_line_description_from_product(product_lang)
        return self._get_requisition_line()._add_description_variants(name)

    def action_clear_quantities(self):
        zeroed_lines = self.filtered(lambda l: l.state not in ["done", "cancel"])
        zeroed_lines.write({"product_qty": 0})
        if len(self) > len(zeroed_lines):
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Some not cleared"),
                    "message": _(
                        "Some quantities were not cleared because their status is not a RFQ status."
                    ),
                    "sticky": False,
                },
            }
        return False

    def action_choose(self):
        order_lines = (self.order_id | self.order_id.alternative_po_ids).mapped(
            "line_ids"
        )
        order_lines = order_lines.filtered(
            lambda l: (
                l.product_qty
                and l.product_id.id in self.product_id.ids
                and l.id not in self.ids
            )
        )
        if order_lines:
            return order_lines.action_clear_quantities()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Nothing to clear"),
                "message": _("There are no quantities to clear."),
                "sticky": False,
            },
        }
