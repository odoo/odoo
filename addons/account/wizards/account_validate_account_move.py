from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ValidateAccountMove(models.TransientModel):
    _name = "validate.account.move"
    _description = "Validate Account Move"

    move_ids = fields.Many2many(comodel_name="account.move")
    force_post = fields.Boolean(
        string="Force",
        help="Entries in the future are set to be auto-posted by default. Check this checkbox to post them now.",
    )
    display_force_post = fields.Boolean(compute="_compute_display_force_post")
    force_hash = fields.Boolean()
    display_force_hash = fields.Boolean(compute="_compute_display_force_hash")
    is_entries = fields.Boolean(compute="_compute_is_entries")
    abnormal_date_partner_ids = fields.One2many(
        comodel_name="res.partner",
        compute="_compute_abnormal_date_partner_ids",
    )
    ignore_abnormal_date = fields.Boolean()
    abnormal_amount_partner_ids = fields.One2many(
        comodel_name="res.partner",
        compute="_compute_abnormal_amount_partner_ids",
    )
    ignore_abnormal_amount = fields.Boolean()

    @api.depends("move_ids")
    def _compute_display_force_post(self):
        today = fields.Date.context_today(self)
        for wizard in self:
            wizard.display_force_post = bool(
                wizard.move_ids.filtered(
                    lambda m: (m.date or m.invoice_date or today) > today
                )
            )

    @api.depends("move_ids")
    def _compute_display_force_hash(self):
        for wizard in self:
            wizard.display_force_hash = bool(
                wizard.move_ids.filtered("restrict_mode_hash_table")
            )

    @api.depends("move_ids")
    def _compute_is_entries(self):
        for wizard in self:
            wizard.is_entries = any(
                move_type == "entry"
                for move_type in wizard.move_ids.mapped("move_type")
            )

    @api.depends("move_ids")
    def _compute_abnormal_date_partner_ids(self):
        for wizard in self:
            wizard.abnormal_date_partner_ids = wizard.move_ids.filtered(
                "abnormal_date_warning"
            ).partner_id

    @api.depends("move_ids")
    def _compute_abnormal_amount_partner_ids(self):
        for wizard in self:
            wizard.abnormal_amount_partner_ids = wizard.move_ids.filtered(
                "abnormal_amount_warning"
            ).partner_id

    @api.model
    @_debug.perf.timed
    def default_get(self, fields_list):
        _debug.lifecycle("default_get", records=self)
        result = super().default_get(fields_list)
        if "move_ids" in fields_list and not result.get("move_ids"):
            if self.env.context.get("active_model") == "account.move":
                domain = [
                    ("id", "in", self.env.context.get("active_ids", [])),
                    ("state", "=", "draft"),
                    ("line_ids", "!=", False),
                ]
            elif self.env.context.get("active_model") == "account.journal":
                domain = [
                    ("journal_id", "=", self.env.context.get("active_id")),
                    ("state", "=", "draft"),
                    ("line_ids", "!=", False),
                ]
            else:
                _debug.logic(
                    "validate_defaults_rejected",
                    reason="unsupported_active_model",
                    active_model=self.env.context.get("active_model"),
                )
                raise UserError(_("Missing 'active_model' in context."))

            moves = self.env["account.move"].search(domain)
            _debug.logic(
                "draft_moves_to_post_found",
                active_model=self.env.context.get("active_model"),
                move=moves,
            )
            if not moves:
                raise UserError(
                    _("There are no journal items in the draft state to post.")
                )
            result["move_ids"] = [Command.set(moves.ids)]

        return result

    @_debug.perf.timed
    def action_post_moves(self):
        _debug.lifecycle("action_post_moves", records=self)
        if self.ignore_abnormal_amount:
            self.abnormal_amount_partner_ids.ignore_abnormal_invoice_amount = True
        if self.ignore_abnormal_date:
            self.abnormal_date_partner_ids.ignore_abnormal_invoice_date = True
        if self.force_post:
            self.move_ids.auto_post = "no"
        excluded_moves = self.env["account.move"]
        if self.force_hash:
            moves_to_post = self.move_ids
        else:
            moves_to_post = self.move_ids.filtered(
                lambda m: not m.restrict_mode_hash_table
            )
            excluded_moves = self.move_ids - moves_to_post
        _debug.logic(
            "post_scope_decided",
            move=moves_to_post,
            excluded=excluded_moves,
            force_hash=self.force_hash,
            force_post=self.force_post,
        )
        moves_to_post._post_check_business_rules()
        moves_to_post._post(not self.force_post)

        if autopost_bills_wizard := moves_to_post._show_autopost_bills_wizard():
            return autopost_bills_wizard
        if excluded_moves:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "message": _(
                        "The following entries were not posted because they are hash-restricted: %(moves)s. Check the 'Force' option to post them anyway.",
                        moves=", ".join(excluded_moves.mapped("name")),
                    ),
                    "sticky": True,
                },
            }
        return {"type": "ir.actions.act_window_close"}
