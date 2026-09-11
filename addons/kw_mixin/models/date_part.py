import datetime
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

MONTH_STR = {'1': _('January'), '2': _('February'), '3': _('March'),
             '4': _('April'), '5': _('May'), '6': _('June'), '7': _('July'),
             '8': _('August'), '9': _('September'), '10': _('October'),
             '11': _('November'), '12': _('December'), }

DOW_STR = {'1': _('Monday'), '2': _('Tuesday'), '3': _('Wednesday'),
           '4': _('Thursday'), '5': _('Friday'), '6': _('Saturday'),
           '7': _('Sunday'), }


class YearMixin(models.AbstractModel):
    _name = 'kw.year.mixin'
    _description = 'Year Mixin'

    year = fields.Integer(
        required=True, index=True)
    year_str = fields.Char(
        compute='_compute_year', string='Year (xxxx)', store=True, )

    @api.depends('year', )
    def _compute_year(self):
        for obj in self:
            obj.year_str = '{}'.format(obj.year or '')

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['year_str'] = '{}'.format(val['year'] or '')
        return super().create(vals_list)

    def write(self, vals):
        if 'year' in vals:
            vals['year_str'] = '{}'.format(vals['year'] or '')
        return super().write(vals)

    @staticmethod
    def get_year(date):
        return datetime.datetime.strptime(date, '%Y-%m-%d').year

    @staticmethod
    def get_default_year():
        date = fields.Date.from_string(fields.Date.today())
        return date.year if date.month < 12 else date.year + 1


class DayOfWeekMixin(models.AbstractModel):
    _name = 'kw.dow.mixin'
    _description = 'Day of week Mixin'

    # pylint: disable=R1710
    @staticmethod
    def get_isoweekday(date):
        if isinstance(date, datetime.datetime):
            date = date.date()
        elif isinstance(date, datetime.date):
            pass
        elif isinstance(date, str):
            date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        else:
            return False
        return date.isoweekday()

    @classmethod
    def get_isoweekday_name(cls, date):
        return cls.get_weekday_name(cls.get_isoweekday(date))

    # pylint: disable=R1710
    @staticmethod
    def get_weekday_name(day):
        if str(day) in DOW_STR.keys():
            return DOW_STR[str(day)]


class WeekMixin(models.AbstractModel):
    _name = 'kw.week.mixin'
    _description = 'Week Mixin'

    week = fields.Integer(
        required=True, index=True)
    week_str = fields.Char(
        compute='_compute_week', string='Week (Wxx)', store=True, )

    @api.depends('week', )
    def _compute_week(self):
        for obj in self:
            obj.week_str = 'W{0:0>2}'.format(obj.week or '')

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['week_str'] = 'W{0:0>2}'.format(val['week'] or '')
        return super().create(vals_list)

    def write(self, vals):
        if 'week' in vals:
            vals['week_str'] = 'W{0:0>2}'.format(vals['week'] or '')
        return super().write(vals)

    @staticmethod
    def get_week(date):
        if isinstance(date, (datetime.datetime, datetime.date)):
            return int(date.strftime('%V'))
        if isinstance(date, str):
            return int(
                datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%V'))
        return False

    @staticmethod
    def get_monday(year, week):
        week = int(float(week))
        year = int(float(year))
        week_str = '{}-{}-1'.format(year, week)
        date = datetime.datetime.strptime(week_str, '%Y-%W-%w')
        if int(date.strftime("%V")) != week:
            delta = week - int(date.strftime('%V'))
            date += datetime.timedelta(days=delta * 7)
        return date


class MonthMixin(models.AbstractModel):
    _name = 'kw.month.mixin'
    _description = 'Month mixin'

    month = fields.Integer(
        required=True, index=True)
    month_str = fields.Char(
        compute='_compute_month', string='Month (xx)', store=True, )

    @api.depends('month', )
    def _compute_month(self):
        for obj in self:
            obj.month_str = '{0:0>2}'.format(obj.month or '')

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['month_str'] = '{0:0>2}'.format(val['month'] or '')
        return super().create(vals_list)

    def write(self, vals):
        if 'month' in vals:
            vals['month_str'] = '{0:0>2}'.format(vals['month'] or '')
        return super().write(vals)

    @staticmethod
    def get_month(date):
        return datetime.datetime.strptime(date, '%Y-%m-%d').month

    @api.constrains('month', )
    def _constrains_month(self):
        for obj in self:
            if obj.month and (not 1 <= obj.month <= 12):
                raise ValidationError(
                    _('Wrong month value: must be from 1 to 12'))

    @staticmethod
    def get_default_month():
        date = fields.Date.from_string(fields.Date.today())
        return date.month if date.month < 12 else 1


class QuarterMixin(models.AbstractModel):
    _name = 'kw.quarter.mixin'
    _description = 'Quarter mixin'

    quarter = fields.Integer(
        required=True, index=True)
    quarter_str = fields.Char(
        compute='_compute_quarter', string='Quarter (Qx)', store=True, )

    @api.depends('quarter', )
    def _compute_quarter(self):
        for obj in self:
            obj.quarter_str = 'Q{}'.format(obj.quarter or '')

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['quarter_str'] = 'Q{}'.format(val['quarter'] or '')
        return super().create(vals_list)

    def write(self, vals):
        if 'quarter' in vals:
            vals['quarter_str'] = 'Q{}'.format(vals['quarter'] or '')
        return super().write(vals)

    @staticmethod
    def get_quarter(date):
        date = (datetime.datetime.strptime(date, '%Y-%m-%d').month - 1)
        return date // 3 + 1

    @api.constrains('quarter', )
    def _constrains_quarter(self):
        for obj in self:
            if obj.quarter and (not 1 <= obj.quarter <= 4):
                raise ValidationError(
                    _('Wrong quarter value: must be from 1 to 4'))
