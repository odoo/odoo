import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import parse_amount

_debug = DebugLog(__name__)


class AccountReconcileModelLine(models.Model):
    _name = "account.reconcile.model.line"
    _inherit = ["mixin.analytic"]
    _description = "Rules for the reconciliation model"
    _order = "sequence, id"
    _check_company_auto = True

    model_id = fields.Many2one(
        comodel_name="account.reconcile.model",
        index="btree_not_null",
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="model_id.company_id",
    )
    sequence = fields.Integer(
        default=10,
        required=True,
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        domain="[('account_type', '!=', 'off_balance')]",
        ondelete="cascade",
        check_company=True,
    )
    partner_id = fields.Many2one(comodel_name="res.partner")
    label = fields.Char(translate=True)
    amount_type = fields.Selection(
        selection=[
            ("fixed", "Fixed"),
            ("percentage", "Percentage of balance"),
            ("percentage_st_line", "Percentage of statement line"),
            ("regex", "From label"),
        ],
        default="percentage",
        required=True,
    )
    amount = fields.Float(
        string="Float Amount",
        compute="_compute_amount",
    )
    amount_string = fields.Char(
        string="Amount",
        default="100",
        required=True,
        help="""Value for the amount of the writeoff line
    * Percentage: Percentage of the balance. Either separator convention is accepted, so 12,5 and 12.5 both read as 12.5.
    * Fixed: The fixed value of the writeoff. The amount will count as a debit if it is negative, as a credit if it is positive.
    * From Label: There is no need for regex delimiter, only the regex is needed. For instance if you want to extract the amount from\nR:9672938 10/07 AX 9415126318 T:5L:NA BRT: 3358,07 C:\nYou could enter\nBRT: ([\\d,]+)
    If the label is "01870912 0009065 00115" and you need the amount in decimal
    format (e.g. 90.65), you can use a regex with capturing groups, for example:
        \\s+0*(\\d+?)(\\d{2})(?=\\s)
    In this case:
    • the first group captures the integer part
    • the second group captures the decimal part (last two digits)
    """,
    )
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        string="Taxes",
        ondelete="restrict",
        check_company=True,
    )

    @api.onchange("amount_type")
    def _onchange_amount_type(self):
        self.amount_string = ""
        if self.amount_type in ("percentage", "percentage_st_line"):
            self.amount_string = "100"
        elif self.amount_type == "regex":
            self.amount_string = r"([\d,]+)"

    @api.depends("amount_string", "amount_type")
    def _compute_amount(self):
        for record in self:
            record.amount = (
                0.0
                if record.amount_type == "regex"
                else parse_amount(record.amount_string) or 0.0
            )

    @api.constrains("amount_string", "amount_type")
    @_debug.perf.timed
    def _check_amount(self):
        for record in self:
            if record.amount_type == "regex":
                try:
                    re.compile(record.amount_string)
                except re.error as err:
                    _debug.logic(
                        "reco_model_line_rejected",
                        reco_model_line=record,
                        reason="bad_regex",
                    )
                    raise ValidationError(
                        self.env._(
                            "%(model)s: the amount regex is not valid.",
                            model=record.model_id.display_name,
                        )
                    ) from err
                continue

            if parse_amount(record.amount_string) is None:
                _debug.logic(
                    "reco_model_line_rejected",
                    reco_model_line=record,
                    reason="unparsable_amount",
                )
                raise ValidationError(
                    self.env._(
                        "%(model)s: %(value)s is not a valid amount. Write a finite "
                        "number, for example 100 or 12,5.",
                        model=record.model_id.display_name,
                        value=record.amount_string,
                    )
                )
            if not record.amount:
                _debug.logic(
                    "reco_model_line_rejected",
                    reco_model_line=record,
                    reason="zero_amount",
                )
                raise ValidationError(
                    self.env._(
                        "%(model)s: the amount of a %(kind)s line cannot be zero.",
                        model=record.model_id.display_name,
                        kind=dict(
                            record._fields["amount_type"]._description_selection(
                                self.env
                            )
                        )[record.amount_type],
                    )
                )


