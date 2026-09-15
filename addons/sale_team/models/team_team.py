from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL
from odoo.tools.translate import LazyTranslate

from odoo.addons.team.models.team import TeamUsage

_lt = LazyTranslate(__name__)

DEFAULT_TEAM_XMLIDS = (
    "sale_team.team_sales_department",
    "sale_team.salesteam_website_sales",
    "sale_team.pos_sales_team",
)

_debug = DebugLog(__name__)


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
    invoiced = fields.Float(
        string="Invoiced This Month",
        compute="_compute_invoiced",
        readonly=True,
        groups="sale.group_sale_salesman,sale.group_sale_readonly",
        help="Invoice revenue for the current month. This is the amount the sales "
        "channel has invoiced this month. It is used to compute the progression ratio "
        "of the current and target revenue on the kanban view.",
    )
    invoiced_target = fields.Float(
        string="Invoicing Target",
        help="Revenue Target for the current month (untaxed total of paid invoices).",
    )
    sale_order_ids = fields.One2many(
        comodel_name="sale.order",
        inverse_name="team_id",
        string="Sales Orders",
    )
    sale_order_count = fields.Integer(
        string="# Sale Orders",
        compute="_compute_sale_order_count",
        groups="sale.group_sale_salesman,sale.group_sale_readonly",
    )

    @api.model
    def _get_usages(self):
        return super()._get_usages() | {
            "sale": TeamUsage(
                key="sale",
                flag="use_sale",
                label=_lt("Sales"),
                manager_group="sale.group_sale_manager",
                membership_multi_param="sale_team.membership_multi",
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
            _debug.logic("team_unlink_refused", teams=protected, reason="default_team")
            raise UserError(
                _('Cannot delete default team "%(name)s"', name=protected[0].name)
            )

    def _compute_dashboard_button_name(self):
        if self._is_in_sale_scope():
            self.dashboard_button_name = _("Sales Analysis")
        else:
            self.dashboard_button_name = _("Dashboard")

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_for_sales(self):
        SO_COUNT_TRIGGER = 5
        for team in self.sudo().filtered("use_sale"):
            if team.sale_order_count >= SO_COUNT_TRIGGER:
                _debug.logic(
                    "team_unlink_refused", team=team, orders=team.sale_order_count
                )
                raise UserError(
                    _(
                        "Team %(team_name)s has %(sale_order_count)s active sale orders. Consider cancelling them or archiving the team instead.",
                        team_name=team.name,
                        sale_order_count=team.sale_order_count,
                    ),
                )

    def _compute_invoiced(self):
        if self.ids:
            self.env["account.move"].flush_model(
                [
                    "team_id",
                    "amount_untaxed_signed",
                    "move_type",
                    "payment_state",
                    "state",
                    "date",
                ],
            )
            today = fields.Date.today()
            data_map = dict(
                self.env.execute_query(
                    SQL(
                        """
                        SELECT
                            move.team_id AS team_id,
                            SUM(move.amount_untaxed_signed) AS amount_untaxed_signed
                        FROM
                            account_move move
                        WHERE
                            move.move_type IN ('out_invoice', 'out_refund', 'out_receipt')
                            AND move.payment_state IN ('in_payment', 'paid', 'reversed')
                            AND move.state = 'posted'
                            AND move.team_id = ANY(%s)
                            AND move.date BETWEEN %s AND %s
                        GROUP BY
                            move.team_id
                        """,
                        list(self.ids),
                        fields.Date.to_string(today.replace(day=1)),
                        fields.Date.to_string(today),
                    ),
                ),
            )
        else:
            data_map = {}

        _debug.perf.count("team_invoiced", teams=len(self), rows=len(data_map))
        for team in self:
            team.invoiced = data_map.get(team._origin.id, 0.0)

    @api.depends("sale_order_ids.state")
    def _compute_sale_order_count(self):
        sale_order_data = self.env["sale.order"]._read_group(
            [
                ("team_id", "in", self.ids),
                ("state", "!=", "cancel"),
            ],
            ["team_id"],
            ["__count"],
        )
        data_map = {team.id: count for team, count in sale_order_data}
        _debug.perf.count("team_sale_order_count", teams=len(self), rows=len(data_map))
        for team in self:
            team.sale_order_count = data_map.get(team.id, 0)

    def action_primary_channel_button(self):
        if self._is_in_sale_scope():
            return self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                "sale_team.action_sale_report_so_salesteam"
            )
        return super().action_primary_channel_button()

    def update_invoiced_target(self, value):
        _debug.lifecycle("invoiced_target_set", teams=self, value=value)
        return self.write({"invoiced_target": round(float(value or 0))})

    def _is_in_sale_scope(self):
        return self.env.context.get("in_sales_app")
