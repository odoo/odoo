from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import LazyTranslate

from odoo.addons.team.models.team import TeamUsage

_lt = LazyTranslate(__name__)

DEFAULT_TEAM_XMLIDS = (
    "sales_team.team_sales_department",
    "sales_team.salesteam_website_sales",
    "sales_team.pos_sales_team",
)


class TeamTeam(models.Model):
    _inherit = "team.team"

    use_sale = fields.Boolean(
        string="Sales",
        help="The team sells: it owns quotations, orders and invoices, and appears in the Sales app.",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )
    dashboard_button_name = fields.Char(
        string="Dashboard Button",
        compute="_compute_dashboard_button_name",
    )

    @api.model
    def _get_usages(self):
        return super()._get_usages() | {
            "sale": TeamUsage(
                key="sale",
                flag="use_sale",
                label=_lt("Sales"),
                manager_group="sales_team.group_sale_manager",
                membership_multi_param="sales_team.membership_multi",
            ),
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default(self):
        default_teams = self.browse()
        for xmlid in DEFAULT_TEAM_XMLIDS:
            default_teams |= (
                self.env.ref(xmlid, raise_if_not_found=False) or self.browse()
            )

        if protected := (self & default_teams):
            raise UserError(
                _('Cannot delete default team "%(name)s"', name=protected[0].name)
            )

    def _compute_dashboard_button_name(self):
        self.dashboard_button_name = _("Dashboard")
