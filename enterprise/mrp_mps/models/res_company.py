# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.date_utils import start_of, end_of, add, subtract
from odoo.tools.misc import format_date


class Company(models.Model):
    _inherit = "res.company"

    manufacturing_period = fields.Selection([
        ('year', 'Yearly'),
        ('month', 'Monthly'),
        ('week', 'Weekly'),
        ('day', 'Daily')], string="Manufacturing Period",
        default='month', required=True,
        help="Default value for the time ranges in Master Production Schedule report.")
    manufacturing_period_to_display_year = fields.Integer(
        'Number of columns for the yearly period to display in Master Production Schedule', default=3)
    manufacturing_period_to_display_month = fields.Integer(
        'Number of columns for the monthly period to display in Master Production Schedule', default=12)
    manufacturing_period_to_display_week = fields.Integer(
        'Number of columns for the weekly period to display in Master Production Schedule', default=12)
    manufacturing_period_to_display_day = fields.Integer(
        'Number of columns for the daily period to display in Master Production Schedule', default=30)
    mrp_mps_show_starting_inventory = fields.Boolean(
        'Display Starting Inventory', default=True)
    mrp_mps_show_demand_forecast = fields.Boolean(
        'Display Demand Forecast', default=True)
    mrp_mps_show_actual_demand = fields.Boolean(
        'Display Actual Demand', default=False)
    mrp_mps_show_indirect_demand = fields.Boolean(
        'Display Indirect Demand', default=True)
    mrp_mps_show_to_replenish = fields.Boolean(
        'Display To Replenish', default=True)
    mrp_mps_show_actual_replenishment = fields.Boolean(
        'Display Actual Replenishment', default=False)
    mrp_mps_show_safety_stock = fields.Boolean(
        'Display Safety Stock', default=True)
    mrp_mps_show_available_to_promise = fields.Boolean(
        'Display Available to Promise', default=False)
    mrp_mps_show_actual_demand_year_minus_1 = fields.Boolean(
        'Display Actual Demand Last Year', default=False)
    mrp_mps_show_actual_demand_year_minus_2 = fields.Boolean(
        'Display Actual Demand Before Year', default=False)

    @api.model
    def _is_field_mps_display_group(self, fname):
        return (
            self._fields[fname].type == 'boolean' and
            fname.startswith(('mrp_mps', 'x_mrp_mps', 'x_studio_mrp_mps'))
        )

    def _get_date_range(self, years=False, force_period=False):
        """ Return the date range for a production schedude depending the
        manufacturing period and the number of columns to display specify by the
        user. It returns a list of tuple that contains the timestamp for each
        column.
        """
        self.ensure_one()
        date_range = []
        period = force_period or self.manufacturing_period
        if not years:
            years = 0
        first_day = start_of(subtract(fields.Date.today(), years=years), period)
        for columns in range(self['manufacturing_period_to_display_%s' % period]):
            last_day = end_of(first_day, period)
            date_range.append((first_day, last_day))
            first_day = add(last_day, days=1)
        return date_range

    def _date_range_to_str(self, force_period=False):
        date_range = self._get_date_range(force_period=force_period)
        dates_as_str = []
        period = force_period or self.manufacturing_period
        for date_start, date_stop in date_range:
            if period == 'year':
                dates_as_str.append(format_date(self.env, date_start, date_format='yyyy'))
            elif period == 'month':
                dates_as_str.append(format_date(self.env, date_start, date_format='MMM yyyy'))
            elif period == 'week':
                dates_as_str.append(_('Week %(week_num)s (%(start_date)s-%(end_date)s/%(month)s)',
                    week_num=format_date(self.env, date_start, date_format='w'),
                    start_date=format_date(self.env, date_start, date_format='d'),
                    end_date=format_date(self.env, date_stop, date_format='d'),
                    month=format_date(self.env, date_stop, date_format='MMM')
                ))
            else:
                dates_as_str.append(format_date(self.env, date_start, date_format='MMM d'))
        return dates_as_str

    def write(self, vals):
        if (('manufacturing_period_to_display_year' in vals and vals['manufacturing_period_to_display_year'] <= 0)
                or ('manufacturing_period_to_display_month' in vals and vals['manufacturing_period_to_display_month'] <= 0)
                or ('manufacturing_period_to_display_week' in vals and vals['manufacturing_period_to_display_week'] <= 0)
                or ('manufacturing_period_to_display_day' in vals and vals['manufacturing_period_to_display_day'] <= 0)):
            raise UserError(_("Manufacturing Settings: Your Master Production Schedule must always display at least 1 period."))
        if len(vals) == 1:
            fname, = vals.keys()
            if self._is_field_mps_display_group(fname) and self.env.user.has_group('mrp.group_mrp_manager'):
                return super(Company, self.sudo()).write(vals)
        return super().write(vals)

    def save_company_settings(self, vals):
        """ Function to call from JS to avoid a full reload of the page and context. """
        return self.write(vals)
