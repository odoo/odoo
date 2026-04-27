from odoo import models, _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def _update_revenues_from_so(self, order):
        for opportunity in self:
            log_body = ''

            if ((opportunity.expected_revenue or 0) < order.non_recurring_total
                and order.currency_id == opportunity.company_id.currency_id
            ):
                opportunity.expected_revenue = order.non_recurring_total
                log_body = _("Expected revenue has been updated based on the linked Sales orders.")

            if ((opportunity.recurring_revenue_monthly or 0) < order.recurring_monthly
                and order.currency_id == opportunity.company_id.currency_id
            ):
                if not opportunity.recurring_plan:
                    opportunity.recurring_plan = opportunity.env.ref('crm.crm_recurring_plan_monthly', raise_if_not_found=False)
                opportunity.recurring_revenue = order.recurring_monthly * (opportunity.recurring_plan.number_of_months or 1)
                if self.env.user.has_group("crm.group_use_recurring_revenues"):
                    if log_body:
                        log_body = _("Recurring revenue and Expected revenue have been updated based on the linked Sales Orders.")
                    else:
                        log_body = _("Recurring revenue has been updated based on the linked Sales Orders.")
            if log_body:
                opportunity._track_set_log_message(log_body)

    def _track_filter_for_display(self, tracking_values):
        if not self.env.user.has_group("crm.group_use_recurring_revenues"):
            return tracking_values.filtered(lambda t: t.field_id.name != 'recurring_revenue')
        return super()._track_filter_for_display(tracking_values)
