from typing import Literal, Self

from odoo import _, api, exceptions, fields, models
from odoo.models import ValuesType
from odoo.tools.safe_eval import safe_eval

DOMAIN_TEMPLATE = "[('store', '=', True), '|', ('model_id', '=', model_id), ('model_id', 'in', model_inherited_ids)%s]"


# Each module wanting to define gamification objectives creates
# ``gamification.goal.definition`` records specifying the computation
# mode (count, sum, python, manual) and the target model/field/domain.
class GamificationGoalDefinition(models.Model):
    """Template that defines how a goal is evaluated."""

    _name = "gamification.goal.definition"
    _description = "Gamification Goal Definition"

    name = fields.Char(
        string="Goal Definition",
        translate=True,
        required=True,
    )
    description = fields.Text(string="Goal Description")
    monetary = fields.Boolean(
        string="Monetary Value",
        default=False,
        help="The target and current value are defined in the company currency.",
    )
    suffix = fields.Char(
        translate=True,
        help="The unit of the target and current values",
    )
    full_suffix = fields.Char(
        compute="_compute_full_suffix",
        help="The currency and suffix field",
    )
    computation_mode = fields.Selection(
        selection=[
            ("manually", "Recorded manually"),
            ("count", "Automatic: number of records"),
            ("sum", "Automatic: sum on a field"),
            ("python", "Automatic: execute a specific Python code"),
        ],
        default="manually",
        required=True,
        help="Define how the goals will be computed. The result of the operation will be stored in the field 'Current'.",
    )
    display_mode = fields.Selection(
        selection=[
            ("progress", "Progressive (using numerical values)"),
            ("boolean", "Exclusive (done or not-done)"),
        ],
        string="Displayed as",
        default="progress",
        required=True,
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        ondelete="cascade",
    )
    model_inherited_ids = fields.Many2many(
        comodel_name="ir.model",
        related="model_id.inherited_model_ids",
    )
    field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Field to Sum",
        domain=DOMAIN_TEMPLATE % "",
    )
    field_date_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Date Field",
        domain=DOMAIN_TEMPLATE % ", ('ttype', 'in', ('date', 'datetime'))",
        help="The date to use for the time period evaluated",
    )
    domain = fields.Char(
        string="Filter Domain",
        default="[]",
        required=True,
        help="Domain for filtering records. General rule, not user depending,"
        " e.g. [('state', '=', 'done')]. The expression can contain"
        " reference to 'user' which is a browse record of the current"
        " user if not in batch mode.",
    )

    batch_mode = fields.Boolean(
        help="Evaluate the expression in batch instead of once for each user"
    )
    batch_distinctive_field = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Distinctive field for batch user",
        help="In batch mode, this indicates which field distinguishes one user from the other, e.g. user_id, partner_id...",
    )
    batch_user_expression = fields.Char(
        string="Evaluated expression for batch mode",
        help="The value to compare with the distinctive field. The expression can contain reference to 'user' which is a browse record of the current user, e.g. user.id, user.partner_id.id...",
    )
    compute_code = fields.Text(
        string="Python Code",
        help="Python code to be executed for each user. 'result' should contains the new current value. Evaluated user can be access through object.user_id.",
    )
    condition = fields.Selection(
        selection=[
            ("higher", "The higher the better"),
            ("lower", "The lower the better"),
        ],
        string="Goal Performance",
        default="higher",
        required=True,
        help="A goal is considered as completed when the current value is compared to the value to reach",
    )
    action_id = fields.Many2one(
        comodel_name="ir.actions.act_window",
        help="The action that will be called to update the goal value.",
    )
    res_id_field = fields.Char(
        string="ID Field of user",
        help="The field name on the user profile (res.users) containing the value for res_id for action.",
    )

    @api.depends("suffix", "monetary")
    @api.depends_context("allowed_company_ids")
    def _compute_full_suffix(self) -> None:
        for goal in self:
            items = []

            if goal.monetary:
                items.append(self.env.company.currency_id.symbol or "¤")
            if goal.suffix:
                items.append(goal.suffix)

            goal.full_suffix = " ".join(items)

    def _check_domain_validity(self) -> bool:
        # take admin as should always be present
        for definition in self:
            if definition.computation_mode not in ("count", "sum"):
                continue

            if not definition.model_id:
                # `self.env[False]` raised a bare KeyError from *outside* the
                # try below, so a count/sum definition saved without a model
                # produced a traceback instead of the message this method exists
                # to produce.
                raise exceptions.UserError(
                    _(
                        "The definition %(definition)s counts records, so it "
                        "needs a model to count them on.",
                        definition=definition.name,
                    )
                )
            try:
                Obj = self.env[definition.model_id.model]
                domain = safe_eval(definition.domain, {"user": self.env.user})
                # dummy search to make sure the domain is valid
                Obj.search_count(domain)  # noqa: E8507 - one probe per definition: each has its own model and domain
            except (KeyError, TypeError, ValueError, SyntaxError) as e:
                msg = e
                if isinstance(e, SyntaxError):
                    msg = e.msg + "\n" + e.text
                raise exceptions.UserError(
                    _(
                        "The domain for the definition %(definition)s seems incorrect, please check it.\n\n%(error_message)s",
                        definition=definition.name,
                        error_message=msg,
                    )
                ) from e
        return True

    def _check_model_validity(self) -> None:
        """Make sure the selected field and model are usable"""
        for definition in self:
            try:
                if not (definition.model_id and definition.field_id):
                    continue

                Model = self.env[definition.model_id.model]
                field = Model._fields.get(definition.field_id.name)
                if not (field and field.store):
                    raise exceptions.UserError(
                        _(
                            "The model configuration for the definition %(name)s seems incorrect, please check it.\n\n%(field_name)s not stored",
                            name=definition.name,
                            field_name=definition.field_id.name,
                        )
                    )
            except KeyError as e:
                raise exceptions.UserError(
                    _(
                        "The model configuration for the definition %(name)s seems incorrect, please check it.\n\n%(error)s not found",
                        name=definition.name,
                        error=e,
                    )
                ) from e

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        definitions = super().create(vals_list)
        definitions.filtered_domain(
            [
                ("computation_mode", "in", ["count", "sum"]),
            ]
        )._check_domain_validity()
        definitions.filtered_domain(
            [
                ("field_id", "!=", False),
            ]
        )._check_model_validity()
        return definitions

    def write(self, vals: ValuesType) -> Literal[True]:
        res = super().write(vals)
        if vals.get("domain") or vals.get("model_id") or vals.get("computation_mode"):
            self.filtered(
                lambda d: d.computation_mode in ("count", "sum")
            )._check_domain_validity()
        if vals.get("field_id") or vals.get("model_id") or vals.get("batch_mode"):
            self._check_model_validity()
        return res
