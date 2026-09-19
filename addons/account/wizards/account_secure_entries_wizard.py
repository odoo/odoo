from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountSecureEntriesWizard(models.TransientModel):
    _name = "account.secure.entries.wizard"
    _description = "Secure Journal Entries"

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
        required=True,
    )
    country_code = fields.Char(
        related="company_id.account_config_id.account_fiscal_country_id.code"
    )
    hash_date = fields.Date(
        string="Hash All Entries",
        compute="_compute_hash_date",
        store=True,
        readonly=False,
        required=True,
        help="The selected Date",
    )
    chains_to_hash_with_gaps = fields.Json(compute="_compute_data")
    max_hash_date = fields.Date(
        compute="_compute_max_hash_date",
        help="Highest Date such that all posted journal entries prior to (including) the date are secured. Only journal entries after the hard lock date are considered.",
    )
    unreconciled_bank_statement_line_ids = fields.Many2many(
        comodel_name="account.bank.statement.line",
        compute="_compute_data",
        help="All unreconciled bank statement lines before the selected date.",
    )
    not_hashable_unlocked_move_ids = fields.Many2many(
        comodel_name="account.move",
        compute="_compute_data",
        help="All unhashable moves before the selected date that are not protected by the Hard Lock Date",
    )
    move_to_hash_ids = fields.Many2many(
        comodel_name="account.move",
        compute="_compute_data",
        help="All moves that will be hashed",
    )
    warnings = fields.Json(compute="_compute_warnings")

    @api.depends("max_hash_date")
    def _compute_hash_date(self):
        for wizard in self:
            if not wizard.hash_date:
                wizard.hash_date = wizard.max_hash_date or fields.Date.context_today(
                    self
                )

    @api.depends("company_id", "company_id.account_config_id.user_hard_lock_date")
    @_debug.perf.timed
    def _compute_max_hash_date(self):
        today = fields.Date.context_today(self)
        for wizard in self:
            chains_to_hash = wizard.with_context(
                chain_info_warnings=False
            )._get_chains_to_hash(wizard.company_id, today)
            moves = self.env["account.move"].concat(
                *[chain["moves"] for chain in chains_to_hash],
                *[chain["not_hashable_unlocked_moves"] for chain in chains_to_hash],
            )
            if moves:
                min_date = self.env.execute_query(
                    self.env["account.move"]
                    ._search([("id", "in", moves.ids)])
                    .select("MIN(date)")
                )[0][0]
                wizard.max_hash_date = min_date - timedelta(days=1)
            else:
                wizard.max_hash_date = False

    @_debug.perf.timed
    def _get_chains_to_hash(self, company_id, hash_date):
        self.check_singleton()
        res = []
        for *__, chain_moves in (
            self.env["account.move"]
            .sudo()
            ._read_group(
                domain=self._get_domain_unhashed_moves_in_hashed_period(
                    company_id, hash_date, [("state", "=", "posted")]
                ),
                groupby=["journal_id", "sequence_prefix"],
                aggregates=["id:recordset"],
            )
        ):
            chain_info = chain_moves._get_chain_info(force_hash=True)
            if not chain_info:
                continue

            last_move_hashed = chain_info["last_move_hashed"]
            if last_move_hashed:
                not_hashable_unlocked_moves = chain_info["remaining_moves"].filtered(
                    lambda move, last_move_hashed=last_move_hashed: (
                        not move.inalterable_hash
                        and move.sequence_number < last_move_hashed.sequence_number
                        and move.date > company_id.account_config_id.user_hard_lock_date
                    )
                )
            else:
                not_hashable_unlocked_moves = self.env["account.move"]
            chain_info["not_hashable_unlocked_moves"] = not_hashable_unlocked_moves
            res.append(chain_info)
        _debug.pipeline(
            "chains_to_hash_collected",
            secure=self,
            company=company_id,
            hash_date=hash_date,
            chains=len(res),
        )
        return res

    @api.depends(
        "company_id", "company_id.account_config_id.user_hard_lock_date", "hash_date"
    )
    @_debug.perf.timed
    def _compute_data(self):
        for wizard in self:
            unreconciled_bank_statement_line_ids = []
            chains_to_hash = []
            if wizard.hash_date:
                for chain_info in wizard._get_chains_to_hash(
                    wizard.company_id, wizard.hash_date
                ):
                    if "unreconciled" in chain_info["warnings"]:
                        unreconciled_bank_statement_line_ids.extend(
                            chain_info["moves"]
                            .statement_line_ids.filtered(lambda l: not l.is_reconciled)
                            .ids
                        )
                    else:
                        chains_to_hash.append(chain_info)
            wizard.unreconciled_bank_statement_line_ids = [
                Command.set(unreconciled_bank_statement_line_ids)
            ]
            wizard.chains_to_hash_with_gaps = [
                {
                    "first_move_id": chain["moves"][0].id,
                    "last_move_id": chain["moves"][-1].id,
                }
                for chain in chains_to_hash
                if "gap" in chain["warnings"]
            ]

            not_hashable_unlocked_moves = []
            move_to_hash_ids = []
            for chain in chains_to_hash:
                not_hashable_unlocked_moves.extend(
                    chain["not_hashable_unlocked_moves"].ids
                )
                move_to_hash_ids.extend(chain["moves"].ids)
            wizard.not_hashable_unlocked_move_ids = [
                Command.set(not_hashable_unlocked_moves)
            ]
            wizard.move_to_hash_ids = [Command.set(move_to_hash_ids)]
            _debug.pipeline(
                "secure_data_computed",
                secure=wizard,
                chains=len(chains_to_hash),
                unreconciled_st_lines=len(unreconciled_bank_statement_line_ids),
                moves_to_hash=len(move_to_hash_ids),
                not_hashable=len(not_hashable_unlocked_moves),
            )

    def _get_unreconciled_statement_warning(self):
        ignored_sequence_prefixes = list(
            set(
                self.unreconciled_bank_statement_line_ids.move_id.mapped(
                    "sequence_prefix"
                )
            )
        )
        return {
            "message": _(
                "There are still unreconciled bank statement lines before the selected date. "
                "The entries from journal prefixes containing them will not be secured: %(prefix_info)s",
                prefix_info=ignored_sequence_prefixes,
            ),
            "level": "danger",
            "action_text": _("Review Statements"),
            "action": self.company_id._get_unreconciled_statement_lines_redirect_action(
                self.unreconciled_bank_statement_line_ids
            ),
        }

    @_debug.perf.timed
    def _get_sequence_gap_warning(self):
        or_domains = []
        for chain in self.chains_to_hash_with_gaps:
            first_move = self.env["account.move"].browse(chain["first_move_id"])
            last_move = self.env["account.move"].browse(chain["last_move_id"])
            or_domains.append(
                [
                    *self.env["account.move"]._check_company_domain(self.company_id),
                    ("journal_id", "=", last_move.journal_id.id),
                    ("sequence_prefix", "=", last_move.sequence_prefix),
                    ("sequence_number", "<=", last_move.sequence_number),
                    ("sequence_number", ">=", first_move.sequence_number),
                ]
            )
        _debug.pipeline(
            "sequence_gap_domains_built",
            secure=self,
            chains=len(or_domains),
        )
        domain = Domain.OR(or_domains)
        return {
            "message": _(
                "Securing these entries will create at least one gap in the sequence."
            ),
            "action_text": _("Review Entries"),
            "action": {
                **self.env["account.journal"]._show_sequence_holes(list(domain)),
                "views": [
                    [
                        self.env.ref("account.view_move_tree_multi_edit").id,
                        "list",
                    ],
                    [self.env.ref("account.view_move_form").id, "form"],
                ],
            },
        }

    @_debug.perf.timed
    def _get_warnings(self):
        self.check_singleton()
        warnings = {}
        _debug.logic(
            "secure_warnings_scope",
            secure=self,
            hash_date=self.hash_date,
            skipped=not self.hash_date,
        )
        if not self.hash_date:
            return warnings

        if self.unreconciled_bank_statement_line_ids:
            warnings["account_unreconciled_bank_statement_line_ids"] = (
                self._get_unreconciled_statement_warning()
            )

        if self.env["account.move"].search_count(
            self._get_domain_draft_moves_in_hashed_period(), limit=1
        ):
            warnings["account_unhashed_draft_entries"] = {
                "message": _("There are still draft entries before the selected date."),
                "action_text": _("Review Entries"),
                "action": self.action_show_draft_moves_in_hashed_period(),
            }

        not_hashable_unlocked_moves = self.not_hashable_unlocked_move_ids
        if not_hashable_unlocked_moves:
            warnings["account_not_hashable_unlocked_moves"] = {
                "message": _(
                    "There are entries that cannot be hashed. They can be protected by the Hard Lock Date."
                ),
                "action_text": _("Review Entries"),
                "action": self.action_show_moves(not_hashable_unlocked_moves),
            }

        if self.chains_to_hash_with_gaps:
            warnings["account_sequence_gap"] = self._get_sequence_gap_warning()

        moves_to_hash_after_selected_date = self.move_to_hash_ids.filtered(
            lambda move: move.date > self.hash_date
        )
        if moves_to_hash_after_selected_date:
            warnings["account_move_to_secure_after_selected_date"] = {
                "message": _(
                    "Securing these entries will also secure entries after the selected date."
                ),
                "action_text": _("Review Entries"),
                "action": self.action_show_moves(moves_to_hash_after_selected_date),
            }
        if _debug.logic.enabled:
            _debug.logic(
                "secure_warnings_built",
                secure=self,
                warnings=sorted(warnings),
            )
        return warnings

    @api.depends(
        "company_id",
        "chains_to_hash_with_gaps",
        "hash_date",
        "not_hashable_unlocked_move_ids",
        "max_hash_date",
        "unreconciled_bank_statement_line_ids",
    )
    def _compute_warnings(self):
        for wizard in self:
            wizard.warnings = wizard._get_warnings()

    @api.model
    def _get_domain_unhashed_moves_in_hashed_period(
        self, company_id, hash_date, domain=False
    ):
        if not (company_id and hash_date):
            return Domain.FALSE
        return Domain.AND(
            [
                [
                    ("date", "<=", fields.Date.to_string(hash_date)),
                    ("company_id", "child_of", company_id.id),
                    ("inalterable_hash", "=", False),
                ],
                domain or Domain.TRUE,
            ]
        )

    def _get_domain_draft_moves_in_hashed_period(self):
        self.check_singleton()
        return self._get_domain_unhashed_moves_in_hashed_period(
            self.company_id, self.hash_date, [("state", "=", "draft")]
        )

    @_debug.perf.timed
    def action_show_moves(self, moves):
        _debug.lifecycle("action_show_moves", records=self)
        self.check_singleton()
        return {
            "view_mode": "list",
            "name": _("Journal Entries"),
            "res_model": "account.move",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", moves.ids)],
            "search_view_id": [
                self.env.ref("account.view_account_move_filter").id,
                "search",
            ],
            "views": [
                [self.env.ref("account.view_move_tree_multi_edit").id, "list"],
                [self.env.ref("account.view_move_form").id, "form"],
            ],
        }

    @_debug.perf.timed
    def action_show_draft_moves_in_hashed_period(self):
        _debug.lifecycle("action_show_draft_moves_in_hashed_period", records=self)
        self.check_singleton()
        return {
            "view_mode": "list",
            "name": _("Draft Entries"),
            "res_model": "account.move",
            "type": "ir.actions.act_window",
            "domain": list(self._get_domain_draft_moves_in_hashed_period()),
            "search_view_id": [
                self.env.ref("account.view_account_move_filter").id,
                "search",
            ],
            "views": [
                [self.env.ref("account.view_move_tree_multi_edit").id, "list"],
                [self.env.ref("account.view_move_form").id, "form"],
            ],
        }

    @_debug.perf.timed
    def action_secure_entries(self):
        _debug.lifecycle("action_secure_entries", records=self)
        self.check_singleton()

        if not self.hash_date:
            raise UserError(
                _("Set a date. The moves will be secured up to including this date.")
            )

        if not self.move_to_hash_ids:
            _debug.logic("nothing_hash_up", secure=self, hash_date=self.hash_date)
            return

        _debug.pipeline(
            "hashing_up",
            secure=self,
            move_to_hash_ids=self.move_to_hash_ids,
            hash_date=self.hash_date,
        )
        self.move_to_hash_ids._hash_moves(force_hash=True, raise_if_gap=False)
