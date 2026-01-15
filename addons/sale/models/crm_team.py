# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    invoiced = fields.Float(
        compute='_compute_invoiced',
        string='Invoiced This Month', readonly=True,
        help="Invoice revenue for the current month. This is the amount the sales "
                "channel has invoiced this month. It is used to compute the progression ratio "
                "of the current and target revenue on the kanban view.")
    invoiced_target = fields.Float(
        string='Invoicing Target',
        help="Revenue Target for the current month (untaxed total of paid invoices).")
    sale_order_count = fields.Integer(compute='_compute_sale_order_count', string='# Sale Orders')

    def _compute_invoiced(self):
        if self.ids:
            today = fields.Date.today()
            data_map = dict(self.env.execute_query(SQL(
                ''' SELECT
                        move.team_id AS team_id,
                        SUM(move.amount_untaxed_signed) AS amount_untaxed_signed
                    FROM account_move move
                    WHERE move.move_type IN ('out_invoice', 'out_refund', 'out_receipt')
                    AND move.payment_state IN ('in_payment', 'paid', 'reversed')
                    AND move.state = 'posted'
                    AND move.team_id IN %s
                    AND move.date BETWEEN %s AND %s
                    GROUP BY move.team_id
                ''',
                tuple(self.ids),
                fields.Date.to_string(today.replace(day=1)),
                fields.Date.to_string(today),
            )))
        else:
            data_map = {}

        for team in self:
            team.invoiced = data_map.get(team._origin.id, 0.0)

    def _compute_sale_order_count(self):
        sale_order_data = self.env['sale.order']._read_group([
            ('team_id', 'in', self.ids),
            ('state', '!=', 'cancel'),
        ], ['team_id'], ['__count'])
        data_map = {team.id: count for team, count in sale_order_data}
        for team in self:
            team.sale_order_count = data_map.get(team.id, 0)

    def _in_sale_scope(self):
        return self.env.context.get('in_sales_app')

    def _compute_dashboard_button_name(self):
        super(CrmTeam,self)._compute_dashboard_button_name()
        if self._in_sale_scope():
            self.dashboard_button_name = _("Sales Analysis")

    def action_primary_channel_button(self):
        if self._in_sale_scope():
            return self.env["ir.actions.actions"]._for_xml_id("sale.action_order_report_so_salesteam")
        return super().action_primary_channel_button()

    def update_invoiced_target(self, value):
        return self.write({'invoiced_target': round(float(value or 0))})

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_for_sales(self):
        """ If more than 5 active SOs, we consider this team to be actively used.
        5 is some random guess based on "user testing", aka more than testing
        CRM feature and less than use it in real life use cases. """
        SO_COUNT_TRIGGER = 5
        for team in self:
            if team.sale_order_count >= SO_COUNT_TRIGGER:
                raise UserError(
                    _('Team %(team_name)s has %(sale_order_count)s active sale orders. Consider cancelling them or archiving the team instead.',
                      team_name=team.name,
                      sale_order_count=team.sale_order_count
                      ))
