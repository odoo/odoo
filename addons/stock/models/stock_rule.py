import logging
from ast import literal_eval
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools import float_is_zero

from ..tools import debug_log as dbg
from .stock_procurement import Procurement, ProcurementException

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _name = "stock.rule"
    _description = "Stock Rule"
    _order = "sequence, id"
    _check_company_auto = True

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if "company_id" in fields and not res.get("company_id"):
            res["company_id"] = self.env.company.id
        return res

    Procurement = Procurement
    name = fields.Char(
        translate=True,
        required=True,
        help="This field will fill the packing origin and the name of its moves",
    )
    active = fields.Boolean(
        default=True,
        help="If unchecked, it will allow you to hide the rule without removing it.",
    )
    sequence = fields.Integer(default=20)
    action = fields.Selection(
        selection=[
            ("pull", "Pull From"),
            ("push", "Push To"),
            ("pull_push", "Pull & Push"),
        ],
        default="pull",
        index=True,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        domain="[('id', '=?', route_company_id)]",
    )
    location_dest_id = fields.Many2one(
        comodel_name="stock.location",
        string="Destination Location",
        index=True,
        required=True,
        check_company=True,
    )
    location_src_id = fields.Many2one(
        comodel_name="stock.location",
        string="Source Location",
        index=True,
        check_company=True,
    )
    location_dest_from_rule = fields.Boolean(
        string="Destination location origin from rule",
        default=False,
        help="When set to True the destination location of the stock.move will be the rule."
        "Otherwise, it takes it from the picking type.",
    )
    route_id = fields.Many2one(
        comodel_name="stock.route",
        index=True,
        required=True,
        ondelete="cascade",
    )
    route_company_id = fields.Many2one(
        related="route_id.company_id",
        string="Route Company",
    )
    procure_method = fields.Selection(
        selection=[
            ("make_to_stock", "Take From Stock"),
            ("make_to_order", "Trigger Another Rule"),
            ("mts_else_mto", "Take From Stock, if unavailable, Trigger Another Rule"),
        ],
        string="Supply Method",
        default="make_to_stock",
        required=True,
        help="Take From Stock: the products will be taken from the available stock of the source location.\n"
        "Trigger Another Rule: the system will try to find a stock rule to bring the products in the source location. The available stock will be ignored.\n"
        "Take From Stock, if Unavailable, Trigger Another Rule: the products will be taken from the available stock of the source location."
        "If there is no stock available, the system will try to find a  rule to bring the products in the source location.",
    )
    route_sequence = fields.Integer(
        related="route_id.sequence",
        string="Route Sequence",
        compute_sudo=True,
    )
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Operation Type",
        required=True,
        domain="[('code', 'in', picking_type_code_domain)] if picking_type_code_domain else []",
        check_company=True,
    )
    picking_type_code_domain = fields.Json(compute="_compute_picking_type_code_domain")
    delay = fields.Integer(
        string="Lead Time",
        default=0,
        help="The expected date of the created transfer will be computed based on this lead time.",
    )
    partner_address_id = fields.Many2one(
        comodel_name="res.partner",
        check_company=True,
        help="Address where goods should be delivered. Optional.",
    )
    propagate_cancel = fields.Boolean(
        string="Cancel Next Move",
        default=False,
        help="When ticked, if the move created by this rule is cancelled, the next move will be cancelled too.",
    )
    propagate_carrier = fields.Boolean(
        string="Propagation of carrier",
        default=False,
        help="When ticked, carrier of shipment will be propagated.",
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        index=True,
        check_company=True,
    )
    auto = fields.Selection(
        selection=[
            ("manual", "Manual Operation"),
            ("transparent", "Automatic No Step Added"),
        ],
        string="Automatic Move",
        default="manual",
        required=True,
        help="The 'Manual Operation' value will create a stock move after the current one. "
        "With 'Automatic No Step Added', the location is replaced in the original move.",
    )
    rule_message = fields.Html(compute="_compute_rule_message")
    push_domain = fields.Char(string="Push Applicability")

    @api.constrains("push_domain")
    def _check_push_domain(self):
        Move = self.env["stock.move"]
        for rule in self:
            if not rule.push_domain:
                continue
            try:
                Domain(literal_eval(rule.push_domain)).check(Move)
            except Exception as error:
                raise ValidationError(
                    _(
                        "The push applicability of rule %(rule)s is not a valid "
                        "domain on stock moves: %(error)s",
                        rule=rule.display_name,
                        error=error,
                    ),
                ) from error

    @api.constrains("company_id", "route_id")
    def _check_company_consistency(self):
        for rule in self:
            route = rule.route_id
            if route.company_id and rule.company_id != route.company_id:
                raise ValidationError(
                    _(
                        "Rule %(rule)s belongs to %(rule_company)s while the route belongs to %(route_company)s.",
                        rule=rule.display_name,
                        rule_company=rule.company_id.display_name,
                        route_company=route.company_id.display_name,
                    )
                )

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for rule, vals in zip(self, vals_list, strict=True):
                vals["name"] = _("%s (copy)", rule.name)
        return vals_list

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    @api.onchange("picking_type_id")
    def _onchange_picking_type_id(self):
        self.location_src_id = self.picking_type_id.default_location_src_id.id
        self.location_dest_id = self.picking_type_id.default_location_dest_id.id

    @api.onchange("route_id", "company_id")
    def _onchange_route(self):
        if self.route_id.company_id:
            self.company_id = self.route_id.company_id
        if self.picking_type_id.company_id != self.company_id:
            self.picking_type_id = False

    def _get_message_labels(self):
        source = (self.location_src_id and self.location_src_id.display_name) or _(
            "Source Location"
        )
        destination = (
            self.location_dest_id and self.location_dest_id.display_name
        ) or _("Destination Location")
        direct_destination = (
            self.picking_type_id
            and self.picking_type_id.default_location_dest_id != self.location_dest_id
            and self.picking_type_id.default_location_dest_id.display_name
        )
        operation = (self.picking_type_id and self.picking_type_id.name) or _(
            "Operation Type"
        )
        return source, destination, direct_destination, operation

    def _get_action_messages(self):
        message_dict = {}
        source, destination, direct_destination, operation = self._get_message_labels()
        if self.action in ("push", "pull", "pull_push"):
            suffix = ""
            if (
                self.action in ("pull", "pull_push")
                and direct_destination
                and not self.location_dest_from_rule
            ):
                suffix = _(
                    "<br>The products will be moved towards <b>%(destination)s</b>, <br/> as specified from <b>%(operation)s</b> destination.",
                    destination=direct_destination,
                    operation=operation,
                )
            if self.procure_method == "make_to_order" and self.location_src_id:
                suffix += _(
                    "<br>A need is created in <b>%s</b> and a rule will be triggered to fulfill it.",
                    source,
                )
            if self.procure_method == "mts_else_mto" and self.location_src_id:
                suffix += _(
                    "<br>If the products are not available in <b>%s</b>, a rule will be triggered to bring the missing quantity in this location.",
                    source,
                )
            message_dict = {
                "pull": _(
                    "When products are needed in <b>%(destination)s</b>, <br> <b>%(operation)s</b> are created from <b>%(source_location)s</b> to fulfill the need. %(suffix)s",
                    destination=destination,
                    operation=operation,
                    source_location=source,
                    suffix=suffix,
                ),
                "push": _(
                    "When products arrive in <b>%(source_location)s</b>, <br> <b>%(operation)s</b> are created to send them to <b>%(destination)s</b>.",
                    source_location=source,
                    operation=operation,
                    destination=destination,
                ),
            }
        return message_dict

    @api.depends(
        "action",
        "location_dest_id",
        "location_src_id",
        "picking_type_id",
        "procure_method",
        "location_dest_from_rule",
    )
    def _compute_rule_message(self):
        for rule in self:
            message_dict = rule._get_action_messages()
            if rule.action == "pull_push":
                rule.rule_message = (
                    message_dict["pull"] + "<br/><br/>" + message_dict["push"]
                )
            else:
                rule.rule_message = message_dict.get(rule.action) or ""

    @api.depends("action")
    def _compute_picking_type_code_domain(self):
        for rule in self:
            rule.picking_type_code_domain = rule._get_domain_picking_type_code()

    def _get_domain_picking_type_code(self):
        return []

    def _get_push_new_date(self, move):
        return fields.Datetime.to_string(move.date + relativedelta(days=self.delay))

    @dbg.timed
    def _run_push(self, moves):
        self.check_singleton()
        dbg.pipeline.debug(
            "[rule:%s] _run_push auto=%s on %s -> %s",
            self.id,
            self.auto,
            dbg.rec(moves),
            self.location_dest_id.id,
        )
        if self.auto == "transparent":
            return {move.id: self._run_push_in_place(move) for move in moves}
        return self._run_push_copy(moves)

    def _run_push_in_place(self, move):
        old_dest_location = move.location_dest_id
        move.write(
            {
                "date": self._get_push_new_date(move),
                "location_dest_id": self.location_dest_id.id,
            },
        )
        if move.move_line_ids:
            move.move_line_ids.location_dest_id = (
                move.location_dest_id._get_putaway_strategy(move.product_id)
                or move.location_dest_id
            )
        if self.location_dest_id != old_dest_location:
            dbg.pipeline.debug(
                "[move:%s] pushed in place %s -> %s, applying next push",
                move.id,
                old_dest_location.id,
                self.location_dest_id.id,
            )
            return move._push_apply()[:1]
        return self.env["stock.move"]

    def _run_push_copy(self, moves):
        vals_list = []
        for move in moves:
            vals = move.sudo().copy_data(
                self._prepare_push_move_copy_values(
                    move,
                    self._get_push_new_date(move),
                ),
            )[0]
            if not move.location_dest_id.is_reservation_bypass_required():
                vals["move_orig_ids"] = [Command.link(move.id)]
            vals_list.append(vals)
        new_moves = self.env["stock.move"].sudo().create(vals_list)
        dbg.pipeline.debug(
            "[rule:%s] push copies %s -> %s",
            self.id,
            dbg.rec(moves),
            dbg.rec(new_moves),
        )
        self._update_pushed_moves(new_moves)
        return dict(zip(moves.ids, new_moves, strict=True))

    def _update_pushed_moves(self, new_moves):
        moves_by_final_location = defaultdict(list)
        for move in new_moves.filtered(lambda move: move._is_excluded_from_push()):
            moves_by_final_location[move.location_final_id.id].append(move.id)
        for location_id, move_ids in moves_by_final_location.items():
            new_moves.browse(move_ids).location_dest_id = location_id
        unreserved = new_moves.filtered(
            lambda move: move._is_reservation_bypass_required(),
        )
        if moves_by_final_location or unreserved:
            dbg.logic.debug(
                "_update_pushed_moves: final locations %s, bypass -> mts %s",
                dict(moves_by_final_location),
                dbg.rec(unreserved),
            )
        if unreserved:
            unreserved.procure_method = "make_to_stock"

    def _prepare_push_move_copy_values(self, move_to_copy, new_date):
        company_id = self.company_id.id
        copied_quantity = move_to_copy.quantity
        final_location_id = False
        location_dest_id = self.location_dest_id.id
        if (
            move_to_copy.location_final_id
            and not move_to_copy.location_dest_id._is_child_of(
                move_to_copy.location_final_id
            )
        ):
            final_location_id = move_to_copy.location_final_id.id
        if (
            move_to_copy.location_final_id
            and move_to_copy.location_final_id._is_child_of(self.location_dest_id)
        ):
            location_dest_id = move_to_copy.location_final_id.id
        if move_to_copy.product_uom_id.compare(move_to_copy.product_uom_qty, 0) < 0:
            copied_quantity = move_to_copy.product_uom_qty
        if not company_id:
            rule_sudo = self.sudo()
            company_id = (
                rule_sudo.warehouse_id.company_id.id
                or rule_sudo.picking_type_id.warehouse_id.company_id.id
            )
        return {
            "product_uom_qty": copied_quantity,
            "origin": move_to_copy.origin or move_to_copy.picking_id.name or "/",
            "location_id": move_to_copy.location_dest_id.id,
            "location_dest_id": location_dest_id,
            "location_final_id": final_location_id,
            "rule_id": self.id,
            "date": new_date,
            "date_deadline": move_to_copy.date_deadline,
            "company_id": company_id,
            "picking_id": False,
            "picking_type_id": self.picking_type_id.id,
            "propagate_cancel": self.propagate_cancel,
            "warehouse_id": self.warehouse_id.id
            or move_to_copy.location_dest_id.warehouse_id.id,
            "procure_method": "make_to_order",
        }

    @dbg.timed
    @api.model
    def _run_pull(self, procurements):
        dbg.pipeline.debug("_run_pull: %d procurements", len(procurements))
        moves_values_by_company = defaultdict(list)

        source_errors = [
            (
                procurement,
                _(
                    "No source location defined on stock rule: %s!",
                    rule.display_name,
                ),
            )
            for procurement, rule in procurements
            if not rule.location_src_id
        ]
        if source_errors:
            raise ProcurementException(source_errors)

        procurements = sorted(
            procurements,
            key=lambda proc: (
                proc[0].product_uom_id.compare(proc[0].product_qty, 0.0) > 0
            ),
        )
        for procurement, rule in procurements:
            procure_method = rule.procure_method
            if rule.procure_method == "mts_else_mto":
                procure_method = "make_to_stock"

            move_values = rule._prepare_stock_move_vals(procurement)
            move_values["procure_method"] = procure_method
            dbg.pipeline.debug(
                "[procurement:%s] rule %s -> move vals product=%s qty=%s %s->%s %s",
                procurement.origin,
                rule.id,
                procurement.product_id.id,
                procurement.product_qty,
                move_values.get("location_id"),
                move_values.get("location_dest_id"),
                procure_method,
            )
            moves_values_by_company[procurement.company_id.id].append(move_values)
        self._propagate_transit_partner(procurements)

        for company_id, moves_values in moves_values_by_company.items():
            moves = (
                self.env["stock.move"]
                .sudo()
                .with_company(company_id)
                .create(moves_values)
            )
            dbg.pipeline.debug(
                "_run_pull: company %s created %s -> _action_confirm",
                company_id,
                dbg.rec(moves),
            )
            moves._action_confirm()
        return True

    @api.model
    def _get_action_runners(self):
        return {"pull": "_run_pull"}

    def _get_fields_custom_move(self):
        return []

    def _prepare_stock_move_vals(self, procurement):
        product_uom_id = procurement.product_uom_id
        values = procurement.values
        date_scheduled = fields.Datetime.to_string(
            fields.Datetime.from_string(values["date_planned"])
            - relativedelta(days=self.delay)
        )
        date_deadline = (
            values.get("date_deadline")
            and (
                fields.Datetime.to_datetime(values["date_deadline"])
                - relativedelta(days=self.delay)
            )
        ) or False
        dest_moves = values.get("move_dest_ids") or self.env["stock.move"]
        move_dest_ids = [Command.link(move_id) for move_id in dest_moves.ids]
        partner = self._get_move_partner(procurement, dest_moves)

        if product_uom_id.compare(procurement.product_qty, 0.0) < 0:
            values = dict(values, to_refund=True)

        move_values = {
            "company_id": self.company_id.id
            or self.location_src_id.company_id.id
            or self.location_dest_id.company_id.id
            or procurement.company_id.id,
            "product_id": procurement.product_id.id,
            "product_uom_id": product_uom_id.id,
            "product_uom_qty": procurement.product_qty,
            "partner_id": partner,
            "location_id": self.location_src_id.id,
            "location_final_id": procurement.location_id.id,
            "move_dest_ids": move_dest_ids,
            "rule_id": self.id,
            "reference_ids": [
                Command.set(
                    (values.get("reference_ids") or self.env["stock.reference"]).ids
                ),
            ],
            "procure_method": self.procure_method,
            "origin": procurement.origin,
            "picking_type_id": self.picking_type_id.id,
            "route_ids": [
                Command.set((values.get("route_ids") or self.env["stock.route"]).ids),
            ],
            "never_product_template_attribute_value_ids": values.get(
                "never_product_template_attribute_value_ids"
            ),
            "warehouse_id": self.warehouse_id.id,
            "date": date_scheduled,
            "date_deadline": date_deadline,
            "propagate_cancel": self.propagate_cancel,
            "priority": values.get("priority", "0"),
            "orderpoint_id": values.get("orderpoint_id") and values["orderpoint_id"].id,
        }
        if self.location_dest_from_rule:
            move_values["location_dest_id"] = self.location_dest_id.id
        decided = set(move_values)
        for field in self._get_fields_custom_move():
            if field in values and field not in decided:
                move_values[field] = values.get(field)
        return move_values

    def _get_move_partner(self, procurement, dest_moves):
        partner = self.partner_address_id.id or procurement.values.get(
            "partner_id",
            False,
        )
        if (
            partner
            or not dest_moves
            or procurement.location_id
            != procurement.company_id.internal_transit_location_id
        ):
            return partner
        partners = dest_moves.location_dest_id.warehouse_id.partner_id
        return partners.id if len(partners) == 1 else partner

    @api.model
    def _propagate_transit_partner(self, procurements):
        moves_by_partner = defaultdict(lambda: self.env["stock.move"])
        for procurement, rule in procurements:
            dest_moves = procurement.values.get("move_dest_ids")
            if not dest_moves or (
                procurement.location_id
                != procurement.company_id.internal_transit_location_id
            ):
                continue
            partner = (
                rule.location_src_id.warehouse_id.partner_id
                or rule.company_id.partner_id
            )
            moves_by_partner[partner.id] |= dest_moves
        for partner_id, moves in moves_by_partner.items():
            dbg.logic.debug(
                "_propagate_transit_partner: %s <- partner %s",
                dbg.rec(moves),
                partner_id,
            )
            moves.partner_id = partner_id

    def _get_lead_days(self, product, **values):
        _ = self.env._
        delays = defaultdict(float)
        delay_description = []
        bypass_delay_description = self.env.context.get("bypass_delay_description")
        delaying_rules = self.filtered(
            lambda r: r.action in ["pull", "pull_push"] and r.delay
        )
        if delaying_rules:
            delays["total_delay"] += sum(delaying_rules.mapped("delay"))
            if not bypass_delay_description:
                delay_description = [
                    (_("Delay on %s", rule.name), _("+ %d day(s)", rule.delay))
                    for rule in delaying_rules
                ]
        global_horizon_days = self.env["stock.warehouse.orderpoint"]._get_horizon_days(
            self.company_id.sorted("id")[:1],
        )
        if global_horizon_days:
            delays["horizon_time"] += global_horizon_days
            if not bypass_delay_description:
                delay_description.append(
                    (_("Time Horizon"), _("+ %d day(s)", global_horizon_days))
                )
        dbg.logic.debug(
            "_get_lead_days product=%s rules=%s -> %s",
            product.id,
            dbg.rec(self),
            dict(delays),
        )
        return delays, delay_description

    @api.model
    def _prepare_procurement_defaults(self, procurement):
        return {
            "company_id": procurement.location_id.company_id,
            "priority": "0",
            **procurement.values,
            "date_planned": procurement.values.get("date_planned")
            or fields.Datetime.now(),
        }

    @api.model
    def _is_nothing_to_procure(self, procurement):
        return procurement.product_id.type != "consu" or float_is_zero(
            procurement.product_qty,
            precision_rounding=procurement.product_uom_id.rounding,
        )

    @dbg.timed
    @api.model
    def run(self, procurements, raise_user_error=True):
        dbg.pipeline.debug(
            "stock.rule.run: %d procurements %s",
            len(procurements),
            dbg.lazy(
                lambda: [
                    (p.origin, p.product_id.id, p.product_qty, p.location_id.id)
                    for p in procurements[:8]
                ]
            ),
        )

        def prepare_procurement_error(procurement_errors):
            if raise_user_error:
                _dummy, errors = zip(*procurement_errors, strict=False)
                return UserError("\n".join(errors))
            return ProcurementException(procurement_errors)

        actions_to_run = defaultdict(list)
        procurement_errors = []
        valid_procurements = [
            procurement._replace(
                values=self._prepare_procurement_defaults(procurement),
            )
            for procurement in procurements
            if not self._is_nothing_to_procure(procurement)
        ]
        rules = self._get_rules_batch(valid_procurements)
        dbg.logic.debug(
            "run: %d of %d procurements need a rule, rules found %s",
            len(valid_procurements),
            len(procurements),
            [rule.id if rule else None for rule in rules],
        )
        for procurement, rule in zip(valid_procurements, rules, strict=True):
            if not rule:
                error = _(
                    'No rule has been found to replenish "%(product)s" in "%(location)s".\nVerify the routes configuration on the product.',
                    product=procurement.product_id.display_name,
                    location=procurement.location_id.display_name,
                )
                procurement_errors.append((procurement, error))
            else:
                action = "pull" if rule.action == "pull_push" else rule.action
                actions_to_run[action].append((procurement, rule))

        if procurement_errors:
            raise prepare_procurement_error(procurement_errors)

        runners = self._get_action_runners()
        for action, action_procurements in actions_to_run.items():
            run_action = (
                getattr(self, runners[action], None) if action in runners else None
            )
            if run_action is None:
                _logger.error(
                    "The method _run_%s doesn't exist on the procurement rules", action
                )
                for procurement, rule in action_procurements:
                    procurement_errors.append(
                        (
                            procurement,
                            _(
                                'The rule "%(rule)s" cannot replenish "%(product)s" in'
                                ' "%(location)s": nothing in this database implements'
                                " its “%(action)s” action. Install the module providing"
                                " it, or change the routes on the product.",
                                rule=rule.display_name,
                                product=procurement.product_id.display_name,
                                location=procurement.location_id.display_name,
                                action=action,
                            ),
                        )
                    )
                continue
            dbg.pipeline.debug(
                "run -> %s for %d procurements",
                runners[action],
                len(action_procurements),
            )
            try:
                run_action(action_procurements)
            except ProcurementException as e:
                dbg.logic.debug(
                    "run: %s raised %d procurement errors",
                    runners[action],
                    len(e.procurement_exceptions),
                )
                procurement_errors += e.procurement_exceptions

        if procurement_errors:
            raise prepare_procurement_error(procurement_errors)
        return True
