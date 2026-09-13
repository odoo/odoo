import typing

from odoo import _, api, fields, models
from odoo.api import ValuesType

if typing.TYPE_CHECKING:
    from .mail_activity_plan_template import MailActivityPlanTemplate
    from odoo.addons.base.models.ir_model import IrModel
    from odoo.addons.base.models.res_company import ResCompany


class MailActivityPlan(models.Model):
    _name = "mail.activity.plan"
    _description = "Activity Plan"
    _order = "id DESC"

    name = fields.Char(required=True)
    company_id: ResCompany = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    template_ids: MailActivityPlanTemplate = fields.One2many(
        comodel_name="mail.activity.plan.template",
        inverse_name="plan_id",
        string="Activities",
        copy=True,
    )
    active = fields.Boolean(default=True)
    res_model_id: IrModel = fields.Many2one(
        comodel_name="ir.model",
        string="Applies to",
        compute="_compute_res_model_id",
        precompute=True,
        compute_sudo=True,
        store=True,
        readonly=False,
        required=True,
        ondelete="cascade",
    )
    res_model = fields.Selection(
        selection=lambda self: self.env["mail.activity"]._selection_activity_models(),
        string="Model",
        required=True,
        help="Specify a model if the activity should be specific to a model"
        " and not available when managing activities for other models.",
    )
    steps_count = fields.Count(count_of="template_ids")
    has_user_on_demand = fields.Boolean(
        string="Has on demand responsible",
        compute="_compute_has_user_on_demand",
    )

    @api.depends("res_model")
    def _compute_res_model_id(self) -> None:
        for plan in self:
            if plan.res_model:
                plan.res_model_id = self.env["ir.model"]._get_id(plan.res_model)
            else:
                plan.res_model_id = False

    @api.constrains("res_model")
    def _check_res_model_compatibility_with_templates(self) -> None:
        self.template_ids._check_activity_type_res_model()

    @api.depends("template_ids.responsible_type")
    def _compute_has_user_on_demand(self) -> None:
        self.has_user_on_demand = False
        for plan in self.filtered("template_ids"):
            plan.has_user_on_demand = any(
                template.responsible_type == "on_demand"
                for template in plan.template_ids
            )

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for plan, vals in zip(self, vals_list, strict=False):
                vals["name"] = _("%s (copy)", plan.name)
        return vals_list
