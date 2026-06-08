# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from itertools import starmap, zip_longest

from odoo import api, fields, models
from odoo.fields import Command
from odoo.tools import is_html_empty


class SaleOrder(models.Model):
    _inherit = "sale.order"

    sale_order_template_id = fields.Many2one(
        comodel_name="sale.order.template",
        string="Template",
        store=True,
        readonly=False,
        check_company=True,
        index="btree_not_null",
        domain="""[
            ('template_type', '=', 'quotation'),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', company_id),
        ]""",
    )

    # === COMPUTE METHODS ===#

    @api.depends("partner_id", "sale_order_template_id")
    def _compute_note(self):
        super()._compute_note()
        for order in self.filtered("sale_order_template_id"):
            template = order.sale_order_template_id.with_context(lang=order.partner_id.lang)
            order.note = template.note if not is_html_empty(template.note) else order.note

    @api.depends("sale_order_template_id")
    def _compute_require_signature(self):
        super()._compute_require_signature()
        for order in self.filtered("sale_order_template_id"):
            order.require_signature = order.sale_order_template_id.require_signature

    @api.depends("sale_order_template_id")
    def _compute_require_payment(self):
        super()._compute_require_payment()
        for order in self.filtered("sale_order_template_id"):
            order.require_payment = order.sale_order_template_id.require_payment

    @api.depends("sale_order_template_id")
    def _compute_prepayment_percent(self):
        super()._compute_prepayment_percent()
        for order in self.filtered("sale_order_template_id"):
            if order.require_payment:
                order.prepayment_percent = order.sale_order_template_id.prepayment_percent

    @api.depends("sale_order_template_id")
    def _compute_validity_date(self):
        super()._compute_validity_date()
        for order in self.filtered("sale_order_template_id"):
            validity_days = order.sale_order_template_id.number_of_days
            if validity_days > 0:
                order.validity_date = fields.Date.context_today(order) + timedelta(validity_days)

    @api.depends("sale_order_template_id")
    def _compute_journal_id(self):
        super()._compute_journal_id()
        for order in self.filtered("sale_order_template_id"):
            order.journal_id = order.sale_order_template_id.journal_id

    # === ONCHANGE METHODS ===#

    @api.onchange("sale_order_template_id")
    def _onchange_sale_order_template_id(self):
        if not self.sale_order_template_id:
            return

        sale_order_template = self.sale_order_template_id.with_context(
            lang=self.partner_id.lang
        ).with_company(self.company_id)

        order_lines_data = [Command.clear()]
        order_lines_data += [
            Command.create(
                line._prepare_order_line_values(self.fiscal_position_id, self.currency_id)
            )
            for line in sale_order_template.sale_order_template_line_ids
        ]

        # set first line to sequence -99, so a resequence on first page doesn't cause following page
        # lines (that all have sequence 10 by default) to get mixed in the first page
        if len(order_lines_data) >= 2:
            order_lines_data[1][2]["sequence"] = -99

        self.order_line = order_lines_data

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        """Reload template for unsaved orders with unmodified lines & orders."""
        if self._origin or not self.sale_order_template_id:
            return

        def line_eqv(line, t_line):
            return (
                line
                and t_line
                and all(
                    line[fname] == t_line[fname]
                    for fname in ["product_id", "product_uom_id", "product_uom_qty", "display_type"]
                )
            )

        lines = self.order_line
        t_lines = self.sale_order_template_id.sale_order_template_line_ids

        if all(starmap(line_eqv, zip_longest(lines, t_lines))):
            self._onchange_sale_order_template_id()

    # === ACTION METHODS ===#

    def _get_confirmation_template(self):
        self.ensure_one()
        return self.sale_order_template_id.mail_template_id or super()._get_confirmation_template()

    def action_confirm(self):
        res = super().action_confirm()

        if self.env.context.get("send_email"):
            # Mail already sent in super method
            return res

        # When an order is confirmed from backend (send_email=False), if the quotation template has
        # a specified mail template, send it as it's probably meant to share additional information.
        for order in self:
            if order.sale_order_template_id.mail_template_id:
                order._send_order_notification_mail(order.sale_order_template_id.mail_template_id)
        return res

    def action_create_quotation_template(self):
        self.ensure_one()

        template_vals = self._prepare_template_order_values()
        new_template = self.env["sale.order.template"].create(template_vals)

        # Assign the newly created template to the current SO
        self.sale_order_template_id = new_template.id

        return new_template.get_record_default_action()

    # === TOOLING METHODS ===#

    def _prepare_template_order_values(self):
        """Prepare the dictionary of values to create a new quotation template from the current
        order.

        :return: `sale.order.template` create values
        :rtype: dict
        """
        self.ensure_one()
        template_lines = [
            Command.create(line._prepare_template_line_values()) for line in self.order_line
        ]

        return {
            "name": self.env._("Template from %s", self.name),
            "company_id": self.company_id.id,
            "journal_id": self.journal_id.id,
            "note": self.note,
            "require_signature": self.require_signature,
            "require_payment": self.require_payment,
            "prepayment_percent": self.prepayment_percent,
            "sale_order_template_line_ids": template_lines,
        }
