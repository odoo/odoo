from itertools import groupby

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog

INVOICE_STATE = [
    ("no", "Nothing to invoice"),
    ("to do", "To invoice"),
    ("partial", "Partially invoiced"),
    ("done", "Fully invoiced"),
    ("over done", "Over-invoiced"),
]

_debug = DebugLog(__name__)


class MixinOrderInvoice(models.AbstractModel):
    _name = "mixin.order.invoice"
    _inherit = ["mixin.order.state.rollup"]
    _description = "Order Invoice Integration"

    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string="Invoices",
        compute="_compute_invoices",
        search="_search_invoice_ids",
    )
    invoice_count = fields.Integer(compute="_compute_invoices")
    invoice_state = fields.Selection(
        selection=INVOICE_STATE,
        string="Invoice Status",
        compute="_compute_invoice_state",
        default="no",
        store=True,
        copy=False,
    )
    force_fully_invoiced = fields.Boolean(
        copy=False,
        help="Report this order as fully invoiced regardless of its lines.",
    )

    def _get_invoice_move_types(self):
        direction = self._invoice_move_direction
        return (f"{direction}_invoice", f"{direction}_refund")

    @api.depends(
        "line_ids.invoice_line_ids",
        "line_ids.invoice_line_ids.move_id.reversal_move_ids",
    )
    def _compute_invoices(self):
        move_types = self._get_invoice_move_types()
        refund_type = move_types[1]

        order_invoices = {}
        all_invoice_ids = set()
        for order in self:
            invoices = order.line_ids.invoice_line_ids.move_id.filtered(
                lambda r: r.move_type in move_types,
            )
            order_invoices[order.id] = set(invoices.ids)
            all_invoice_ids.update(invoices.ids)

        orphan_refunds_by_reversed_id = self._get_orphan_refunds_by_reversed_id(
            all_invoice_ids,
            refund_type,
        )

        AccountMove = self.env["account.move"]
        for order in self:
            invoice_ids = order_invoices.get(order.id, set())
            pending = list(invoice_ids)
            while pending:
                inv_id = pending.pop()
                for orphan_id in orphan_refunds_by_reversed_id.get(inv_id, ()):
                    if orphan_id not in invoice_ids:
                        invoice_ids.add(orphan_id)
                        pending.append(orphan_id)
            order.invoice_ids = AccountMove.browse(sorted(invoice_ids))
            order.invoice_count = len(invoice_ids)
            if _debug.logic.enabled and len(invoice_ids) != len(
                order_invoices.get(order.id, ())
            ):
                _debug.logic(
                    "orphan_refunds_attached",
                    order=order,
                    invoices=len(invoice_ids),
                )

    def _get_orphan_refunds_by_reversed_id(self, invoice_ids, refund_type):
        """Map every invoice/refund id reachable from `invoice_ids` through a
        chain of reversals to the orphan refund ids that reverse it -- an
        orphan refund can itself be reversed by a further orphan refund, so
        this resolves the whole chain, not just its first level."""
        orphan_refunds_by_reversed_id = {}
        known_ids = set(invoice_ids)
        frontier = set(invoice_ids)
        while frontier:
            orphans = self.env["account.move"].search(
                [
                    ("reversed_entry_id", "in", list(frontier)),
                    ("move_type", "=", refund_type),
                    ("id", "not in", list(known_ids)),
                ],
            )
            if not orphans:
                break
            frontier = set()
            for refund in orphans:
                orphan_refunds_by_reversed_id.setdefault(
                    refund.reversed_entry_id.id,
                    [],
                ).append(refund.id)
                known_ids.add(refund.id)
                frontier.add(refund.id)
        _debug.perf.count(
            "orphan_refund_chain",
            seeds=len(invoice_ids),
            reversed_entries=len(orphan_refunds_by_reversed_id),
        )
        return orphan_refunds_by_reversed_id

    def _search_invoice_ids(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        move_types = self._get_invoice_move_types()

        def linked(condition=None):
            conditions = [("move_id.move_type", "in", move_types)]
            if condition:
                conditions.append(condition)
            return Domain("line_ids.invoice_line_ids", "any", conditions)

        if operator != "in" or not value:
            return linked(("move_id", operator, value))

        move_ids = [v for v in value if v is not False]
        matched = Domain.FALSE
        if move_ids:
            matched = linked(("move_id", "in", move_ids))
        if False in value:
            matched |= ~linked()
        return matched

    @api.depends(
        "state", "line_ids.invoice_state", "invoice_ids", "force_fully_invoiced"
    )
    def _compute_invoice_state(self):
        forced_orders = self.filtered("force_fully_invoiced")
        forced_orders.invoice_state = "done"
        confirmed_orders = (self - forced_orders).filtered(lambda o: o.state == "done")
        (self - forced_orders - confirmed_orders).invoice_state = "no"
        _debug.perf.count(
            "invoice_state_rollup",
            orders=len(self),
            forced=len(forced_orders),
            confirmed=len(confirmed_orders),
        )
        if not confirmed_orders:
            return

        line_invoice_state_all, pending_no_ids = confirmed_orders._rollup_line_states(
            "invoice_state", nothing_may_be_pending=True
        )

        for order in confirmed_orders:
            states = line_invoice_state_all.get(order._origin.id, set())
            if not states:
                order.invoice_state = "no"
                continue
            order.invoice_state = order._resolve_invoice_state(
                states,
                order._origin.id in pending_no_ids,
            )
            _debug.logic(
                "invoice_state",
                order=order,
                state=order.invoice_state,
                line_states=",".join(sorted(states)),
            )

    def _resolve_invoice_state(self, states, nothing_is_pending):
        self.check_singleton()
        if "over done" in states:
            return "over done"
        if "partial" in states:
            return "partial"
        billed = "done" in states
        outstanding = "to do" in states or nothing_is_pending
        if billed and outstanding:
            return "partial"
        if billed:
            return "done"
        if outstanding:
            return self._get_outstanding_invoice_state(states)
        return "no"

    def _get_outstanding_invoice_state(self, states):
        self.check_singleton()
        return "to do"

    def action_force_invoice_state(self):
        _debug.lifecycle("invoice_state_forced", orders=self, forced=True)
        self.force_fully_invoiced = True

    def action_unforce_invoice_state(self):
        _debug.lifecycle("invoice_state_forced", orders=self, forced=False)
        self.force_fully_invoiced = False

    @api.readonly
    def action_view_invoice(self, invoices=False):
        if not invoices:
            invoices = self.mapped("invoice_ids")

        direction = self._invoice_move_direction
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            f"account.action_move_{direction}_invoice_type",
        )

        if len(invoices) > 1:
            action["domain"] = [("id", "in", invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref("account.view_move_form").id, "form")]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = invoices.id
        else:
            action = {"type": "ir.actions.act_window_close"}

        context = {"default_move_type": f"{direction}_invoice"}
        if len(self) == 1:
            context.update(self._prepare_invoice_action_context())
        action["context"] = context
        return action

    def _prepare_invoice_action_context(self):
        self.check_singleton()
        pt_field = self._get_partner_payment_term_field()
        return {
            "default_partner_id": self.partner_id.id,
            "default_invoice_payment_term_id": (
                self.payment_term_id.id
                or self.partner_id[pt_field].id
                or self.env["account.move"]
                .default_get(["invoice_payment_term_id"])
                .get("invoice_payment_term_id")
            ),
        }

    def _get_invoice_grouping_keys(self):
        return ["company_id", "partner_id", "currency_id", "fiscal_position_id"]

    def _get_invoice_partner(self):
        self.check_singleton()
        return self.partner_id

    def _prepare_invoice_vals(self):
        self.check_singleton()
        direction = self._invoice_move_direction
        move_type = self.env.context.get("default_move_type", f"{direction}_invoice")
        invoice_partner = self._get_invoice_partner()
        values = {
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "partner_id": invoice_partner.id,
            "invoice_payment_term_id": self.payment_term_id.id,
            "fiscal_position_id": (
                self.fiscal_position_id
                or self.env["account.fiscal.position"]._get_fiscal_position(
                    invoice_partner,
                )
            ).id,
            "invoice_user_id": self.user_id.id,
            "move_type": move_type,
            "narration": self.notes,
            "invoice_origin": self.name,
            "invoice_line_ids": [],
        }
        if self.journal_id:
            values["journal_id"] = self.journal_id.id
        return values

    def _create_invoices(self, grouped=False, final=False, date=None):
        if not self.env["account.move"].has_access("create"):
            try:
                self.check_access("write")
            except AccessError:
                _debug.logic("create_invoices_denied", orders=self, reason="no_access")
                return self.env["account.move"]

        invoice_vals_list = []
        sequence = self._get_invoice_line_sequence_start()
        for order in self:
            order = order._get_invoicing_order()
            invoice_vals = order._prepare_invoice_vals()
            line_commands, sequence = order._prepare_invoice_line_commands(
                order._get_invoiceable_lines(final),
                sequence,
            )
            if not line_commands:
                _debug.logic("order_not_invoiceable", order=order, reason="no_lines")
                continue
            invoice_vals["invoice_line_ids"] += line_commands
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            if self.env.context.get("raise_if_nothing_to_invoice", True):
                _debug.logic("nothing_to_invoice", orders=self, raising=True)
                raise UserError(self._get_nothing_to_invoice_error_message())
            _debug.logic("nothing_to_invoice", orders=self, raising=False)
            return self.env["account.move"]

        if not grouped:
            invoice_vals_list = self._group_invoice_vals(invoice_vals_list)
        invoice_vals_list = self._post_group_invoice_vals(invoice_vals_list)

        with _debug.perf(
            "create_invoices",
            cr=self.env.cr,
            orders=self,
            invoices=len(invoice_vals_list),
        ):
            moves = self._create_invoice_moves(invoice_vals_list)

            self._switch_negative_moves(moves, final)

            self._post_create_invoices(moves)
        _debug.lifecycle(
            "invoices_created",
            orders=self,
            invoices=moves,
            final=final,
            grouped=grouped,
        )
        return moves

    def _get_invoicing_order(self):
        self.check_singleton()
        return self.with_company(self.company_id)

    def _get_invoice_line_sequence_start(self):
        return 10

    def _post_group_invoice_vals(self, invoice_vals_list):
        return invoice_vals_list

    def _create_invoice_moves(self, invoice_vals_list):
        invoice_type = self._get_invoice_move_types()[0]
        return (
            self.env["account.move"]
            .sudo()
            .with_context(default_move_type=invoice_type)
            .create(invoice_vals_list)
        )

    def _switch_negative_moves(self, moves, final):
        """Switch every negative-total move to a credit note/refund.

        The base implementation ignores ``final`` and switches
        unconditionally -- that is the live behavior for any concrete model
        that does not override this method (e.g. `purchase.order`).
        `sale.order` overrides it to gate on `final` instead; a future
        override that wants that gating must implement it itself rather than
        relying on a `super()` call to apply it.
        """
        moves_to_switch = moves.sudo().filtered(
            lambda m: m.currency_id.round(m.amount_total) < 0,
        )
        if moves_to_switch:
            _debug.lifecycle(
                "negative_moves_switched", orders=self, moves=moves_to_switch
            )
            moves_to_switch.action_switch_move_type()

    def _get_invoiceable_lines(self, final=False):
        self.check_singleton()
        return self.line_ids.filtered(
            lambda line: not line.display_type and line.qty_to_invoice,
        )

    def _prepare_down_payment_line_section_values(self):
        self.check_singleton()
        return {
            "order_id": self.id,
            "display_type": "line_section",
            "is_downpayment": True,
            "sequence": self._get_next_line_sequence(),
        }

    def _get_next_line_sequence(self):
        self.check_singleton()
        return max(self.line_ids.mapped("sequence"), default=9) + 1

    def _get_down_payment_section_line(self):
        self.check_singleton()
        section = self.line_ids.filtered(
            lambda line: line.display_type and line.is_downpayment,
        )[:1]
        return section or self._create_order_lines(
            [self._prepare_down_payment_line_section_values()],
        )

    def _create_down_payment_lines(self, vals_list):
        self.check_singleton()
        section = self._get_down_payment_section_line()
        return self._create_order_lines(
            [
                {**vals, "sequence": section.sequence + index}
                for index, vals in enumerate(vals_list, start=1)
            ],
        )

    def _create_order_lines(self, vals_list):
        self.check_singleton()
        lines = (
            self.env[self._get_line_model()]
            .with_context(no_log_for_new_lines=True)
            .create(vals_list)
        )
        self.with_context(bypass_locked_check=True).line_ids = [
            Command.link(line_id) for line_id in lines.ids
        ]
        _debug.lifecycle("order_lines_created", order=self, lines=lines)
        return lines

    def _prepare_invoice_line_commands(self, invoiceable_lines, sequence=10):
        commands = []
        for line in invoiceable_lines:
            commands.extend(
                Command.create(vals)
                for vals in line._prepare_aml_vals_list(sequence=sequence)
            )
            sequence += 1
        return commands, sequence

    def _group_invoice_vals(self, invoice_vals_list):
        grouping_keys = self._get_invoice_grouping_keys()

        def key(vals):
            return [vals.get(k) for k in grouping_keys]

        grouped = []
        for _keys, group in groupby(sorted(invoice_vals_list, key=key), key=key):
            origins = set()
            ref_vals = None
            for vals in group:
                if not ref_vals:
                    ref_vals = vals
                else:
                    ref_vals["invoice_line_ids"] += vals["invoice_line_ids"]
                origins.add(vals.get("invoice_origin"))
            ref_vals["invoice_origin"] = ", ".join(sorted(o for o in origins if o))
            grouped.append(ref_vals)
        _debug.pipeline(
            "invoice_vals_grouped",
            orders=self,
            before=len(invoice_vals_list),
            after=len(grouped),
        )
        return grouped

    def _post_create_invoices(self, moves):
        return moves

    def _get_nothing_to_invoice_error_message(self):
        return _("There is nothing to invoice for this order.")
