from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools.safe_eval import safe_eval

class IZIKPI(models.Model):
    _name = 'izi.kpi'
    _description = 'Key Performance Indicator'
    _order = 'long_sequence asc, id asc'

    name = fields.Char('Name', required=True)
    name_with_sequence = fields.Char('Name Sequence', store=True, compute='_compute_name_and_sequence')
    name_with_space = fields.Char('Name Space', store=True, compute='_compute_name_and_sequence')
    category_id = fields.Many2one('izi.kpi.category', string='Category', required=True)
    parent_id = fields.Many2one('izi.kpi', string='Parent')
    child_ids = fields.One2many('izi.kpi', 'parent_id', string='Childs')
    child_count = fields.Integer('Count of Child KPIs', compute='_compute_child_count')
    period_ids = fields.Many2many('izi.kpi.period', string='Periods', required=True)
    success_criteria = fields.Selection([('more', 'More Is Better'), ('less', 'Less Is Better')], default='more', string='Success Criteria', required=True)
    sequence = fields.Integer('Sequence')
    long_sequence = fields.Char('Long Sequence', store=True, compute='_compute_name_and_sequence', recursive=True)
    interval = fields.Selection([
        ('day', 'Daily'),
        ('week', 'Weekly'),
        ('month', 'Monthly'),
        ('year', 'Annually'),
    ], default='month', string='Interval', required=True)
    line_ids = fields.One2many('izi.kpi.line', 'kpi_id', string='Details', copy=False)
    calculation_method = fields.Selection([('model', 'Odoo Model'), ('manual', 'Input Manually')], default='model', string='Method')
    table_model_id = fields.Many2one('izi.table', string='Table Model', required=False, ondelete='cascade')
    table_id = fields.Many2one('izi.table', string='Table', required=False, ondelete='cascade')
    date_field_id = fields.Many2one('izi.table.field', string='Date Field', required=False)
    measurement_field_id = fields.Many2one('izi.table.field', string='Measurement', required=False)
    model_id = fields.Many2one('ir.model', string='Model')
    model_name = fields.Char('Model Name', related='model_id.model')
    domain = fields.Char('Domain')
    summarize_childs = fields.Boolean(string='Summarize Childs', help='Summarize Values From Child Key Performance Indicators', default=True)

    @api.model_create_multi
    def create(self, vals_list):
        recs = super(IZIKPI, self).create(vals_list)
        for rec in recs:
            rec.parent_validation()
        return recs

    def write(self, vals):
        res = super(IZIKPI, self).write(vals)
        fields = [
            'category_id', 'success_criteria', 'interval',
            'table_model_id', 'table_id', 'model_id',
            'date_field_id', 'measurement_field_id', 'period_ids',
        ]
        if self.child_ids:
            child_vals = {}
            for key in vals:
                if key in fields:
                    child_vals[key] = vals[key]
            self.child_ids.write(child_vals)
        self.parent_validation()
        return res

    def parent_validation(self):
        for record in self:
            if record.parent_id:
                if record.category_id != record.parent_id.category_id or \
                    record.success_criteria != record.parent_id.success_criteria or \
                    record.interval != record.parent_id.interval or \
                    record.table_model_id != record.parent_id.table_model_id or \
                    record.table_id != record.parent_id.table_id or \
                    record.date_field_id != record.parent_id.date_field_id or \
                    record.measurement_field_id != record.parent_id.measurement_field_id or \
                    record.period_ids != record.parent_id.period_ids or \
                    record.model_id != record.parent_id.model_id:
                    raise UserError('Some attributes must be the same with the parent')
    
    @api.onchange('parent_id')
    def onchange_parent_id(self):
        self.category_id = self.parent_id.category_id.id
        self.success_criteria = self.parent_id.success_criteria
        self.interval = self.parent_id.interval
        self.table_model_id = self.parent_id.table_model_id.id
        self.table_id = self.parent_id.table_id.id
        self.model_id = self.parent_id.model_id.id
        self.date_field_id = self.parent_id.date_field_id.id
        self.measurement_field_id = self.parent_id.measurement_field_id.id
        self.period_ids = self.parent_id.period_ids.ids
    
    @api.onchange('table_model_id')
    def onchange_table_model_id(self):
        self.ensure_one()
        self.table_id = self.table_model_id.id
        self.model_id = self.table_model_id.model_id.id

    def _compute_child_count(self):
        for record in self:
            record.child_count = len(record.child_ids)

    @api.depends('name', 'sequence', 'parent_id.long_sequence')
    def _compute_name_and_sequence(self):
        for record in self:
            # Name With Space
            space = ''
            i = 0
            while i < record.get_parent_number():
                space += '__'
                i += 1
            record.name_with_space = '%s%s' % (space, record.name)
            # Long sequence
            long_sequence = str(record.sequence or record.id).zfill(5)
            long_sequence = record.get_parent_long_sequence(long_sequence)
            record.long_sequence = long_sequence
            code_sequence = str(record.sequence).zfill(2)
            code_sequence = record.get_parent_sequence(code_sequence)
            record.name_with_sequence = '[%s] %s' % (code_sequence, record.name)

    def get_parent_number(self, prev=0):
        self.ensure_one()
        if self.parent_id:
            prev = self.parent_id.get_parent_number(prev+1)
        return prev
    
    def get_parent_sequence(self, prev_sequence):
        self.ensure_one()
        if self.parent_id:
            prev_sequence = '%s.%s' % (str(self.parent_id.sequence).zfill(2), prev_sequence)
            prev_sequence = self.parent_id.get_parent_sequence(prev_sequence)
        return prev_sequence
    
    def get_parent_long_sequence(self, prev_long_sequence):
        self.ensure_one()
        if self.parent_id:
            prev_long_sequence = '%s.%s' % (str(self.parent_id.sequence or self.parent_id.id).zfill(5), prev_long_sequence)
            prev_long_sequence = self.parent_id.get_parent_long_sequence(prev_long_sequence)
        return prev_long_sequence

    def action_calculate_value(self):
        self.ensure_one()
        self = self.with_context(lang='en_US')
        kpi_data_by_period = {}
        # Run Calculation On Child KPI First
        child_kpi_datas = []
        for child in self.child_ids:
            child_kpi_data_by_period = child.action_calculate_value()
            child_kpi_datas.append(child_kpi_data_by_period)
        # Get Values & Target By Child KPIs
        if self.child_ids and self.summarize_childs:
            for ckd_by_period in child_kpi_datas:
                for period in self.period_ids:
                    if period.id in ckd_by_period:
                        if period.id not in kpi_data_by_period:
                            kpi_data_by_period[period.id] = {}
                        child_lines_by_name = ckd_by_period[period.id]
                        for line_name in child_lines_by_name:
                            if line_name not in kpi_data_by_period[period.id]:
                                kpi_data_by_period[period.id][line_name] = {
                                    'kpi_id': self.id,
                                    'period_id': period.id,
                                    'name': line_name,
                                    'date': child_lines_by_name[line_name].date,
                                    'interval': self.interval,
                                    'achievement': 0,
                                    'target': 0,
                                    'value': 0,
                                }
                            kpi_data_by_period[period.id][line_name]['target'] += child_lines_by_name[line_name].target
                            kpi_data_by_period[period.id][line_name]['value'] += child_lines_by_name[line_name].value
            # Create Line
            self.line_ids.unlink()
            for period_id in kpi_data_by_period:
                for line_name in kpi_data_by_period[period_id]:
                    total_target = kpi_data_by_period[period_id][line_name]['target']
                    total_value = kpi_data_by_period[period_id][line_name]['value']
                    total_achievement = 0
                    if total_target != 0:
                        total_achievement = 100 * total_value / total_target
                    kpi_data_by_period[period_id][line_name]['achievement'] = total_achievement
                    new_line = self.env['izi.kpi.line'].create(kpi_data_by_period[period_id][line_name])
                    kpi_data_by_period[period_id][line_name] = new_line
            return kpi_data_by_period

        # If Not Summarize By Child KPIs
        data_by_group_key = {}
        # ORM Model Calculation
        if self.calculation_method == 'model':
            domain = []
            measurements = []
            groups = []
            group_key = ''
            if self.measurement_field_id and self.date_field_id and self.interval:
                if self.domain:
                    domain = safe_eval(self.domain)
                measurements = ['measurement:sum(%s)' % self.measurement_field_id.field_name]
                group_key = '%s:%s' % (self.date_field_id.field_name, self.interval)
                groups = [group_key]
            else:
                raise UserError('Please input measurement, date field and interval first.') 

            res_data = self.env[self.model_id.model].read_group(domain, measurements, groups, lazy=False)
            for rd in res_data:
                if rd[group_key] not in data_by_group_key:
                    data_by_group_key[rd[group_key]] = rd['measurement']

        # Generate Line
        for period in self.period_ids:
            start_date = period.start_date
            end_date = period.end_date
            interval_start_date = False
            interval_end_date = False
            interval_delta = False
            if self.interval == 'day':
                interval_start_date = start_date
                interval_end_date = end_date
                interval_delta = timedelta(days=1)
                interval_dateformat = '%d %b %Y'
            elif self.interval == 'week':
                interval_start_date = start_date - timedelta(days=start_date.weekday())
                if interval_start_date.year < period.start_date.year:
                    interval_start_date = interval_start_date + timedelta(days=7)
                interval_end_date = end_date - timedelta(days=end_date.weekday())
                interval_delta = timedelta(days=7)
                interval_dateformat = 'W%W %Y'
            elif self.interval == 'month':
                interval_start_date = start_date.replace(day=1)
                interval_end_date = end_date.replace(day=1)
                interval_delta = relativedelta(months=1)
                interval_dateformat = '%B %Y'
            elif self.interval == 'year':
                interval_start_date = start_date.replace(day=1, month=1)
                interval_end_date = end_date.replace(day=1, month=1)
                interval_delta = relativedelta(years=1)
                interval_dateformat = '%Y'
            
            # Check Period Lines
            period_lines_by_name = {}
            for line in self.line_ids:
                # Delete Line With Different Period
                if line.period_id.id not in self.period_ids.ids:
                    line.unlink()
                    continue
                if line.period_id.id == period.id:
                    # Delete Line With Different Interval
                    if line.interval != self.interval or line.date < period.start_date or line.date > period.end_date:
                        line.unlink()
                        continue
                    period_lines_by_name[line.name] = line

            if interval_start_date and interval_end_date and interval_delta:
                cur_date = interval_start_date
                while cur_date <= interval_end_date:
                    cur_name = cur_date.strftime(interval_dateformat).replace('W0', 'W')
                    measurement_value = 0
                    if self.calculation_method == 'model' and cur_name in data_by_group_key:
                        measurement_value = data_by_group_key[cur_name]
                    if self.calculation_method == 'manual' and cur_name in period_lines_by_name:
                        measurement_value = period_lines_by_name[cur_name].value
                    # Check Period Line With The Same Name
                    if cur_name in period_lines_by_name:
                        target = period_lines_by_name[cur_name].target
                        achievement = 0
                        if target != 0:
                            achievement = 100 * measurement_value / target
                        period_lines_by_name[cur_name].write({
                            'value': measurement_value,
                            'achievement': achievement,
                        })
                    else:
                        line_values = {
                            'kpi_id': self.id,
                            'period_id': period.id,
                            'name': cur_name,
                            'date': cur_date,
                            'target': 0,
                            'value': measurement_value,
                            'interval': self.interval,
                            'achievement': 0,
                        }
                        new_line = self.env['izi.kpi.line'].create(line_values)
                        period_lines_by_name[cur_name] = new_line
                    cur_date += interval_delta
            if period.id not in kpi_data_by_period:
                kpi_data_by_period[period.id] = period_lines_by_name
        return kpi_data_by_period

class IZIKPICategory(models.Model):
    _name = 'izi.kpi.category'
    _description = 'IZI KPI Category'

    name = fields.Char('Name')

class IZIKPIPeriod(models.Model):
    _name = 'izi.kpi.period'
    _description = 'IZI KPI Period'

    name = fields.Char('Name')
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)

class IZIKPILine(models.Model):
    _name = 'izi.kpi.line'
    _description = 'Key Performance Indicator Values'
    _order = 'date asc'

    interval = fields.Selection([
        ('day', 'Daily'),
        ('week', 'Weekly'),
        ('month', 'Monthly'),
        ('year', 'Annually'),
    ], default='month', string='Interval')
    kpi_id = fields.Many2one('izi.kpi', string='KPI', required=True, ondelete='cascade')
    period_id = fields.Many2one('izi.kpi.period', string='Period')
    name = fields.Char('Name')
    date = fields.Date('Date')
    target = fields.Float('Target')
    value = fields.Float('Value')
    achievement = fields.Float('Achievement')
