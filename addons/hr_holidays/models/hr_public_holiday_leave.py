from ast import literal_eval

from pytz import timezone, utc
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.convert import relativedelta


class HrPublicHolidayLeave(models.Model):
    _name = 'hr.public.holiday.leave'
    _description = 'HR Public Leave'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    date_start = fields.Datetime(string='Start Date', default=lambda self: fields.Datetime.today(), required=True)
    date_end = fields.Datetime(string='End Date', compute="_compute_date_end", readonly=False, store=True, required=True)
    country_id = fields.Many2one('res.country', string='Country', domain=lambda self: [('id', 'in', self.env.companies.country_id.ids)])
    condition_domain = fields.Char(string='Applicability Domain', help="Define the applicability rules for this public holiday.")

    @api.depends('date_start')
    def _compute_date_end(self):
        user_tz = self.env.tz
        if not (self.env.user.tz or self.env.context.get('tz')):
            user_tz = timezone(self.company_id.resource_calendar_id.tz or 'UTC')
        for leave in self:
            if not leave.date_start or (leave.date_end and leave.date_end > leave.date_start):
                continue
            local_date_from = utc.localize(leave.date_start).astimezone(user_tz)
            local_date_to = local_date_from + relativedelta(hour=23, minute=59, second=59)
            leave.date_end = local_date_to.astimezone(utc).replace(tzinfo=None)

    @api.constrains("date_start", "date_end")
    def _check_validity_dates(self):
        if self.filtered(lambda leave: leave.date_start > leave.date_end):
            raise ValidationError(self.env._("The start date of the time off must be earlier than the end date."))

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        all_existing_leaves = self.env["hr.public.holiday.leave"].search([
            ("company_id", "in", self.company_id.ids),
            ("date_start", "<=", max(self.mapped("date_end"))),
            ("date_end", ">=", min(self.mapped("date_start"))),
        ])
        all_resource_calendars = list(self.env["resource.calendar"].search([]))
        for record in self:
            overlapping_leaves = all_existing_leaves.filtered(
                lambda leave: record.id != leave.id
                and record["company_id"] == leave["company_id"]
                and record["date_start"] <= leave["date_end"]
                and record["date_end"] >= leave["date_start"],
            )
            if overlapping_leaves and (
                not record.condition_domain or "resource_calendar_id" not in record.condition_domain
            ):
                raise ValidationError(
                    self.env._("Two public holidays cannot overlap each other for the same working hours."),
                )

            record_matcher = self._calendar_matcher(record.condition_domain)

            for leave in overlapping_leaves:
                leave_matcher = self._calendar_matcher(leave.condition_domain)
                for cal_id in all_resource_calendars + [
                    self.env["resource.calendar"],
                ]:  # self.env['resource.calendar'] for no calendars
                    if record_matcher(cal_id) and leave_matcher(cal_id):
                        raise ValidationError(
                            self.env._("Two public holidays cannot overlap each other for the same working hours.")
                        )

    def _calendar_matcher(self, condition_domain):
        """Return a function(calendar_id) -> bool based on condition_domain."""
        if not condition_domain:
            return lambda cal: True
        try:
            domain = literal_eval(condition_domain)
        except ValueError:
            return lambda cal: True

        def matcher(cal):
            for field, operator, value in domain:
                if field != "resource_calendar_id":
                    continue

                if operator == "in":
                    if cal.id not in value:
                        return False
                elif operator == "not in":
                    if cal.id in value:
                        return False
                elif operator == "=":  # not set (= False)
                    if value:
                        return False
                elif operator == "!=":  # is set (!= False)
                    if value:
                        return True
                elif operator == "ilike":
                    cal_name = cal.name if cal else ""
                    if value.lower() not in cal_name.lower():
                        return False
                elif operator == "not ilike":
                    cal_name = cal.name if cal else ""
                    if value.lower() in cal_name.lower():
                        return False

            return True

        return matcher

    @api.onchange('company_id')
    def _onchange_company_id(self):
        for leave in self:
            leave.country_id = leave.company_id.country_id or self.env.company.country_id

    # @api.model_create_multi
    # def create(self, vals_list):
    #     leaves = super().create(vals_list)
    #     # leaves._sync_resource_calendar_leaves()
    #     return leaves

    # def write(self, vals):
    #     leaves = super().write(vals)
    #     self._unlink_resource_calendar_leaves()
    #     self._sync_resource_calendar_leaves()
    #     return leaves

    # @api.ondelete(at_uninstall=False)
    # def unlink_public_holiday_leave(self):
    #     self.env['resource.calendar.leaves'].search([
    #         ('public_holiday_id', 'in', self.ids),
    #     ]).unlink()
    #     return super().unlink()

    # def _get_employees(self, condition_domain):
    #     domain = self._get_employees_domain(condition_domain)
    #     return self.env['hr.employee'].search(domain)

    # def _get_employees_domain(self, condition_domain):
    #     base_domain = [('company_id', '=', self.company_id.id)]
    #     return base_domain + literal_eval(condition_domain) if condition_domain else base_domain

    # def _sync_resource_calendar_leaves(self):
    #     for record in self:
    #         employees = self._get_employees(record.condition_domain)

    #         for employee in employees:
    #             val = {
    #                 'is_public': True,
    #                 'public_holiday_id': record.id,
    #                 'resource_id': employee.resource_id.id,
    #                 'name': record.name,
    #                 'company_id': record.company_id.id,
    #                 'date_from': record.date_start,
    #                 'date_to': record.date_end,
    #             }
    #             record.env['resource.calendar.leaves'].sudo().create(val)

    # def _unlink_resource_calendar_leaves(self):
    #     resource_calendar_leaves = self.env['resource.calendar.leaves']
    #     for record in self:
    #         resource_calendar_leaves |= record.env['resource.calendar.leaves'].search([('public_holiday_id', '=', record.id)])
    #     resource_calendar_leaves.unlink()
