from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_round

_debug = DebugLog(__name__)


class MrpProductionSplitMulti(models.TransientModel):
    _name = "mrp.production.split.multi"
    _description = "Wizard to Split Multiple Productions"

    production_ids = fields.One2many(
        comodel_name="mrp.production.split",
        inverse_name="production_split_multi_id",
        string="Productions To Split",
    )


class MrpProductionSplit(models.TransientModel):
    _name = "mrp.production.split"
    _description = "Wizard to Split a Production"

    production_split_multi_id = fields.Many2one(
        comodel_name="mrp.production.split.multi",
        string="Split Productions",
    )
    production_id = fields.Many2one(
        comodel_name="mrp.production",
        string="Manufacturing Order",
        readonly=True,
    )
    product_id = fields.Many2one(related="production_id.product_id")
    product_qty = fields.Float(related="production_id.product_qty")
    product_uom_id = fields.Many2one(related="production_id.product_uom_id")
    production_capacity = fields.Float(related="production_id.production_capacity")
    production_detailed_vals_ids = fields.One2many(
        comodel_name="mrp.production.split.line",
        inverse_name="mrp_production_split_id",
        string="Split Details",
        compute="_compute_production_detailed_vals_ids",
        store=True,
        readonly=False,
    )
    valid_details = fields.Boolean(
        string="Valid",
        compute="_compute_valid_details",
    )
    max_batch_size = fields.Float(
        digits="Product Unit",
        compute="_compute_max_batch_size",
        readonly=False,
    )
    num_splits = fields.Integer(
        string="# Splits",
        compute="_compute_num_splits",
        readonly=True,
    )

    MAX_SPLITS = 1000

    @api.depends("production_id")
    def _compute_max_batch_size(self):
        for wizard in self:
            bom_id = wizard.production_id.bom_id
            wizard.max_batch_size = (
                bom_id.batch_size if bom_id.enable_batch_size else wizard.product_qty
            )

    @api.depends("max_batch_size")
    def _compute_num_splits(self):
        self.num_splits = 0
        for wizard in self:
            if wizard.product_uom_id.compare(wizard.max_batch_size, 0) <= 0:
                continue
            num_splits = float_round(
                wizard.product_qty / wizard.max_batch_size,
                precision_digits=0,
                rounding_method="UP",
            )
            if num_splits > wizard.MAX_SPLITS:
                _debug.logic(
                    "split_refused",
                    reason="too_many_splits",
                    production=wizard.production_id.id,
                    splits=num_splits,
                    maximum=wizard.MAX_SPLITS,
                )
                raise ValidationError(
                    wizard.env._(
                        "A batch size of %(size)s would split this order into"
                        " %(count)s manufacturing orders, more than the"
                        " %(maximum)s allowed. Use a larger batch size.",
                        size=wizard.max_batch_size,
                        count=num_splits,
                        maximum=wizard.MAX_SPLITS,
                    )
                )
            wizard.num_splits = num_splits

    @api.depends("num_splits")
    def _compute_production_detailed_vals_ids(self):
        for wizard in self:
            commands = [Command.clear()]
            if wizard.num_splits <= 0 or not wizard.production_id:
                wizard.production_detailed_vals_ids = commands
                continue
            remaining_qty = wizard.product_qty
            for _split_index in range(wizard.num_splits):
                qty = min(wizard.max_batch_size, remaining_qty)
                commands.append(
                    Command.create(
                        {
                            "quantity": qty,
                            "user_id": wizard.production_id.user_id.id,
                            "date": wizard.production_id.date_start,
                        }
                    )
                )
                remaining_qty = wizard.product_uom_id.round(remaining_qty - qty)
            wizard.production_detailed_vals_ids = commands

    @api.depends("production_detailed_vals_ids")
    def _compute_valid_details(self):
        self.valid_details = False
        for wizard in self:
            if wizard.production_detailed_vals_ids:
                wizard.valid_details = (
                    wizard.product_uom_id.compare(
                        wizard.product_qty,
                        sum(wizard.production_detailed_vals_ids.mapped("quantity")),
                    )
                    == 0
                )

    def action_split(self):
        if not self.valid_details:
            _debug.logic(
                "split_refused",
                reason="quantities_do_not_sum",
                production=self.production_id.id,
            )
            raise UserError(
                _(
                    "The total quantity to split (%(total)s) does not match "
                    "the manufacturing order's quantity (%(product_qty)s).",
                    total=sum(self.production_detailed_vals_ids.mapped("quantity")),
                    product_qty=self.product_qty,
                )
            )
        _debug.pipeline(
            "split_wizard",
            production=self.production_id.id,
            parts=len(self.production_detailed_vals_ids),
        )
        productions = self.production_id._split_productions(
            {
                self.production_id: [
                    detail.quantity for detail in self.production_detailed_vals_ids
                ]
            }
        )
        for production, detail in zip(
            productions, self.production_detailed_vals_ids, strict=True
        ):
            production.user_id = detail.user_id
            production.date_start = detail.date
        if self.production_split_multi_id:
            saved_production_split_multi_id = self.production_split_multi_id.id
            self.production_split_multi_id.production_ids = [Command.unlink(self.id)]
            action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                "mrp.action_mrp_production_split_multi"
            )
            action["res_id"] = saved_production_split_multi_id
            return action
        return None

    def action_prepare_split(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.action_mrp_production_split"
        )
        action["res_id"] = self.id
        return action

    def action_return_to_list(self):
        self.production_detailed_vals_ids = [Command.clear()]
        self.max_batch_size = 0
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.action_mrp_production_split_multi"
        )
        action["res_id"] = self.production_split_multi_id.id
        return action


class MrpProductionSplitLine(models.TransientModel):
    _name = "mrp.production.split.line"
    _description = "Split Production Detail"

    mrp_production_split_id = fields.Many2one(
        comodel_name="mrp.production.split",
        string="Split Production",
        required=True,
        ondelete="cascade",
    )
    quantity = fields.Float(
        string="Quantity To Produce",
        digits="Product Unit",
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        domain=lambda self: [
            ("all_group_ids", "in", self.env.ref("mrp.group_mrp_user").id)
        ],
    )
    date = fields.Datetime(string="Schedule Date")
