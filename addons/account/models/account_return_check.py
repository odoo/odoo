import ast

from markupsafe import Markup

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools.translate import LazyGettext

from .account_audit_account_status import STATUS_SELECTION
from .account_return_check_template import CHECK_TYPES

_debug = DebugLog(__name__)


class AccountReturnCheck(models.Model):
    _name = "account.return.check"
    _description = "Accounting Return Check"
    _order = "name, id"

    code = fields.Char(
        string="Check ID",
        required=True,
    )
    type = fields.Selection(
        selection=CHECK_TYPES,
        default="check",
        required=True,
    )
    template_id = fields.Many2one(
        comodel_name="account.return.check.template",
        ondelete="set null",
    )

    # Refreshed fields
    name = fields.Char(
        translate=True,
        required=True,
    )
    message = fields.Text(
        string="Description",
        translate=True,
    )
    state = fields.Char(
        string="Return State To Check For",
        default="new",
        required=True,
    )
    records_count = fields.Integer(readonly=True)
    records_name = fields.Char(
        compute="_compute_records_name",
        compute_sudo=True,
    )  # sudo is necessary because we're accessing ir.model
    records_model = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
    )
    action = fields.Json()
    result = fields.Selection(
        selection=STATUS_SELECTION,
        default="todo",
        required=True,
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        bypass_search_access=True,
    )

    # Return related
    return_id = fields.Many2one(
        comodel_name="account.return",
        string="Account Return",
        index=True,
        required=True,
        ondelete="cascade",
    )
    is_return_active = fields.Boolean(related="return_id.active")
    return_state = fields.Char(
        related="return_id.state",
        string="Return State",
    )
    return_name = fields.Char(
        related="return_id.name",
        string="Return Name",
    )
    date_deadline = fields.Date(
        related="return_id.date_deadline",
        string="Deadline",
    )

    # Editable fields
    refresh_result = fields.Boolean(default=True)
    approver_ids = fields.Many2many(
        comodel_name="res.users",
        string="Approved By",
        readonly=True,
        context={"active_test": False},
    )
    supervisor_id = fields.Many2one(
        comodel_name="res.users",
        string="Supervised By",
        readonly=True,
    )
    approver_supervisor_ids = fields.Many2many(
        comodel_name="res.users",
        string="Approvers and Supervisor",
        compute="_compute_approver_supervisor_ids",
        context={"active_test": False},
    )

    cycle = fields.Selection(related="template_id.cycle")

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        new_vals_list = [
            {
                key: self.env._(value) if isinstance(value, LazyGettext) else value  # pylint: disable=E8502
                for key, value in vals_dict.items()
            }
            for vals_dict in vals_list
        ]

        records = super().create(new_vals_list)

        # Left part is the check field name and right part is the template field name
        translatable_fields = [("name", "name"), ("message", "description")]
        all_langs = self.env["res.lang"].get_installed()
        for vals_dict, record in zip(vals_list, records, strict=False):
            for lang_code, _lang_name in all_langs:
                record = record.with_context(lang=lang_code)
                for check_field, template_field in translatable_fields:
                    if record.template_id:
                        record[check_field] = record.template_id[template_field]
                    elif (value := vals_dict.get(check_field)) and isinstance(
                        value, LazyGettext
                    ):
                        record[check_field] = value._translate(lang=lang_code)
        _debug.pipeline(
            "check_translations_applied",
            checks=records,
            langs=len(all_langs),
        )

        return records

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        for check in self:
            user = self.env.user
            if "supervisor_id" in vals and not user.has_groups(
                "account.group_account_manager"
            ):
                raise AccessError(
                    self.env._(
                        "Only an accounting administrator can set/unset a supervisor."
                    )
                )

            if "result" in vals:
                if check.return_state != "new":
                    raise UserError(
                        self.env._(
                            "You're only allowed to change the check state when the return hasn't been reviewed."
                        )
                    )
                if _debug.logic.enabled:
                    _debug.logic(
                        "check_result_changed",
                        check=check,
                        old=check.result,
                        new=vals.get("result"),
                        by_superuser=user.id == SUPERUSER_ID,
                    )

                if user.id != SUPERUSER_ID:
                    check.refresh_result = False

                    result_selection = dict(
                        self._fields["result"]._description_selection(self.env)
                    )
                    msg_body = Markup("""
                        <i>{check_name}</i> {check_updated}:
                        <ul class='mb-0 ps-4'>
                            <li>
                                <span class='o-mail-Message-trackingOld me-1 px-1 text-muted fw-bold'>{old_result}</span>
                                <i class='o-mail-Message-trackingSeparator fa-solid fa-right-long mx-1 text-600'/>
                                <span class='o-mail-Message-trackingNew me-1 fw-bold text-info'>{new_result}</span>
                                <span class='o-mail-Message-trackingField fst-italic text-muted'>({tracking_field})</span>
                            </li>
                        </ul>
                    """).format(
                        check_updated=self.env._("check updated"),
                        check_name=check.name,
                        old_result=result_selection[check.result],
                        new_result=result_selection[vals["result"]],
                        tracking_field=self.env._("Check State"),
                    )
                    check.return_id.message_post(body=msg_body)

                if vals["result"] in ("anomaly", "todo"):
                    check.approver_ids = False
                    # Writing on supervisor_id is only allowed for account admin, we don't want to raise
                    # an access error to a bookmaker if nothing is unset.
                    if check.supervisor_id:
                        check.supervisor_id = False
                elif vals["result"] == "reviewed":
                    check.approver_ids |= user
                    # Same as above
                    if check.supervisor_id:
                        check.supervisor_id = False
                elif vals["result"] == "supervised":
                    check.supervisor_id = user

        cleaned_vals = {
            key: self.env._(value) if isinstance(value, LazyGettext) else value  # pylint: disable=E8502
            for key, value in vals.items()
        }
        result = super().write(cleaned_vals)

        for check in self:
            if "type" in vals and check.type != vals["type"]:
                if not check.refresh_result:
                    check.action_invalidate_check()

            type = vals.get("type", check.type)
            if type != "file" and check.attachment_ids:
                _debug.logic("check_attachments_dropped", check=check, type=type)
                check.attachment_ids.unlink()

            if "attachment_ids" in vals and type == "file":
                check.refresh_result = not bool(check.attachment_ids)
                _debug.logic(
                    "file_check_refresh_toggled",
                    check=check,
                    attachments=check.attachment_ids,
                )

        return result

    @api.depends("records_model")
    @api.depends_context("lang")
    def _compute_records_name(self):
        for check in self:
            check.records_name = (
                check.records_model.name
                if check.records_model
                else self.env._("Missing")
            )

    @api.constrains("code")
    @_debug.perf.timed
    def _check_code(self):
        for record in self:
            if (
                len(
                    record.return_id.check_ids.filtered(
                        lambda check, record=record: check.code == record.code
                    )
                )
                > 1
            ):
                raise ValidationError(
                    _("You can only have a unique check code for each return.")
                )

    @api.depends("approver_ids", "supervisor_id")
    def _compute_approver_supervisor_ids(self):
        for check in self:
            check.approver_supervisor_ids = check.approver_ids | check.supervisor_id

    @_debug.perf.timed
    def _prepare_evaluation_context(self):
        def generate_journals_options():
            options = self.env.ref("account.trial_balance_report").get_options({})
            journals = options.get("journals", [])
            for journal in journals:
                if journal["model"] == "account.journal":
                    journal["selected"] = journal["type"] == "cash"
                elif journal["model"] == "account.journal.group":
                    journal["selected"] = False
            return journals

        company = self.return_id.company_id
        _debug.logic(
            "evaluation_context_built",
            check=self,
            tax_return=self.return_id,
            company=company,
        )
        return {
            "active_id": self.return_id.id,
            "active_ids": [self.return_id.id],
            "active_model": self.return_id._name,
            "return_start_date": fields.Date.to_string(self.return_id.date_from),
            "return_end_date": fields.Date.to_string(self.return_id.date_to),
            "return_last_month_start": fields.Date.to_string(
                fields.Date.start_of(self.return_id.date_to, "month")
            ),
            "ref": lambda xml_id: self.env.ref(xml_id).id,
            "internal_transfer_account_id": company.account_config_id.transfer_account_id.id,
            "currency_exhange_difference_account_ids": (
                company.account_config_id.income_currency_exchange_account_id.id,
                company.account_config_id.expense_currency_exchange_account_id.id,
            ),
            "company_currency_id": company.currency_id.id,
            "company_country_code": company.account_config_id.account_fiscal_country_id.code,
            "company_id": company.id,
            "cash_journal_options": generate_journals_options(),
        }

    def _parse_expression(self, value, context):
        """Evaluate a stringified expression (context, domain or params).

        :param value: the expression to evaluate
        :param context: the evaluation context exposing the allowed helpers
        :return: the evaluated expression
        """
        # literal_eval on the transformed tree: only the predefined helpers of the evaluation
        # context (e.g. ref()) are resolved, so no arbitrary code can be executed.
        try:
            tree = ast.parse(value, mode="eval")
            transformer = CheckActionExpressionTransformer(context)
            transformed_tree = transformer.visit(tree)
            return ast.literal_eval(transformed_tree)
        except (SyntaxError, TypeError, ValueError) as error:
            raise ValidationError(_("Invalid code")) from error

    @_debug.perf.timed
    def action_review(self):
        """Preprocess and return the action that must be triggered when clicking a check.

        :rtype: dict or None
        """
        # Actions coming from data carry their domain and context as strings, so they must be
        # evaluated against _prepare_evaluation_context before being returned.
        _debug.lifecycle("action_review", records=self)
        self.check_singleton()

        if (
            self.code
            == "_account_return_check_template_intercompany_account_reconciliation"
        ):
            other_companies = (
                self.env["res.company"]
                .search([])
                .filtered(lambda company: company not in self.return_id.company_ids)
            )
            other_companies_partners_ids = (
                other_companies.sudo().mapped("partner_id").ids
            )
            _debug.logic(
                "review_intercompany_partners",
                check=self,
                tax_return=self.return_id,
                other_companies=other_companies,
            )

            return {
                **self.action,
                "domain": [
                    ("company_id", "in", self.return_id.company_ids.ids),
                    ("date", ">=", self.return_id.date_from),
                    ("date", "<=", self.return_id.date_to),
                    ("partner_id", "in", other_companies_partners_ids),
                ],
            }

        if self.action:
            action = {**self.action}

            evaluation_context = self._prepare_evaluation_context()
            if _debug.logic.enabled:
                _debug.logic(
                    "review_action_string_expressions",
                    check=self,
                    keys=",".join(
                        key
                        for key in ("context", "domain", "params")
                        if isinstance(self.action.get(key), str)
                    ),
                )

            if "context" in self.action and isinstance(self.action["context"], str):
                action["context"] = self._parse_expression(
                    self.action["context"], evaluation_context
                )

            if "domain" in self.action and isinstance(self.action["domain"], str):
                action["domain"] = self._parse_expression(
                    self.action["domain"], evaluation_context
                )

            if "params" in self.action and isinstance(self.action["params"], str):
                action["params"] = self._parse_expression(
                    self.action["params"], evaluation_context
                )

            if self.template_id:
                if self.template_id.additional_action_domain:
                    action["domain"] = [
                        *(action.get("domain", []) or []),
                        *self._parse_expression(
                            self.template_id.additional_action_domain,
                            evaluation_context,
                        ),
                    ]

                if self.template_id.additional_action_context:
                    action["context"] = {
                        **(action.get("context", {}) or {}),
                        **self._parse_expression(
                            self.template_id.additional_action_context,
                            evaluation_context,
                        ),
                    }

                if (
                    self.template_id.additional_action_params
                    and action.get("type") == "ir.actions.client"
                ):
                    action["params"] = {
                        **(action.get("params", {}) or {}),
                        **self._parse_expression(
                            self.template_id.additional_action_params,
                            evaluation_context,
                        ),
                    }

            action["active_id"] = self.return_id.id
            action["active_model"] = self.return_id._name
            _debug.logic(
                "review_action_resolved",
                check=self,
                template=self.template_id,
                action_type=action.get("type"),
                has_domain=bool(action.get("domain")),
            )

            return action
        _debug.logic("review_skipped", check=self, reason="no_action")
        return None

    @_debug.perf.timed
    def action_view_document(self):
        _debug.lifecycle("action_view_document", records=self)
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.attachment_ids.id}",
            "target": "download",
        }

    @_debug.perf.timed
    def action_unlink_attachments(self):
        _debug.lifecycle("action_unlink_attachments", records=self)
        self.check_singleton()
        self.attachment_ids.unlink()
        self.refresh_result = True
        return True


class CheckActionExpressionTransformer(ast.NodeTransformer):
    def __init__(self, evaluation_context):
        self.evaluation_context = evaluation_context

    def visit_Name(self, node):
        if node.id in self.evaluation_context:
            return ast.Constant(self.evaluation_context[node.id])
        return node

    def prepare_call_args(self, ast_arguments):
        args = []
        args.extend(ast.literal_eval(self.visit(ast_arg)) for ast_arg in ast_arguments)
        return args

    def visit_Call(self, node):
        if (
            isinstance(node.func, ast.Name)
            and not node.keywords
            and callable(helper := self.evaluation_context.get(node.func.id))
        ):
            return ast.Constant(helper(*self.prepare_call_args(node.args)))
        # Preserve unsupported calls so literal_eval rejects them as invalid expressions.
        return node
