from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools.translate import _

from odoo.addons.account.tools.display_types import NON_ACCOUNTABLE_DISPLAY_TYPES

_debug = DebugLog(__name__)


class AccountMoveReversal(models.TransientModel):
    _name = "account.move.reversal"
    _description = "Account Move Reversal"
    _check_company_auto = True

    move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="account_move_reversal_move",
        column1="reversal_id",
        column2="move_id",
        domain=[("state", "=", "posted")],
    )
    new_move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="account_move_reversal_new_move",
        column1="reversal_id",
        column2="new_move_id",
    )
    date = fields.Date(
        string="Reversal date",
        default=fields.Date.context_today,
    )
    reason = fields.Char(string="Reason displayed on Credit Note")
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_journal_id",
        store=True,
        readonly=False,
        required=True,
        check_company=True,
        help="If empty, uses the journal of the journal entry to be reversed.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
        required=True,
    )
    available_journal_ids = fields.Many2many(
        comodel_name="account.journal",
        compute="_compute_available_journal_ids",
    )
    country_code = fields.Char(related="company_id.country_id.code")

    residual = fields.Monetary(compute="_compute_from_moves")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_from_moves",
    )
    move_type = fields.Char(compute="_compute_from_moves")

    @api.depends("move_ids")
    def _compute_journal_id(self):
        for record in self:
            if record.journal_id:
                record.journal_id = record.journal_id
            else:
                journals = record.move_ids.journal_id.filtered(lambda x: x.active)
                record.journal_id = journals[0] if journals else None

    @api.depends("move_ids")
    def _compute_available_journal_ids(self):
        Journal = self.env["account.journal"]
        journals = Journal.search(Journal._check_company_domain(self.company_id))
        for record in self:
            allowed = journals.filtered_domain(
                Journal._check_company_domain(record.company_id)
            )
            if record.move_ids:
                types = record.move_ids.journal_id.mapped("type")
                allowed = allowed.filtered(
                    lambda journal, types=types: journal.type in types
                )
            record.available_journal_ids = allowed

    @api.constrains("journal_id", "move_ids")
    @_debug.perf.timed
    def _check_journal_type(self):
        for record in self:
            if record.journal_id.type not in record.move_ids.journal_id.mapped("type"):
                raise ValidationError(
                    _("Journal should be the same type as the reversed entry.")
                )

    @api.model
    @_debug.perf.timed
    def default_get(self, fields_list):
        _debug.lifecycle("default_get", records=self)
        res = super().default_get(fields_list)
        move_ids = (
            self.env["account.move"].browse(self.env.context.get("active_ids"))
            if self.env.context.get("active_model") == "account.move"
            else self.env["account.move"]
        )

        if len(move_ids.company_id) > 1:
            _debug.logic(
                "reversal_defaults_rejected", move=move_ids, reason="multi_company"
            )
            raise UserError(
                _("All selected moves for reversal must belong to the same company.")
            )

        if any(move.state != "posted" for move in move_ids):
            _debug.logic(
                "reversal_defaults_rejected", move=move_ids, reason="not_posted"
            )
            raise UserError(_("To reverse a journal entry, it has to be posted first."))
        if "company_id" in fields_list:
            res["company_id"] = move_ids.company_id.id or self.env.company.id
        if "move_ids" in fields_list:
            res["move_ids"] = [Command.set(move_ids.ids)]
        return res

    @api.depends("move_ids")
    @_debug.perf.timed
    def _compute_from_moves(self):
        for record in self:
            move_ids = record.move_ids._origin
            record.residual = (len(move_ids) == 1 and move_ids.amount_residual) or 0
            record.currency_id = (
                len(move_ids.currency_id) == 1 and move_ids.currency_id
            ) or False
            record.move_type = (
                move_ids.move_type
                if len(move_ids) == 1
                else (
                    (
                        any(
                            move.move_type in ("in_invoice", "out_invoice")
                            for move in move_ids
                        )
                        and "some_invoice"
                    )
                    or False
                )
            )

    @_debug.perf.timed
    def _prepare_default_reversal(self, move):
        reverse_date = self.date
        mixed_payment_term = (
            move.invoice_payment_term_id.id
            if move.invoice_payment_term_id.early_pay_discount_computation == "mixed"
            else None
        )
        lang = move.partner_id.lang or self.env.lang
        return {
            "ref": self.with_context(lang=lang).env._(
                "Reversal of: %(move_name)s, %(reason)s",
                move_name=move.name,
                reason=self.reason,
            )
            if self.reason
            else self.with_context(lang=lang).env._("Reversal of: %s", move.name),
            "date": reverse_date,
            "invoice_date_due": reverse_date,
            "invoice_date": (
                move.is_invoice(include_receipts=True) and (self.date or move.date)
            )
            or False,
            "journal_id": self.journal_id.id,
            "invoice_payment_term_id": mixed_payment_term,
            "invoice_user_id": move.invoice_user_id.id,
            "auto_post": "at_date"
            if reverse_date > fields.Date.context_today(self)
            else "no",
            "invoice_origin": move.invoice_origin,
        }

    def _get_reversal_batches(self, moves, default_values_list, is_modify):
        batches = [
            [self.env["account.move"], [], True],
            [self.env["account.move"], [], False],
        ]
        for move, default_vals in zip(moves, default_values_list, strict=True):
            is_auto_post = default_vals.get("auto_post") != "no"
            is_cancel_needed = not is_auto_post and (
                is_modify or self.move_type == "entry"
            )
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)
        return batches

    def _get_modified_reversal_moves(self, batch_moves):
        moves_vals_list = []
        for move in batch_moves.with_context(include_business_fields=True):
            data = move.copy_data(self._modify_default_reverse_values(move))[0]
            data["line_ids"] = [
                line
                for line in data["line_ids"]
                if line[2]["display_type"]
                in ("product", *NON_ACCOUNTABLE_DISPLAY_TYPES)
            ]
            moves_vals_list.append(data)
        return self.env["account.move"].create(moves_vals_list)

    def _get_reversal_redirect_action(self, moves_to_redirect):
        action = {
            "name": _("Reverse Moves"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
        }
        _debug.logic(
            "reversal_redirect_chosen",
            move=moves_to_redirect,
            single_form=len(moves_to_redirect) == 1,
        )
        if len(moves_to_redirect) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": moves_to_redirect.id,
                    "context": {"default_move_type": moves_to_redirect.move_type},
                }
            )
        else:
            action.update(
                {
                    "view_mode": "list,form",
                    "domain": [("id", "in", moves_to_redirect.ids)],
                }
            )
            if len(set(moves_to_redirect.mapped("move_type"))) == 1:
                action["context"] = {
                    "default_move_type": moves_to_redirect.mapped("move_type").pop()
                }
        return action

    @_debug.perf.timed
    def reverse_moves(self, is_modify=False):
        self.check_singleton()
        moves = self.move_ids

        default_values_list = [
            {
                "partner_bank_id": False,
                **self._prepare_default_reversal(move),
            }
            for move in moves
        ]
        batches = self._get_reversal_batches(moves, default_values_list, is_modify)
        _debug.pipeline(
            "reverse_moves",
            reversal=self,
            moves=moves,
            modify=is_modify,
            batches_count=len(batches),
        )

        moves_to_redirect = self.env["account.move"]
        for batch_moves, batch_default_values, is_cancel_needed in batches:
            _debug.logic(
                "batch",
                reversal=self,
                batch_moves=batch_moves,
                cancel=is_cancel_needed,
            )
            new_moves = batch_moves._reverse_moves(
                batch_default_values, cancel=is_cancel_needed
            )
            new_moves._compute_partner_bank_id()
            batch_moves._message_log_batch(
                bodies={
                    move.id: move.env._(
                        "This entry has been %s",
                        reverse._get_html_link(title=move.env._("reversed")),
                    )
                    for move, reverse in zip(batch_moves, new_moves, strict=True)
                }
            )

            if is_modify:
                new_moves = self._get_modified_reversal_moves(batch_moves)
                new_moves._compute_partner_bank_id()

            moves_to_redirect |= new_moves

        self.new_move_ids = moves_to_redirect
        return self._get_reversal_redirect_action(moves_to_redirect)

    def refund_moves(self):
        return self.reverse_moves(is_modify=False)

    def modify_moves(self):
        return self.reverse_moves(is_modify=True)

    def _modify_default_reverse_values(self, origin_move):
        data = {
            "date": self.date,
            "invoice_origin": origin_move.invoice_origin,
        }

        if (
            origin_move.move_type.startswith("in_")
            and origin_move.message_main_attachment_id
        ):
            new_main_attachment_id = origin_move.message_main_attachment_id.copy(
                {"res_id": False}
            ).id
            data.update(
                {
                    "message_main_attachment_id": new_main_attachment_id,
                    "attachment_ids": [Command.link(new_main_attachment_id)],
                }
            )

        return data
