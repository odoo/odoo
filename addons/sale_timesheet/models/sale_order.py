# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    timesheet_count = fields.Float(string='Timesheet activities', compute='_compute_timesheet_count', groups="hr_timesheet.group_hr_timesheet_user", export_string_translation=False)
    timesheet_encode_uom_id = fields.Many2one('uom.uom', related='company_id.timesheet_encode_uom_id', export_string_translation=False)
    timesheet_total_duration = fields.Integer("Timesheet Total Duration", compute='_compute_timesheet_total_duration',
        help="Total recorded duration, expressed in the encoding UoM, and rounded to the unit", compute_sudo=True,
        groups="hr_timesheet.group_hr_timesheet_user", export_string_translation=False)
    show_hours_recorded_button = fields.Boolean(compute="_compute_show_hours_recorded_button", groups="hr_timesheet.group_hr_timesheet_user", export_string_translation=False)


    def _compute_timesheet_count(self):
        timesheets_per_so = {
            order.id: count
            for order, count in self.env['account.analytic.line']._read_group(
                [('order_id', 'in', self.ids), ('project_id', '!=', False)],
                ['order_id'],
                ['__count'],
            )
        }

        for order in self:
            order.timesheet_count = timesheets_per_so.get(order.id, 0)

    @api.depends('company_id.project_time_mode_id', 'company_id.timesheet_encode_uom_id', 'order_line.timesheet_ids')
    def _compute_timesheet_total_duration(self):
        group_data = self.env['account.analytic.line']._read_group([
            ('order_id', 'in', self.ids), ('project_id', '!=', False)
        ], ['order_id'], ['unit_amount:sum'])
        timesheet_unit_amount_dict = defaultdict(float)
        timesheet_unit_amount_dict.update({order.id: unit_amount for order, unit_amount in group_data})
        for sale_order in self:
            total_time = sale_order.company_id.project_time_mode_id._compute_quantity(
                timesheet_unit_amount_dict[sale_order.id],
                sale_order.timesheet_encode_uom_id,
                rounding_method='HALF-UP',
            )
            sale_order.timesheet_total_duration = round(total_time)

    def _compute_field_value(self, field):
        if field.name != 'invoice_status' or self.env.context.get('mail_activity_automation_skip'):
            return super()._compute_field_value(field)

        # Get SOs which their state is not equal to upselling and if at least a SOL has warning prepaid service upsell set to True and the warning has not already been displayed
        upsellable_orders = self.filtered(lambda so:
            so.state == 'sale'
            and so.invoice_status != 'upselling'
            and so.id
            and (so.user_id or so.partner_id.user_id)  # salesperson needed to assign upsell activity
        )
        super(SaleOrder, upsellable_orders.with_context(mail_activity_automation_skip=True))._compute_field_value(field)
        for order in upsellable_orders:
            upsellable_lines = order._get_prepaid_service_lines_to_upsell()
            if upsellable_lines:
                order._create_upsell_activity()
                # We want to display only one time the warning for each SOL
                upsellable_lines.write({'has_displayed_warning_upsell': True})
        super(SaleOrder, self - upsellable_orders)._compute_field_value(field)

    def _compute_show_hours_recorded_button(self):
        show_button_ids = self._get_order_with_valid_service_product()
        for order in self:
            order.show_hours_recorded_button = order.timesheet_count or order.project_count and order.id in show_button_ids

    def _get_order_with_valid_service_product(self):
        SaleOrderLine = self.env['sale.order.line']
        return SaleOrderLine._read_group(expression.AND([
            SaleOrderLine._domain_sale_line_service(),
            [
                ('order_id', 'in', self.ids),
                '|', ('product_id.service_type', 'not in', ['milestones', 'manual']),
                     ('product_id.invoice_policy', '!=', 'delivery'),
            ]
        ]), aggregates=['order_id:array_agg'])[0][0]

    def _get_prepaid_service_lines_to_upsell(self):
        """ Retrieve all sols which need to display an upsell activity warning in the SO

            These SOLs should contain a product which has:
                - type="service",
                - service_policy="ordered_prepaid",
        """
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        return self.order_line.filtered(lambda sol:
            sol.is_service
            and sol.invoice_status != "invoiced"
            and not sol.has_displayed_warning_upsell  # we don't want to display many times the warning each time we timesheet on the SOL
            and sol.product_id.service_policy == 'ordered_prepaid'
            and float_compare(
                sol.qty_delivered,
                sol.product_uom_qty * (sol.product_id.service_upsell_threshold or 1.0),
                precision_digits=precision
            ) > 0
        )

    def action_view_timesheet(self):
        self.ensure_one()
        if not self.order_line:
            return {'type': 'ir.actions.act_window_close'}

        action = self.env["ir.actions.actions"]._for_xml_id("sale_timesheet.timesheet_action_from_sales_order")
        default_sale_line = next((sale_line for sale_line in self.order_line if sale_line.is_service and sale_line.product_id.service_policy in ['ordered_prepaid', 'delivered_timesheet']), self.env['sale.order.line'])
        context = {
            'search_default_billable_timesheet': True,
            'default_is_so_line_edited': True,
            'default_so_line': default_sale_line.id,
        }  # erase default filters

        tasks = self.order_line.task_id._filtered_access('write')
        if tasks:
            context['default_task_id'] = tasks[0].id
        else:
            projects = self.order_line.project_id._filtered_access('write')
            if projects:
                context['default_project_id'] = projects[0].id
            elif self.project_ids:
                context['default_project_id'] = self.project_ids[0].id
        action.update({
            'context': context,
            'domain': [('so_line', 'in', self.order_line.ids), ('project_id', '!=', False)],
            'help': _("""
                <p class="o_view_nocontent_smiling_face">
                    No activities found. Let's start a new one!
                </p><p>
                    Track your working hours by projects every day and invoice this time to your customers.
                </p>
            """)
        })

        return action

    def _reset_has_displayed_warning_upsell_order_lines(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self.order_line:
            if line.has_displayed_warning_upsell and line.product_uom and float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 0:
                line.has_displayed_warning_upsell = False

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Link timesheets to the created invoices. Date interval is injected in the
        context in sale_make_invoice_advance_inv wizard.
        """
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        moves._link_timesheets_to_invoice(self.env.context.get("timesheet_start_date"), self.env.context.get("timesheet_end_date"))
        self._reset_has_displayed_warning_upsell_order_lines()
        return moves