class AccountReconcileModel(models.Model):
    _name = "account.reconcile.model"
    _description = (
        "Preset to create journal entries during a invoices and payments matching"
    )
    _inherit = ["mixin.mail.thread"]
    _order = "sequence, id"
    _check_company_auto = True

    active = fields.Boolean(
        default=True,
        tracking=True,
    )
    name = fields.Char(
        translate=True,
        required=True,
        tracking=True,
    )
    sequence = fields.Integer(
        default=10,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
        required=True,
    )

    trigger = fields.Selection(
        selection=[("manual", "Manual"), ("auto_reconcile", "Automated")],
        default="manual",
        required=True,
        tracking=True,
        help="Validate the statement line automatically (reconciliation based on your rule).",
    )
    next_activity_type_id = fields.Many2one(
        comodel_name="mail.activity.type",
        string="Next Activity",
    )

    can_be_proposed = fields.Boolean(
        compute="_compute_can_be_proposed",
        store=True,
        copy=False,
    )
    mapped_partner_id = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_mapped_partner_id",
        store=True,
        copy=False,
    )
    match_journal_ids = fields.Many2many(
        comodel_name="account.journal",
        string="Journals",
        domain="[('type', 'in', ('bank', 'cash', 'credit'))]",
        check_company=True,
        tracking=True,
        help="The reconciliation model will only be available from the selected journals.",
    )
    match_amount = fields.Selection(
        selection=[
            ("lower", "Is lower than or equal to"),
            ("greater", "Is greater than or equal to"),
            ("between", "Is between"),
        ],
        string="Amount",
        tracking=True,
        help="The reconciliation model will only be applied when the amount being lower than, greater than or between specified amount(s).",
    )
    match_amount_min = fields.Float(
        string="Amount Min Parameter",
        tracking=True,
    )
    match_amount_max = fields.Float(
        string="Amount Max Parameter",
        tracking=True,
    )
    match_label = fields.Selection(
        selection=[
            ("contains", "Contains"),
            ("not_contains", "Not Contains"),
            ("match_regex", "Match Regex"),
        ],
        string="Label",
        tracking=True,
        help="""The reconciliation model will only be applied when either the statement line label, the transaction details or the note matches the following:
        * Contains: The statement line must contains this string (case insensitive). It is matched literally, so % and _ carry no special meaning.
        * Not Contains: Negation of "Contains".
        * Match Regex: Define your own regular expression.""",
    )
    match_label_param = fields.Char(
        string="Label Parameter",
        tracking=True,
    )
    match_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Partners",
        tracking=True,
        help="The reconciliation model will only be applied to the selected customers/vendors.",
    )

    line_ids = fields.One2many(
        comodel_name="account.reconcile.model.line",
        inverse_name="model_id",
        copy=True,
        tracking=True,
    )

    @api.constrains("match_label", "match_label_param")
    @_debug.perf.timed
    def _check_match_label_param(self):
        for record in self:
            if not record.match_label:
                continue
            if not record.match_label_param:
                _debug.logic(
                    "reco_model_rejected", reco_model=record, reason="empty_label_param"
                )
                raise ValidationError(
                    self.env._(
                        "%(model)s: the label filter is set to %(mode)s but no text "
                        "was given, so the model would never match anything.",
                        model=record.display_name,
                        mode=dict(
                            record._fields["match_label"]._description_selection(
                                self.env
                            )
                        )[record.match_label],
                    )
                )
            if record.match_label == "match_regex":
                try:
                    re.compile(record.match_label_param)
                except re.error as err:
                    _debug.logic(
                        "reco_model_rejected",
                        reco_model=record,
                        reason="bad_label_regex",
                    )
                    raise ValidationError(
                        self.env._(
                            "%(model)s: the label regex is not valid.",
                            model=record.display_name,
                        )
                    ) from err

    @api.depends(
        "mapped_partner_id",
        "match_label",
        "match_amount",
        "match_partner_ids",
        "match_journal_ids",
        "trigger",
    )
    def _compute_can_be_proposed(self):
        for model in self:
            model.can_be_proposed = not model.mapped_partner_id and (
                model.match_label
                or model.match_amount
                or model.match_partner_ids
                or model.match_journal_ids
                or model.trigger == "auto_reconcile"
            )

    @api.depends("match_label", "line_ids.partner_id", "line_ids.account_id")
    def _compute_mapped_partner_id(self):
        for model in self:
            is_partner_mapping = (
                model.match_label
                and len(model.line_ids) == 1
                and model.line_ids[0].partner_id
                and not model.line_ids[0].account_id
            )
            model.mapped_partner_id = (
                is_partner_mapping and model.line_ids[0].partner_id.id
            )

    @_debug.perf.timed
    def action_set_manual(self):
        _debug.lifecycle("action_set_manual", records=self)
        self.trigger = "manual"

    @_debug.perf.timed
    def action_set_auto_reconcile(self):
        _debug.lifecycle("action_set_auto_reconcile", records=self)
        self.trigger = "auto_reconcile"

    @_debug.perf.timed
    def action_reconcile_stat(self):
        _debug.lifecycle("action_reconcile_stat", records=self)
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "account.action_move_journal_line"
        )
        action.update(
            {
                "context": {},
                "domain": [("line_ids.reconcile_model_id", "=", self.id)],
                "help": """<p class="o_view_nocontent_empty_folder">{}</p>""".format(
                    self.env._("This reconciliation model has created no entry so far")
                ),
            }
        )
        return action

    def _get_copy_name(self, name):
        candidate = self.env._("%s (copy)", name)
        while self.search_count([("name", "=", candidate)], limit=1):
            candidate = self.env._("%s (copy)", candidate)
        return candidate

    def _get_copy_name_rounds(self, original, copied):
        rounds, name = 0, original
        while name != copied:
            longer = self.env._("%s (copy)", name)
            if len(longer) > len(copied):
                return 0
            name, rounds = longer, rounds + 1
        return rounds

    @_debug.perf.timed
    def copy_data(self, default=None):
        _debug.lifecycle("copy_data", records=self)
        default = dict(default or {})
        vals_list = super().copy_data(default)
        if default.get("name"):
            return vals_list
        for model, vals in zip(self, vals_list, strict=True):
            vals["name"] = self._get_copy_name(model.name)
        return vals_list

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        rounds = self._get_copy_name_rounds(self.name, new.name)
        if not rounds:
            return

        def rename(record, term):
            for _round in range(rounds):
                term = record.env._("%s (copy)", term)
            return term

        self._copy_translations_of_renamed_field(new, "name", rename)
