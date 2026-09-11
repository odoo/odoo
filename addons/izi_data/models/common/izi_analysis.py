# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
import sqlparse
import pytz
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError, UserError
from itertools import accumulate
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from random import randint
import pandas
import json
import re

DEFAULT_DATA_SCRIPT = """
response = {
    'data': [
        {
            'id': 1,
            'value': 10,
            'name': 'Product A',
        },
        {
            'id': 1,
            'value': 20,
            'name': 'Product B',
        }
    ],
    'metrics': ['value'],
    'dimensions': ['name'],
}
"""

class IZIAnalysisCategory(models.Model):
    _name = 'izi.analysis.category'
    _description = 'IZI Analysis Category'

    name = fields.Char(string='Name', required=True)

class IZIAnalysis(models.Model):
    _name = 'izi.analysis'
    _description = 'IZI Analysis'

    name = fields.Char(string='Name', required=True)
    source_id = fields.Many2one('izi.data.source', string='Data Source', required=True, ondelete='cascade', default=lambda self: self._default_source())
    source_type = fields.Selection(string='Data Source Type', related='source_id.type')
    method = fields.Selection([
        ('model', 'Odoo Model'),
        ('query', 'Query'),
        ('table', 'Table Mart'), # The Output Of Mart Table Can Be Stored In dataframe Variable
        ('table_view', 'Table View'), # Will Be Deprecated
        # ('data_script', 'Direct Data Script'), # Will Be Deprecated, Moved To Table With Direct Attributes
        # ('kpi', 'Key Performance Indicator'), # Deprecated
    ], default='model', string='Method', required=True)
    table_name = fields.Char('Table View Name')
    table_id = fields.Many2one('izi.table', string='Table', required=False, ondelete='cascade')
    table_view_id = fields.Many2one('izi.table', string='Table View', required=False, ondelete='cascade')
    table_model_id = fields.Many2one('izi.table', string='Table Model', required=False, ondelete='cascade')
    db_query = fields.Text('Query', related='table_id.db_query', readonly=False, store=True)
    metric_ids = fields.One2many('izi.analysis.metric', 'analysis_id', string='Metrics', required=True)
    dimension_ids = fields.One2many('izi.analysis.dimension', 'analysis_id', string='Dimensions')
    action_id = fields.Many2one('ir.actions.act_window', string='Action Window')
    action_model = fields.Char(string='Action Model Name', related='model_id.model')
    drilldown_dimension_ids = fields.One2many('izi.analysis.drilldown.dimension', 'analysis_id', string='Drilldown Dimensions')
    filter_temp_ids = fields.One2many('izi.analysis.filter.temp', 'analysis_id', string='Filters Temp')
    filter_ids = fields.One2many('izi.analysis.filter', 'analysis_id', string='Filters')
    limit = fields.Integer(string='Limit', default=100)
    query_preview = fields.Text(string='Query Preview', compute='get_query_preview')
    sort_ids = fields.One2many(comodel_name='izi.analysis.sort', inverse_name='analysis_id', string="Sorts")
    field_ids = fields.Many2many(comodel_name='izi.table.field', compute='_get_analysis_fields')
    group_ids = fields.Many2many(comodel_name='res.groups', string='Groups')
    date_field_id = fields.Many2one('izi.table.field', string='Date Field')
    identifier_field_id = fields.Many2one('izi.table.field', string='Identifier Field')
    model_id = fields.Many2one('ir.model', string='Model')
    model_name = fields.Char('Model Name', related='model_id.model')
    domain = fields.Char('Domain')
    category_id = fields.Many2one('izi.analysis.category', string='Category')
    kpi_id = fields.Many2one('izi.kpi', 'Key Performance Indicator')
    kpi_auto_calculate = fields.Boolean('Auto Calculate When Open Dashboard', default=False)
    date_format = fields.Selection([
        ('today', 'Today'),
        ('this_week', 'This Week'),
        ('this_month', 'This Month'),
        ('this_year', 'This Year'),
        ('mtd', 'Month to Date'),
        ('ytd', 'Year to Date'),
        ('last_week', 'Last Week'),
        ('last_month', 'Last Month'),
        ('last_two_months', 'Last 2 Months'),
        ('last_three_months', 'Last 3 Months'),
        ('last_year', 'Last Year'),
        ('last_10', 'Last 10 Days'),
        ('last_30', 'Last 30 Days'),
        ('last_60', 'Last 60 Days'),
        ('custom', 'Custom Range'),
    ], default=False, string='Date Filter')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    premium = fields.Boolean('Premium', default=False)
    detail_config = fields.Boolean('All Configuration', default=False)
    
    show_popup = fields.Boolean('Show Popup', default=False)
    # For Analysis Data Script
    server_action_id = fields.Many2one('ir.actions.server', string='Action Server')
    analysis_data_script = fields.Text('Analysis Data Script', related='server_action_id.code', readonly=False)
    is_ai = fields.Boolean('Generated By AI')

    # _sql_constraints = [
    #     ('name_table_unique', 'unique(name, table_id)', 'Analysis Name Already Exist.')
    # ]

    def _default_source(self):
        source_id = False
        source = self.env['izi.data.source'].search([('type', '=', 'db_odoo')], limit=1)
        if source:
            source_id = source.id
        return source_id

    @api.onchange('method')
    def onchange_method(self):
        self.ensure_one()
        self.table_model_id = False
        self.table_view_id = False
        self.table_id = False
        if self.method != 'kpi':
            self.kpi_id = False
        # if self.method == 'table_view':
        #     self.method = 'query'
        if self.method == 'table':
            self.prepare_direct_table()

    @api.onchange('kpi_id')
    def onchange_kpi_id(self):
        self.ensure_one()
        if self.method == 'kpi' and self.kpi_id:
            table = self.env['izi.table'].search([('model_id.model', '=', 'izi.kpi.line')], limit=1)
            if not table:
                raise UserError('Table Key Performance Indicator is not found!')
            self.table_model_id = table.id
            self.name = self.kpi_id.name or 'New Analysis'
            self.domain = '''[('kpi_id', '=', %s)]''' % (self.kpi_id.id)

    @api.onchange('table_view_id')
    def onchange_table_view_id(self):
        self.ensure_one()
        if self.table_view_id:
            self.table_id = self.table_view_id.id

    @api.onchange('table_model_id')
    def onchange_table_model_id(self):
        self.ensure_one()
        if self.table_model_id:
            self.table_id = self.table_model_id.id

    @api.onchange('table_id')
    def onchange_table_id(self):
        self.ensure_one()
        self.filter_ids = False
        self.sort_ids = False
        self.metric_ids = False
        self.dimension_ids = False
        self.model_id = False
        self.domain = False
        self.date_field_id = False
        if self.table_model_id:
            self.model_id = self.table_model_id.model_id.id
        if self.method == 'table' and self.table_id and self.table_id.store_table_name and not self.db_query:
            self.db_query = '''SELECT * \nFROM %s \nLIMIT 100;''' % (self.table_id.store_table_name)
        if self.method == 'kpi' and self.kpi_id:
            self.domain = '''[('kpi_id', '=', %s)]''' % (self.kpi_id.id)
            for field in self.table_id.field_ids.sorted('name', reverse=True):
                if field.field_name == 'value' or field.field_name == 'target':
                    self.metric_ids = [(0, 0, {
                        'field_id': field.id,
                        'calculation': 'sum',
                    })]
                elif field.field_name == 'date':
                    self.dimension_ids = [(0, 0, {
                        'field_id': field.id,
                        'field_format': self.kpi_id.interval,
                    })]
                    self.date_field_id = field.id

    def action_save_and_close(self):
        if self._context.get('dashboard_id'):
            dashboard_id = self._context.get('dashboard_id')
            analysis_id = self.id
            # Create Dashboard Block
            dashboard_block = self.env['izi.dashboard.block'].create({
                'dashboard_id': dashboard_id,
                'analysis_id': analysis_id,
            })
            if self._context.get('action_open_new'):
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Analysis',
                    'target': 'new',
                    'res_id': self.id,
                    'res_model': 'izi.analysis',
                    'views': [[False, 'izianalysis']],
                    'context': {'analysis_id': self.id},
                }
        return True

    def action_open(self):
        if self._context.get('dashboard_id'):
            dashboard_id = self._context.get('dashboard_id')
            analysis_id = self.id
            # Create Dashboard Block
            dashboard_block = self.env['izi.dashboard.block'].create({
                'dashboard_id': dashboard_id,
                'analysis_id': analysis_id,
            })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Analysis',
            'target': 'current',
            'res_id': self.id,
            'res_model': 'izi.analysis',
            'views': [[False, 'izianalysis']],
            'context': {'analysis_id': self.id},
        }

    # Unlink
    def unlink(self):
        res = super(IZIAnalysis, self).unlink()
        return res
    
    def action_duplicate(self):
        self.ensure_one()
        self.copy()

    def action_refresh_table_list(self):
        self.ensure_one()
        if self.source_id:
            self.source_id.get_source_tables()
        if self.env.context.get('from_ui', False):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Analysis',
                'target': 'new',
                'res_id': self.id,
                'res_model': 'izi.analysis',
                'views': [[False, 'form']],
                'context': {'active_test': False},
            }

    def _set_default_metric(self):
        self.ensure_one()
        self.filter_ids.unlink()
        self.sort_ids.unlink()
        self.metric_ids.unlink()
        self.dimension_ids.unlink()
        
        Field = self.env['izi.table.field']
        # Default Metric
        metric_field = Field.search([('field_type', 'in', ('numeric', 'number')),
                                    ('table_id', '=', self.table_id.id)], limit=1, order='id asc')
        if not metric_field:
            metric_field = Field.search([('field_type', 'in', ('numeric', 'number')),
                                        ('table_id', '=', self.table_id.id)], limit=1)
        if metric_field:
            self.metric_ids = [(0, 0, {
                'field_id': metric_field.id,
                'calculation': 'count',
            })]
    
    def build_query(self):
        self.ensure_one()
        if self.method == 'query':
            table = self.env['izi.table'].search([('name', '=', self.name), ('is_query', '=', True)], limit=1)
            if not table:
                table = self.env['izi.table'].create({
                    'name': self.name,
                    'source_id': self.source_id.id,
                    'is_query': True,
                    'db_query': self.db_query,
                })
            table.get_table_fields()
            # self._set_default_metric()
            self.table_id = table.id
            return {
                'type': 'ir.actions.act_window',
                'name': 'Analysis',
                'target': 'new',
                'res_id': self.id,
                'res_model': 'izi.analysis',
                'views': [[False, 'form']],
            }
    
    def prepare_direct_table(self):
        self.ensure_one()
        if self.method == 'table' and self.name and self.source_id:
            table = self.env['izi.table'].search([('name', '=', self.name)], limit=1)
            if not table:
                table = self.env['izi.table'].create({
                    'name': self.name,
                    'source_id': self.source_id.id,
                    'stored_option': 'direct',
                    'is_stored': True,
                    'is_direct': True,
                    'is_query': False,
                })
            self.table_id = table.id
    
    def get_table_datas(self):
        self.ensure_one()
        return self.table_id.with_context(test_query=True).get_table_datas()

    @api.model_create_multi
    def create(self, vals_list):
        recs = super(IZIAnalysis, self).create(vals_list)
        # for analysis in recs:
        #     if not analysis.metric_ids:
        #         analysis._set_default_metric()
        return recs

    def write(self, vals):
        for analysis in self:
            if vals.get('analysis_data_script') and not analysis.server_action_id:
                # Create Action Server
                server_action = self.env['ir.actions.server'].create({
                    'name': 'Get Analysis Data %s' % (analysis.name),
                    'model_id': self.env['ir.model'].search([('model', '=', 'izi.analysis')], limit=1).id,
                    'state': 'code',
                    'code': vals.get('analysis_data_script'),
                })
                vals['server_action_id'] = server_action.id
            if vals.get('name') and analysis.method in ('query', 'table_view') and analysis.table_id:
                analysis.table_id.name = vals.get('name')
        res = super(IZIAnalysis, self).write(vals)
        # for analysis in self:
        #     if not analysis.metric_ids:
        #         analysis._set_default_metric()
        return res

    def copy(self, default=None):
        self.ensure_one()
        if self._context.get('action_copy'):
            analysis = self.search([('name', 'like', self.name)])
            new_identifier = str(len(analysis) + 1)
            if not default or type(default) != dict:
                default = {}
            default.update({
                'name': '%s %s' % (self.name, new_identifier),
            })
        analysis = super(IZIAnalysis, self.with_context(copy=True)).copy(default)
        if self._context.get('action_copy'):
            if self.method in ('table_view', 'query') and self.table_id:
                tables = self.env['izi.table'].search([('name', 'like', self.table_id.name)])
                new_identifier = str(len(tables) + 1)
                new_table = self.table_id.copy({
                    'name': '%s %s' % (self.table_id.name, new_identifier),
                    'db_query': self.table_id.db_query,
                })
                new_table.get_table_fields()
                analysis.table_id = new_table.id
                analysis.table_view_id = new_table.id
            elif self.method == 'data_script' and self.server_action_id:
                new_code = self.server_action_id.code
                new_action = self.env['ir.actions.server'].create({
                    'name': 'Get Analysis Data %s' % (analysis.name),
                    'model_id': self.env['ir.model'].search([('model', '=', 'izi.analysis')], limit=1).id,
                    'state': 'code',
                    'code': new_code,
                })
                analysis.server_action_id = new_action.id
            elif self.method == 'table' and self.table_id and self.table_id.is_stored:
                if not self._context.get('action_copy_from_conversation', False):
                    tables = self.env['izi.table'].search([('name', 'like', self.table_id.name), ('is_stored', '=', True)])
                    new_identifier = str(len(tables) + 1)
                    new_code = ''
                    if self.table_id.cron_id and self.table_id.cron_id.ir_actions_server_id:
                        new_code = self.table_id.cron_id.ir_actions_server_id.code or ''
                        new_code = new_code.replace(self.table_id.store_table_name, '%s_%s' % (self.table_id.store_table_name, new_identifier))
                    new_table = self.table_id.copy({
                        'name': '%s %s' % (self.table_id.name, new_identifier),
                        'is_stored': True,
                        'cron_code': new_code,
                    })
                    for field in self.table_id.field_ids:
                        new_field = field.copy({
                            'table_id': new_table.id,
                        })
                    new_table.update_schema_store_table()
                    analysis.table_id = new_table.id
            
            # Metric & Dimensions
            new_metric_ids = []
            for metric in self.metric_ids:
                field = self.env['izi.table.field'].search([('field_name', '=', metric.field_id.field_name), ('table_id', '=', analysis.table_id.id)], limit=1)
                if field:
                    new_metric = metric.copy({
                        'field_id': field.id,
                    })
                    new_metric_ids.append(new_metric.id)
            analysis.metric_ids = [(6, 0, new_metric_ids)]
            
            new_dimension_ids = []
            for dimension in self.dimension_ids:
                field = self.env['izi.table.field'].search([('field_name', '=', dimension.field_id.field_name), ('table_id', '=', analysis.table_id.id)], limit=1)
                if field:
                    new_dimension = dimension.copy({
                        'field_id': field.id,
                    })
                    new_dimension_ids.append(new_dimension.id)
            analysis.dimension_ids = [(6, 0, new_dimension_ids)]
            
            new_sort_ids = []
            for sort in self.sort_ids:
                field = self.env['izi.table.field'].search([('field_name', '=', sort.field_id.field_name), ('table_id', '=', analysis.table_id.id)], limit=1)
                if field:
                    new_sort = sort.copy({
                        'field_id': field.id,
                    })
                    new_sort_ids.append(new_sort.id)
            analysis.sort_ids = [(6, 0, new_sort_ids)]

            # Visual Config
            new_avcs = []
            for avc in self.analysis_visual_config_ids:
                new_avcs += [(0, 0, {
                    'visual_config_id': avc.visual_config_id.id,
                    'string_value': avc.string_value,
                })]
            analysis.analysis_visual_config_ids = new_avcs
                    
        return analysis
    
    def get_data_script(self):
        self.ensure_one()
        if self.method == 'data_script':
            return (self.analysis_data_script or '', 'python')
        elif self.method in ('query', 'table_view'):
            return (self.db_query or '', 'sql')
        elif self.method == 'table':
            if self.table_id.is_stored and self.table_id.cron_id:
                return (self.table_id.cron_id.code or '', 'python')
            return ''
        return (False, False)

    def write_data_script(self, script, to_execute=False):
        self.ensure_one()
        if self.method == 'data_script':
            self.analysis_data_script = script
            self.server_action_id.run()
            return True
        elif self.method in ('query', 'table_view'):
            self.db_query = script
            if to_execute:
                self.build_query()
            return True
        elif self.method == 'table':
            if self.table_id.is_stored and self.table_id.cron_id:
                self.table_id.cron_id.code = script
                if to_execute:
                    self.table_id.method_direct_trigger()
                return True
        return False
    
    def try_write_data_script(self, script, to_execute=False, context=[]):
        result = {}
        try:
            result['code'] = 200
            result['is_success'] = self.with_context(context).write_data_script(script, to_execute)
        except Exception as e:
            self.env.cr.rollback()
            result['code'] = 500
            result['is_error'] = True
            error_message = str(e)
            error_messages = error_message.split(' while evaluating')
            if error_messages:
                error_message = error_messages[0]
            error_messages = error_message.split('>: ')
            if error_messages and len(error_messages) >= 2:
                error_message = error_messages[1]
            error_message = error_message.replace('"', '')
            result['error'] = error_message
        return result

    @api.depends('metric_ids', 'dimension_ids')
    def _get_analysis_fields(self):
        for analysis in self:
            field_ids = []
            for metric in analysis.metric_ids:
                field_ids.append(metric.field_id.id)
            for dimension in analysis.dimension_ids:
                field_ids.append(dimension.field_id.id)
            analysis.field_ids = list(set(field_ids))

    def get_query_preview_companion(self,field_name,drilldown_value):
        res_metrics = []
        res_dimensions = []
        res_fields = []

        # query variable
        dimension_query = ''
        dimension_queries = []
        metric_queries = []
        limit_query = ''
        where_clause = ''
        select_clause = ''

        # Build Dimension Query
        func_get_field_metric_format = getattr(self, 'get_field_metric_format_%s' % self.source_id.type)
        func_get_field_dimension_format = getattr(self, 'get_field_dimension_format_%s' % self.source_id.type)
        if self.table_id.is_stored:
            func_get_field_metric_format = getattr(self, 'get_field_metric_format_db_odoo')
            func_get_field_dimension_format = getattr(self, 'get_field_dimension_format_db_odoo')
        for dimension in self.dimension_ids:
            dimension_alias = dimension.field_id.name
            if dimension.name_alias:
                dimension_alias = dimension.name_alias
            dimension_metric = func_get_field_metric_format(
                **{'field_name': dimension.field_id.field_name, 'field_type': dimension.field_id.field_type,
                   'field_format': dimension.field_format})
            dimension_field = func_get_field_dimension_format(
                **{'field_name': dimension.field_id.field_name, 'field_type': dimension.field_id.field_type,
                   'field_format': dimension.field_format})
            metric_queries.append('%s as "%s"' % (dimension_metric, dimension_alias))
            dimension_queries.append('%s' % (dimension_field))
            res_dimensions.append(dimension_alias)
            res_fields.append(dimension_alias)
        
        # Build Metric Query
        for metric in self.metric_ids:
            metric_alias = "%s" % (metric.field_id.name)
            if metric.name_alias:
                metric_alias = metric.name_alias
            metric_queries.append('%s(%s) as "%s"' % (metric.calculation, metric.field_id.field_name, metric_alias))
            res_metrics.append(metric_alias)
            res_fields.append(metric_alias)

        if dimension_metric:
            where_clause = f"WHERE {dimension_metric} = '{drilldown_value}'"
        if metric_queries:
            select_clause = f"{field_name}, {metric_queries[1]}"
            dimension_query = 'GROUP BY %s' % (field_name)

        # Check
        if not self.table_id.table_name:
            if self.table_id.is_stored:
                table_query = self.table_id.store_table_name
            else:
                table_query = self.table_id.db_query or ''
                table_query = table_query.replace(';', '')
                table_query = '(%s) table_query' % (table_query)
        if self.limit:
            if self.limit > 0:
                limit_query = 'LIMIT %s' % (self.limit)

        query = '''
            SELECT
                %s
            FROM
                %s
            %s
            %s
            %s;
        ''' % (select_clause, table_query, where_clause, dimension_query, limit_query)
        return sqlparse.format(query, reindent=True, keyword_case='upper')

    def get_query_preview(self):
        res_metrics = []
        res_dimensions = []
        res_fields = []

        # query variable
        dimension_query = ''
        dimension_queries = []
        metric_query = ''
        metric_queries = []
        sort_query = ''
        sort_queries = []
        filter_query = "'IZI' = 'IZI'"
        filter_queries = []
        limit_query = ''

        # Build Dimension Query
        func_get_field_metric_format = getattr(self, 'get_field_metric_format_%s' % self.source_id.type)
        func_get_field_dimension_format = getattr(self, 'get_field_dimension_format_%s' % self.source_id.type)
        func_get_field_sort = getattr(self, 'get_field_sort_format_%s' % self.source_id.type)
        if self.table_id.is_stored:
            func_get_field_metric_format = getattr(self, 'get_field_metric_format_db_odoo')
            func_get_field_dimension_format = getattr(self, 'get_field_dimension_format_db_odoo')
            func_get_field_sort = getattr(self, 'get_field_sort_format_db_odoo')
        for dimension in self.dimension_ids:
            dimension_alias = dimension.field_id.name
            if dimension.name_alias:
                dimension_alias = dimension.name_alias
            dimension_metric = func_get_field_metric_format(
                **{'field_name': dimension.field_id.field_name, 'field_type': dimension.field_id.field_type,
                   'field_format': dimension.field_format})
            dimension_field = func_get_field_dimension_format(
                **{'field_name': dimension.field_id.field_name, 'field_type': dimension.field_id.field_type,
                   'field_format': dimension.field_format})
            metric_queries.append('%s as "%s"' % (dimension_metric, dimension_alias))
            dimension_queries.append('%s' % (dimension_field))
            res_dimensions.append(dimension_alias)
            res_fields.append(dimension_alias)

        # Build Metric Query
        for metric in self.metric_ids:
            # metric_alias = "%s of %s" % (metric.calculation.title(), metric.field_id.name)
            metric_alias = "%s" % (metric.field_id.name)
            if metric.name_alias:
                metric_alias = metric.name_alias
            metric_queries.append('%s(%s) as "%s"' % (metric.calculation, metric.field_id.field_name, metric_alias))
            res_metrics.append(metric_alias)
            res_fields.append(metric_alias)

        # Build Filter Query
        for fltr in self.filter_ids:
            open_bracket = ''
            close_bracket = ''
            if fltr.open_bracket:
                open_bracket = '('
            if fltr.close_bracket:
                close_bracket = ')'

            fltr_value = ' %s' % fltr.value.replace("'", '').replace('"', '')
            if fltr.field_type == 'string':
                fltr_value = ' \'%s\'' % fltr.value.replace("'", '').replace('"', '')

            fltr_str = '%s %s%s %s %s%s' % (fltr.condition, open_bracket,
                                            fltr.field_id.field_name, fltr.operator_id.name, fltr_value, close_bracket)
            filter_queries.append(fltr_str)

        filter_query += ' %s' % ' '.join(filter_queries)

        # Build Sort Query
        for sort in self.sort_ids:
            if sort.field_format:
                field_sort = func_get_field_sort(
                    **{'field_name': sort.field_id.field_name, 'field_type': sort.field_id.field_type,
                       'field_format': sort.field_format, 'sort': sort.sort})
                sort_queries.append(field_sort)
            elif sort.field_calculation:
                sort_queries.append('%s(%s) %s' % (sort.field_calculation, sort.field_id.field_name, sort.sort))
            else:
                sort_queries.append('%s %s' % (sort.field_id.field_name, sort.sort))

        # Build Query
        # SELECT operation(metric) FROM table WHERE filter GROUP BY dimension ORDER BY sort
        metric_query = ', '.join(metric_queries)
        dimension_query = ', '.join(dimension_queries)
        table_query = self.table_id.table_name
        sort_query = ', '.join(sort_queries)

        # Check
        if not self.table_id.table_name:
            if self.table_id.is_stored:
                table_query = self.table_id.store_table_name
            else:
                table_query = self.table_id.db_query or ''
                table_query = table_query.replace(';', '')
                table_query = '(%s) table_query' % (table_query)
        if filter_query:
            filter_query = 'WHERE %s' % (filter_query)
        if dimension_query:
            dimension_query = 'GROUP BY %s' % (dimension_query)
        if sort_query:
            sort_query = 'ORDER BY %s' % (sort_query)
        if self.limit:
            if self.limit > 0:
                limit_query = 'LIMIT %s' % (self.limit)

        query = '''
            SELECT
                %s
            FROM
                %s
            %s
            %s
            %s
            %s;
        ''' % (metric_query, table_query, filter_query, dimension_query, sort_query, limit_query)

        self.query_preview = sqlparse.format(query, reindent=True, keyword_case='upper')

    def get_analysis_data(self, **kwargs):
        self.ensure_one()
        if self.method in ('model', 'kpi'):
            if self.method == 'kpi' and self.kpi_id and self.kpi_auto_calculate:
                self.kpi_id.action_calculate_value()
            return self.get_analysis_data_model(**kwargs)
        elif self.method in ('table_view', 'query', 'table'):
            if self.table_id and self.table_id.is_direct:
                return self.get_analysis_data_frame(**kwargs)
            return self.get_analysis_data_query(**kwargs)
        elif self.method in ('data_script'):
            return self.get_analysis_data_script(**kwargs)
    
    def get_analysis_data_frame(self, **kwargs):
        self.ensure_one()
        self = self.sudo()
        if self.table_id and self.table_id.cron_id and self.table_id.cron_id.code:
            res = self.table_id.cron_id.with_context(izi_table=self, kwargs=kwargs).ir_actions_server_id.run()
            # Automatic Get Fields From Data Frame
            if res and type(res) == dict and 'dataframe' in res and isinstance(res.get('dataframe'), pandas.DataFrame):
                df = res.get('dataframe')
                df = df.fillna('')
                
                # To Apply Filters
                domain = []
                if kwargs.get('filters'):
                    # Check Default Date Filter In Analysis If Filters Empty
                    if self.date_field_id and not kwargs.get('filters').get('date_format'):
                        if self.date_format:
                            kwargs['filters']['date_format'] = self.date_format
                            if self.date_format == 'custom' and (self.start_date or self.end_date):
                                kwargs['filters']['date_range'] = [self.start_date, self.end_date]
                    # Process Date Filter
                    if self.date_field_id and kwargs.get('filters').get('date_format'):
                        start_date = False
                        end_date = False
                        start_datetime = False
                        end_datetime = False
                        date_format = kwargs.get('filters').get('date_format')
                        if date_format == 'custom' and kwargs.get('filters').get('date_range'):
                            date_range = kwargs.get('filters').get('date_range')
                            start_date = date_range[0]
                            end_date = date_range[1]
                            if start_date:
                                start_datetime = start_date + ' 00:00:00'
                                start_datetime = self.convert_to_utc(start_datetime)
                            if end_date:
                                end_datetime = end_date + ' 23:59:59'
                                end_datetime = self.convert_to_utc(end_datetime)
                        elif date_format != 'custom':
                            date_range = self.get_date_range_by_date_format(date_format)
                            start_date = date_range.get('start_date')
                            end_date = date_range.get('end_date')
                            start_datetime = date_range.get('start_datetime')
                            start_datetime = self.convert_to_utc(start_datetime)
                            end_datetime = date_range.get('end_datetime')
                            end_datetime = self.convert_to_utc(end_datetime)
                        # Create Domain
                        if self.date_field_id.field_type == 'date':
                            if start_date:
                                domain.append((self.date_field_id.field_name, '>=', start_date))
                            if end_date:
                                domain.append((self.date_field_id.field_name, '<=', end_date))
                        if self.date_field_id.field_type == 'datetime':
                            if start_datetime:
                                domain.append((self.date_field_id.field_name, '>=', start_datetime))
                            if end_datetime:
                                domain.append((self.date_field_id.field_name, '<=', end_datetime))
                    # Process Dynamic Filters
                    if kwargs.get('filters').get('dynamic'):
                        for dynamic_filter in kwargs.get('filters').get('dynamic'):
                            if dynamic_filter.get('field_name') and dynamic_filter.get('operator') and dynamic_filter.get('values'):
                                # Convert to Array
                                if not isinstance(dynamic_filter.get('values'), list):
                                    dynamic_filter['values'] = [dynamic_filter.get('values')]
                                # Check If All Values Number
                                is_number = True
                                f_values_in_number = []
                                for f_val in dynamic_filter.get('values'):
                                    if type(f_val) == int:
                                        f_values_in_number.append(int(f_val))
                                    elif type(f_val) == float:
                                        f_values_in_number.append(float(f_val))
                                    else:
                                        is_number = False
                                if is_number:
                                    dynamic_filter['values'] = f_values_in_number
                                # Add Domain
                                if len(dynamic_filter.get('values')) == 1 and dynamic_filter.get('operator') in ['=', '!=', '>', '>=', '<', '<=', 'like', 'ilike', 'not like', 'not ilike']:
                                    domain.append((dynamic_filter.get('field_name'), dynamic_filter.get('operator'), dynamic_filter.get('values')[0]))
                                else:
                                    domain.append((dynamic_filter.get('field_name'), 'in', dynamic_filter.get('values')))
                    # Process Action Filters
                    # Action Filters Is Active When The Chart Is Clicked
                    if kwargs.get('filters').get('action'):
                        for action_filter in kwargs.get('filters').get('action'):
                            action_filter_field_name = action_filter.get('field_name')
                            action_filter_operator = action_filter.get('operator', '=')
                            action_filter_dimension_alias = action_filter.get('dimension_alias')
                            action_filter_value = action_filter.get('value')
                            if action_filter_dimension_alias and action_filter_dimension_alias in field_by_alias:
                                action_filter_field_name = field_by_alias[action_filter_dimension_alias]
                            if action_filter_field_name:
                                # Check If Value Number
                                is_number = False
                                if type(action_filter_value) == int or type(action_filter_value) == float:
                                    is_number = True
                                # Convert to UTC
                                action_domain = [[action_filter_field_name, action_filter_operator, action_filter_value]]
                                action_domain = self.convert_domain_to_utc(action_domain)
                                if action_domain:
                                    action_filter_value = action_domain[0][2]
                                # Add Domain
                                # TODO: Somehow it works with string value. Need to check later
                                domain.append((action_filter_field_name, action_filter_operator, action_filter_value))
                # Build Filter Temp Query
                # Temporary Filters is in Analysis View
                if kwargs.get('filter_temp_values'):
                    for temp_filter in kwargs.get('filter_temp_values'):
                        temp_domain = self.get_filter_temp_query_model(temp_filter)
                        if temp_domain:
                            domain += temp_domain
                
                # Transform Domain To Pandas Filter
                # df.query('Value1 > 20 and Value2 < 7')
                pd_queries = []
                for dm in domain:
                    if len(dm) == 3:
                        dm_key = dm[0]
                        dm_op = dm[1]
                        if dm_op == '=':
                            dm_op = '=='
                        dm_val = dm[2]
                        if type(dm_val) == str:
                            dm_val = "'%s'" % dm_val
                        pd_queries.append('%s %s %s' % (dm_key, dm_op, dm_val))
                if pd_queries:
                    pd_query = ' and '.join(pd_queries)
                    df = df.query(pd_query)
                
                rename = {}
                df_fields = []
                df_dimensions = []
                for dimension in self.dimension_ids:
                    field_name = dimension.name_alias or dimension.name or dimension.field_id.field_name
                    df_dimensions.append(field_name)
                    df_fields.append(field_name)
                    df.rename(columns={dimension.field_id.field_name: field_name}, inplace=True)
                    rename[dimension.field_id.field_name] = field_name
                
                df_metrics = []
                df_metrics_dict = {}
                for metric in self.metric_ids:
                    field_name = metric.name_alias or metric.name or metric.field_id.field_name
                    df_metrics.append(field_name)
                    df_fields.append(field_name)
                    df.rename(columns={metric.field_id.field_name: field_name}, inplace=True)
                    rename[metric.field_id.field_name] = field_name
                    df_calculation = 'sum'
                    if metric.calculation == 'avg':
                        df_calculation = 'mean'
                    elif metric.calculation == 'count':
                        df_calculation = 'count'
                    df_metrics_dict[field_name] = df_calculation
                
                df_sorts = []
                df_sorts_asc = []
                for sort in self.sort_ids:
                    field_name = sort.field_id.name or sort.field_id.field_name
                    if sort.field_id.field_name in rename:
                        field_name = rename[sort.field_id.field_name]
                    df_sorts.append(field_name)
                    # df.rename(columns={sort.field_id.field_name: field_name}, inplace=True)
                    sort_asc = True
                    if sort.sort == 'desc':
                        sort_asc = False
                    df_sorts_asc.append(sort_asc)
                
                # Grouping & Aggregation
                if df_dimensions and df_metrics_dict:
                    df = df.groupby(df_dimensions).agg(df_metrics_dict).reset_index()
                else:
                    df = df[df_fields]
                df = df.sort_values(by=df_sorts, ascending=df_sorts_asc)
                if self.limit:
                    df = df.head(self.limit)
                
                return {
                    'data': df.to_dict('records'),
                    'metrics': df_metrics,
                    'dimensions': df_dimensions,
                    'fields': df_fields,
                    'values': df.values.tolist(),
                }
        return {
            'data': [],
            'metrics': [],
            'dimensions': [],
            'fields': [],
            'values': [],
        }


    def get_analysis_data_script(self, **kwargs):
        self.ensure_one()
        if self.server_action_id:
            response = self.server_action_id.with_context(kwargs=kwargs).run()
            if response and isinstance(response, dict):
                # Generate Fields
                is_metric_by_field = {}
                fields = []
                if response.get('dimensions'):
                    for dimension in response.get('dimensions'):
                        fields.append(dimension)
                else:
                    response['dimensions'] = []
                if response.get('metrics'):
                    for metric in response.get('metrics'):
                        fields.append(metric)
                        is_metric_by_field[metric] = True
                else:
                    response['metrics'] = []
                response['fields'] = fields
                response['is_metric_by_field'] = is_metric_by_field
                # Generate Values
                values = []
                if response.get('data'):
                    for dt in response.get('data'):
                        value = []
                        for field in fields:
                            value.append(dt.get(field))
                        values.append(value)
                response['values'] = values
                # Return
                return response
        return {
            'data': [],
            'metrics': [],
            'dimensions': [],
            'fields': [],
            'values': [],
        }

    def get_analysis_data_model(self, **kwargs):
        self.ensure_one()
        if not self.metric_ids:
            return {
                'data': [],
                'metrics': [],
                'dimensions': [],
                'fields': [],
                'values': [],
            }
            raise ValidationError('To query the data, analysis must have at least one metric')
        if not self.model_id:
            raise ValidationError('To query the data with odoo orm, analysis must use table from odoo model')

        res_data = []
        res_metrics = []
        res_dimensions = []
        res_fields = []
        res_values = []

        dimension_queries = []
        field_by_alias = {}
        metric_queries = []
        sort_queries = []
        alias_by_field_name = {}
        field_names = []
        metric_field_names = []
        selection_dict_by_field_name = {}
        field_type_by_alias = {}

        max_dimension = False
        if 'max_dimension' in kwargs:
            max_dimension = kwargs.get('max_dimension')

        # Field
        for field in self.table_id.field_ids:
            field_alias = field.name
            field_by_alias[field_alias] = field.field_name
            field_type_by_alias[field_alias] = field.field_type
        # Dimension
        dimensions = self.dimension_ids
        
        # Check For Drill Down
        drilldown_level = 0
        count_dimension = 0

        drilldown_sort_field = False
        if kwargs.get('drilldown_level'):
            drilldown_level = kwargs.get('drilldown_level')
            if kwargs.get('drilldown_field'):
                drilldown_field = self.env['izi.table.field'].search([('field_name', '=', kwargs.get('drilldown_field')), ('table_id', '=', self.table_id.id)], limit=1)
                drilldown_visual_type = self.env['izi.visual.type'].search([('name', '=', 'bar')])
                if self.visual_type_id.name == 'bar_line':
                    drilldown_visual_type = self.visual_type_id
                drilldown_field_format = kwargs.get('drilldown_field_subtype', False)
                drilldown_sort_field = drilldown_field
                if drilldown_field.field_type in ['date', 'datetime']:
                    if not drilldown_field_format:
                        drilldown_field_format = 'day'
                    drilldown_visual_type = self.env['izi.visual.type'].search([('name', '=', 'line')])
                if drilldown_field:
                    self.drilldown_dimension_ids.unlink()
                    dimensions = self.env['izi.analysis.drilldown.dimension'].create({
                        'analysis_id': self.id,
                        'field_id': drilldown_field.id,
                        'visual_type_id': drilldown_visual_type.id,
                        'field_format': drilldown_field_format,
                    })
                
        for dimension in dimensions:
            # Date Format
            if dimension.field_id.field_type in ('date', 'datetime') and dimension.field_format:
                field_name = '%s:%s' % (dimension.field_id.field_name, dimension.field_format)
            else:
                field_name = dimension.field_id.field_name
            # Check If Selection
            if self.env[self.model_id.model]._fields.get(dimension.field_id.field_name, False):
                if self.env[self.model_id.model]._fields.get(dimension.field_id.field_name).type == 'selection':
                    model_field = self.env[self.model_id.model]._fields[dimension.field_id.field_name]
                    selection = None
                    if not model_field.related:
                        selection = model_field.selection
                    else:
                        if model_field.related_field:
                            selection = model_field.related_field.selection
                            if not selection and model_field.related_field.args and type(model_field.related_field.args) == dict and model_field.related_field.args.get('selection'):
                                selection = model_field.related_field.args['selection']
                    if selection:
                        selection_dict_by_field_name[field_name] = dict(selection)
            dimension_queries.append(field_name)
            field_names.append(field_name)
            # Field Alias
            dimension_alias = dimension.field_id.name
            if dimension.name_alias:
                dimension_alias = dimension.name_alias
            res_dimensions.append(dimension_alias)
            res_fields.append(dimension_alias)
            field_by_alias[dimension_alias] = dimension.field_id.field_name
            alias_by_field_name[field_name] = dimension_alias
            count_dimension += 1
            if max_dimension:
                if count_dimension >= max_dimension:
                    break
       
        # Metric
        for metric in self.metric_ids:
            # metric_alias = "%s of %s" % (metric.calculation.title(), metric.field_id.name)
            metric_alias = "%s" % (metric.field_id.name)
            field_name = "%s_of_%s" % (metric.calculation.lower(), metric.field_id.field_name)
            field_names.append(field_name)
            metric_field_names.append(field_name)
            # Field Alias
            if metric.name_alias:
                metric_alias = metric.name_alias
            metric_calculation = metric.calculation.lower() if metric.calculation != 'csum' else 'sum'
            metric_queries.append('%s:%s(%s)' % (field_name, metric_calculation, metric.field_id.field_name))
            res_metrics.append(metric_alias)
            res_fields.append(metric_alias)
            alias_by_field_name[field_name] = metric_alias

        # Sort
        if drilldown_sort_field:
            sort_query = '%s asc' % (drilldown_sort_field.field_name)
            sort_queries.append(sort_query)
        else:
            for sort in self.sort_ids:
                sort_query = '%s %s' % (sort.field_id.field_name, sort.sort)
                for metric in self.metric_ids:
                    if sort.field_id == metric.field_id:
                        # metric_alias = "%s of %s" % (metric.calculation.title(), metric.field_id.name)
                        metric_alias = "%s" % (metric.field_id.name)
                        field_name = "%s_of_%s" % (metric.calculation.lower(), metric.field_id.field_name)
                        sort_query = '%s %s' % (field_name, sort.sort)
                        break
                sort_queries.append(sort_query)
        sort_queries = (',').join(sort_queries)

        # Data
        # There Are 4 Types Of Filters
        # 1. Date Filter (Above Dashboard, Affect Multiple Charts)
        # 2. Dashboard Dynamic Filter (Above Dashboard, Affect Multiple Charts)
        # 3. Analysis Temporary Filter (Above Chart, Affect Only One Chart)
        # 4. Action Filter (Takes Effect When Click On Chart)
        domain = []
        if self.domain:
            domain = safe_eval(self.domain)
        if kwargs.get('filters'):
            # Check Default Date Filter In Analysis If Filters Empty
            if self.date_field_id and not kwargs.get('filters').get('date_format'):
                if self.date_format:
                    kwargs['filters']['date_format'] = self.date_format
                    if self.date_format == 'custom' and (self.start_date or self.end_date):
                        kwargs['filters']['date_range'] = [self.start_date, self.end_date]
            # Process Date Filter
            if self.date_field_id and kwargs.get('filters').get('date_format'):
                start_date = False
                end_date = False
                start_datetime = False
                end_datetime = False
                date_format = kwargs.get('filters').get('date_format')
                if date_format == 'custom' and kwargs.get('filters').get('date_range'):
                    date_range = kwargs.get('filters').get('date_range')
                    start_date = date_range[0]
                    end_date = date_range[1]
                    if start_date:
                        start_datetime = start_date + ' 00:00:00'
                        start_datetime = self.convert_to_utc(start_datetime)
                    if end_date:
                        end_datetime = end_date + ' 23:59:59'
                        end_datetime = self.convert_to_utc(end_datetime)
                elif date_format != 'custom':
                    date_range = self.get_date_range_by_date_format(date_format)
                    start_date = date_range.get('start_date')
                    end_date = date_range.get('end_date')
                    start_datetime = date_range.get('start_datetime')
                    start_datetime = self.convert_to_utc(start_datetime)
                    end_datetime = date_range.get('end_datetime')
                    end_datetime = self.convert_to_utc(end_datetime)
                # Create Domain
                if self.date_field_id.field_type == 'date':
                    if start_date:
                        domain.append((self.date_field_id.field_name, '>=', start_date))
                    if end_date:
                        domain.append((self.date_field_id.field_name, '<=', end_date))
                if self.date_field_id.field_type == 'datetime':
                    if start_datetime:
                        domain.append((self.date_field_id.field_name, '>=', start_datetime))
                    if end_datetime:
                        domain.append((self.date_field_id.field_name, '<=', end_datetime))
            # Process Dynamic Filters
            if kwargs.get('filters').get('dynamic'):
                for dynamic_filter in kwargs.get('filters').get('dynamic'):
                    if dynamic_filter.get('field_name') and dynamic_filter.get('operator') and dynamic_filter.get('values'):
                        # Convert to Array
                        if not isinstance(dynamic_filter.get('values'), list):
                            dynamic_filter['values'] = [dynamic_filter.get('values')]
                        # Check If All Values Number
                        is_number = True
                        f_values_in_number = []
                        for f_val in dynamic_filter.get('values'):
                            if type(f_val) == int:
                                f_values_in_number.append(int(f_val))
                            elif type(f_val) == float:
                                f_values_in_number.append(float(f_val))
                            else:
                                is_number = False
                        if is_number:
                            dynamic_filter['values'] = f_values_in_number
                        # Add Domain
                        if len(dynamic_filter.get('values')) == 1 and dynamic_filter.get('operator') in ['=', '!=', '>', '>=', '<', '<=', 'like', 'ilike', 'not like', 'not ilike']:
                            domain.append((dynamic_filter.get('field_name'), dynamic_filter.get('operator'), dynamic_filter.get('values')[0]))
                        else:
                            domain.append((dynamic_filter.get('field_name'), 'in', dynamic_filter.get('values')))
            # Process Action Filters
            # Action Filters Is Active When The Chart Is Clicked
            if kwargs.get('filters').get('action'):
                for action_filter in kwargs.get('filters').get('action'):
                    action_filter_field_name = action_filter.get('field_name')
                    action_filter_operator = action_filter.get('operator', '=')
                    action_filter_dimension_alias = action_filter.get('dimension_alias')
                    action_filter_value = action_filter.get('value')
                    if action_filter_dimension_alias and action_filter_dimension_alias in field_by_alias:
                        action_filter_field_name = field_by_alias[action_filter_dimension_alias]
                    if action_filter_field_name:
                        # Check If Value Number
                        is_number = False
                        if type(action_filter_value) == int or type(action_filter_value) == float:
                            is_number = True
                        # Convert to UTC
                        action_domain = [[action_filter_field_name, action_filter_operator, action_filter_value]]
                        action_domain = self.convert_domain_to_utc(action_domain)
                        if action_domain:
                            action_filter_value = action_domain[0][2]
                        # Add Domain
                        # TODO: Somehow it works with string value. Need to check later

                        #R: Onhit returning the Value of selection. in domain, should be using the Key of selection
                        #this is to update the domain
                        field_type = self.env[self.model_id.model]._fields[action_filter_field_name].type
                        if field_type == 'selection':
                            selection_field = self.env[self.model_id.model]._fields[action_filter_field_name]
                            selection_options = dict(selection_field.selection(self.env[self.model_id.model])) if callable(selection_field.selection) else dict(selection_field.selection)
                            key = [k for k, v in selection_options.items() if self._languange_translation(v) == action_filter_value]
                            if key:
                                action_filter_value = key[0]

                        domain.append((action_filter_field_name, action_filter_operator, action_filter_value))
        # Build Filter Temp Query
        # Temporary Filters is in Analysis View
        if kwargs.get('filter_temp_values'):
            for temp_filter in kwargs.get('filter_temp_values'):
                temp_domain = self.get_filter_temp_query_model(temp_filter)
                if temp_domain:
                    domain += temp_domain
        
        # Before Get Data
        # We Can Return The Domain Only For Open List View
        if self._context.get('action_return_domain'):
            return domain

        drilldown_limit = False
        if kwargs.get('drilldown_limit') and kwargs.get('drilldown_limit') > 0:
            drilldown_limit = kwargs.get('drilldown_limit')

        records = self.env[self.model_id.model].read_group(domain, metric_queries, dimension_queries, limit=(drilldown_limit or self.limit), orderby=sort_queries, lazy=False)
        res_data = []
        for record in records:
            dict_value = {}
            for field_name in field_names:
                value = False
                key = field_name
                if record.get(field_name):
                    value = record.get(field_name)
                    if type(record.get(field_name)) is tuple:
                        value = record.get(field_name)[1]
                        if type(value) == dict and _value in value.keys and value._value:
                            value = value._value
                # Set Key to Field Alias
                if alias_by_field_name.get(field_name):
                    key = alias_by_field_name.get(field_name)
                # Set Value If Null
                if not value:
                    if field_name in metric_field_names:
                        value = 0
                    else:
                        value = ''
                # Set Selection Label
                if field_name in selection_dict_by_field_name:
                    selection_dict = selection_dict_by_field_name[field_name]
                    if value in selection_dict:
                        value = selection_dict[value]
                dict_value[key] = value
            res_data.append(dict_value)

        # Cumulative SUM
        for metric in res_metrics:
            calc = metric.lower().split(' ')[0]
            if calc == 'csum':
                totals = [item[metric] for item in res_data]
                cumulative_sums = list(accumulate(totals))
                for i, item in enumerate(res_data):
                    item[metric] = cumulative_sums[i]

        # Values
        for record in res_data:
            res_value = []
            for key in record:
                res_value.append(record[key])
            res_values.append(res_value)
        
        result = {
            'data': res_data,
            'metrics': res_metrics,
            'dimensions': res_dimensions,
            'fields': res_fields,
            'values': res_values,
            'field_by_alias': field_by_alias,
            'field_type_by_alias': field_type_by_alias,
        }

        if 'test_analysis' not in self._context:
            return result
        else:
            title = _("Successfully Get Data Analysis")
            message = _("""
                Your analysis looks fine!
                Sample Data:
                %s
            """ % (str(result.get('data')[0]) if result.get('data') else str(result.get('data'))))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': message,
                    'sticky': False,
                }
            }

    def _languange_translation(self, text):
        # R: THIS FUNCTION IS TO REVERT FROM OTHER LANGUANGE WORD TO ORIGINAL WORD (IF USING .po FILE TRANSLATION)
        languange = self.env.context.get('lang')
        translation = self.env['ir.translation'].search([
            ('value', '=', text),
            ('lang', '=', languange),
        ], limit=1)
        return translation.src if translation else None

    def _transform_json_data(self, data):
        transform_data = []
        transform_fields = []
        transform_lang = False
        all_fields = []
        checked_fields = []
        is_all_checked = False
        if data:
            dt = data[0]
            all_fields = tuple(dt.keys())
        for dt in data:
            for field in all_fields:
                if tuple(checked_fields) == all_fields:
                    is_all_checked = True
                    break
                if field in checked_fields:
                    continue
                if dt[field]:
                    if type(dt[field]) == dict:
                        transform_fields.append(field)
                        transform_lang = next(iter(dt[field]))
                        checked_fields.append(field)
                    else:
                        checked_fields.append(field)
            if is_all_checked:
                break
        if transform_fields:
            for dt in data:
                for field in transform_fields:
                    if dt[field]:
                        if transform_lang:
                            dt[field] = dt[field][transform_lang]
                        else:
                            dt[field] = dt[field][next(iter(dt[field]))]
                transform_data.append(dt)
            return transform_data
        else:
            return data
    
    def check_special_variable(self, table_query):
        # Replace Special Variable in Query
        user_id = self.env.user.id
        user_name = self.env.user.name
        user_tz = self.env.user.tz
        company_id = self.env.user.company_id.id
        company_name = self.env.user.company_id.name
        company_ids = []
        if self._context and self._context.get('allowed_company_ids'):
            allowed_companies = self.env['res.company'].browse(self._context.get('allowed_company_ids'))
            if allowed_companies:
                company_id = allowed_companies[0].id
                company_name = allowed_companies[0].name
                for company in allowed_companies:
                    company_ids.append(str(company.id))

        if '#user_id' in table_query:
            table_query = table_query.replace('#user_id', str(user_id))
        if '#company_ids' in table_query:
            table_query = table_query.replace('#company_ids', '(%s)' % (',').join(company_ids))
        if '#company_id' in table_query:
            table_query = table_query.replace('#company_id', str(company_id))
        if '#user_name' in table_query:
            table_query = table_query.replace('#user_name', str(user_name))
        if '#company_name' in table_query:
            table_query = table_query.replace('#company_name', str(company_name))
        if '#user_tz' in table_query:
            table_query = table_query.replace('#user_tz', str(user_tz))
        if 'test_query' in self._context:
            try:
                matches = re.findall(r"limit \d+", table_query, re.IGNORECASE)
                if matches:
                    for match in matches:
                        table_query = table_query.replace(match, 'limit 1')
                match = re.search(r"limit \d+", table_query, re.IGNORECASE)
                if match:
                    table_query = table_query.replace(match.group(), 'limit 1')
                else:
                    table_query = table_query = '%s %s' % (table_query, 'limit 1')
            except Exception:
                pass
            
        if 'table_query' not in table_query:
            table_query = '(%s) table_query' % (table_query)

        return table_query

    def get_analysis_data_query(self, **kwargs):
        self.ensure_one()
        if not self.metric_ids:
            return {
                'data': [],
                'metrics': [],
                'dimensions': [],
                'fields': [],
                'values': [],
            }
            raise ValidationError('To query the data, analysis must have at least one metric')

        res_data = []
        res_metrics = []
        res_dimensions = []
        res_fields = []
        res_values = []

        # Query Variable
        dimension_query = ''
        dimension_queries = []
        field_by_alias = {}
        field_by_name = {}
        metric_query = ''
        metric_queries = []
        sort_query = ''
        sort_queries = []
        filter_query = "'IZI' = 'IZI'"
        filter_queries = []
        filter_temp_result_list = []
        limit_query = ''
        dashboard_filter_queries = []
        res_lang_codes = []
        field_type_by_alias = {}

        res_langs = self.env['res.lang'].with_context(active_test=False).search([('active', '=', True)], order='active desc')
        for res_lang in res_langs:
            res_lang_codes.append(res_lang.code)

        # Field
        for field in self.table_id.field_ids:
            field_alias = field.name
            field_by_alias[field_alias] = field.field_name
            field_by_name[field.field_name] = field
            field_type_by_alias[field_alias] = field.field_type
        
        max_dimension = False
        if 'max_dimension' in kwargs:
            max_dimension = kwargs.get('max_dimension')

        # Build Dimension Query
        func_get_field_metric_format = getattr(self, 'get_field_metric_format_%s' % self.source_id.type)
        func_get_field_dimension_format = getattr(self, 'get_field_dimension_format_%s' % self.source_id.type)
        func_get_field_sort = getattr(self, 'get_field_sort_format_%s' % self.source_id.type)
        if self.table_id.is_stored:
            func_get_field_metric_format = getattr(self, 'get_field_metric_format_db_odoo')
            func_get_field_dimension_format = getattr(self, 'get_field_dimension_format_db_odoo')
            func_get_field_sort = getattr(self, 'get_field_sort_format_db_odoo')
        
        # Dimensions
        dimensions = self.dimension_ids
        
        # Check For Drill Down
        drilldown_level = 0
        count_dimension = 0

        if kwargs.get('drilldown_level'):
            drilldown_level = kwargs.get('drilldown_level')
            if kwargs.get('drilldown_field'):
                drilldown_field = self.env['izi.table.field'].search([('field_name', '=', kwargs.get('drilldown_field')), ('table_id', '=', self.table_id.id)], limit=1)
                drilldown_visual_type = self.env['izi.visual.type'].search([('name', '=', 'bar')])
                if self.visual_type_id.name == 'bar_line':
                    drilldown_visual_type = self.visual_type_id
                drilldown_field_format = kwargs.get('drilldown_field_subtype', False)
                drilldown_sort_field = False
                if drilldown_field.field_type in ['date', 'datetime']:
                    if not drilldown_field_format:
                        drilldown_field_format = 'day'
                    drilldown_visual_type = self.env['izi.visual.type'].search([('name', '=', 'line')])
                    drilldown_sort_field = drilldown_field
                if drilldown_field:
                    self.drilldown_dimension_ids.unlink()
                    dimensions = self.env['izi.analysis.drilldown.dimension'].create({
                        'analysis_id': self.id,
                        'field_id': drilldown_field.id,
                        'visual_type_id': drilldown_visual_type.id,
                        'field_format': drilldown_field_format,
                    })

        for dimension in dimensions:
            dimension_alias = dimension.field_id.name
            if dimension.name_alias:
                dimension_alias = dimension.name_alias
            dimension_metric = func_get_field_metric_format(
                **{'field_name': dimension.field_id.field_name, 'field_type': dimension.field_id.field_type,
                   'field_format': dimension.field_format})
            dimension_field = func_get_field_dimension_format(
                **{'field_name': dimension.field_id.field_name, 'field_type': dimension.field_id.field_type,
                   'field_format': dimension.field_format})
            metric_queries.append('%s as "%s"' % (dimension_metric, dimension_alias))
            dimension_queries.append('%s' % (dimension_field))
            res_dimensions.append(dimension_alias)
            res_fields.append(dimension_alias)
            field_by_alias[dimension_alias] = dimension.field_id.field_name

            count_dimension += 1
            if max_dimension:
                if count_dimension >= max_dimension:
                    break
        
        if kwargs.get('custom_drilldown_field'):
            metric_queries = ['%s as "%s"' % (kwargs.get('custom_drilldown_field'), kwargs.get('custom_drilldown_field_label'))]
            dimension_queries = [kwargs.get('custom_drilldown_field')]
        # Build Metric Query
        for metric in self.metric_ids:
            # metric_alias = "%s of %s" % (metric.calculation.title(), metric.field_id.name)
            metric_alias = "%s" % (metric.field_id.name)
            if metric.name_alias:
                metric_alias = metric.name_alias
            metric_queries.append('%s(%s) as "%s"' % (metric.calculation, metric.field_id.field_name, metric_alias))
            res_metrics.append(metric_alias)
            res_fields.append(metric_alias)

        # Build Filter Query
        # There Are 4 Types Of Filters
        # 1. Date Filter (Above Dashboard, Affect Multiple Charts)
        # 2. Dashboard Dynamic Filter (Above Dashboard, Affect Multiple Charts)
        # 3. Analysis Temporary Filter (Above Chart, Affect Only One Chart)
        # 4. Action Filter (Takes Effect When Click On Chart)
        for fltr in self.filter_ids:
            open_bracket = ''
            close_bracket = ''
            if fltr.open_bracket:
                open_bracket = '('
            if fltr.close_bracket:
                close_bracket = ')'

            if fltr.operator_id.name not in ('in', 'not in'):
                if fltr.field_type in ('numeric', 'number'):
                    fltr_value = ' %s' % fltr.value.replace("'", '').replace('"', '').replace('$$', '')
                else:
                    fltr_value = ' $$%s$$' % fltr.value.replace("'", '').replace('"', '').replace('$$', '')
            else:
                fltr_value = ' %s' % fltr.value

            fltr_str = '%s %s%s %s %s%s' % (fltr.condition, open_bracket,
                                            fltr.field_id.field_name, fltr.operator_id.name, fltr_value, close_bracket)
            filter_queries.append(fltr_str)

        filter_query += ' %s' % ' '.join(filter_queries)

        # Build Dashboard Date Filter Query
        if kwargs.get('filters'):
            # Date Filters
            if self.date_field_id and kwargs.get('filters').get('date_format'):
                start_date = False
                end_date = False
                start_datetime = False
                end_datetime = False
                date_format = kwargs.get('filters').get('date_format')
                if date_format == 'custom' and kwargs.get('filters').get('date_range'):
                    date_range = kwargs.get('filters').get('date_range')
                    start_date = date_range[0]
                    end_date = date_range[1]
                    if start_date:
                        start_datetime = start_date + ' 00:00:00'
                        start_datetime = self.convert_to_utc(start_datetime)
                    if end_date:
                        end_datetime = end_date + ' 23:59:59'
                        end_datetime = self.convert_to_utc(end_datetime)
                elif date_format != 'custom':
                    date_range = self.get_date_range_by_date_format(date_format)
                    start_date = date_range.get('start_date')
                    end_date = date_range.get('end_date')
                    start_datetime = date_range.get('start_datetime')
                    start_datetime = self.convert_to_utc(start_datetime)
                    end_datetime = date_range.get('end_datetime')
                    end_datetime = self.convert_to_utc(end_datetime)
                # Create Query
                if self.date_field_id.field_type == 'date':
                    if start_date:
                        dashboard_filter_queries.append('(%s >= $$%s$$)' % (self.date_field_id.field_name, start_date))
                    if end_date:
                        dashboard_filter_queries.append('(%s <= $$%s$$)' % (self.date_field_id.field_name, end_date))
                if self.date_field_id.field_type == 'datetime':
                    if start_datetime:
                        dashboard_filter_queries.append('(%s >= $$%s$$)' % (self.date_field_id.field_name, start_datetime))
                    if end_datetime:
                        dashboard_filter_queries.append('(%s <= $$%s$$)' % (self.date_field_id.field_name, end_datetime))
            # Process Dynamic Filters
            # Dynamic Filters is in Dashboard View
            if kwargs.get('filters').get('dynamic'):
                for dynamic_filter in kwargs.get('filters').get('dynamic'):
                    if dynamic_filter.get('field_name') and dynamic_filter.get('operator') and dynamic_filter.get('values'):
                        # Convert to Array
                        if not isinstance(dynamic_filter.get('values'), list):
                            dynamic_filter['values'] = [dynamic_filter.get('values')]
                        # Check If All Values Number
                        if dynamic_filter.get('field_id'):
                            table_field = self.env['izi.table.field'].browse(dynamic_filter.get('field_id'))
                            if table_field.field_type == 'number':
                                is_number = True
                                f_values_in_number = []
                                f_values_query_string = []
                                for f_val in dynamic_filter.get('values'):
                                    f_values_in_number.append(float(f_val))
                                    f_values_query_string.append('%s' % f_val)
                            else:
                                is_number = False
                                f_values_in_number = []
                                f_values_query_string = []
                                for f_val in dynamic_filter.get('values'):
                                    f_values_query_string.append('$$%s$$' % f_val)
                        else:
                            is_number = True
                            f_values_in_number = []
                            f_values_query_string = []
                            for f_val in dynamic_filter.get('values'):
                                if type(f_val) == int:
                                    f_values_in_number.append(int(f_val))
                                    f_values_query_string.append('%s' % f_val)
                                elif type(f_val) == float:
                                    f_values_in_number.append(float(f_val))
                                    f_values_query_string.append('%s' % f_val)
                                else:
                                    is_number = False
                                    f_values_query_string.append('$$%s$$' % f_val)
                        f_values_query_string = ','.join(f_values_query_string)
                        if is_number:
                            dynamic_filter['values'] = f_values_in_number
                        # Add Query
                        if len(dynamic_filter.get('values')) == 1 and dynamic_filter.get('operator') in ['=', '!=', '>', '>=', '<', '<=', 'like', 'ilike', 'not like', 'not ilike']:
                            if not is_number:
                                if dynamic_filter.get('operator') in ['like', 'ilike', 'not like', 'not ilike']:
                                    dashboard_filter_queries.append('(%s::TEXT %s $$%%%s%%$$)' % (dynamic_filter.get('field_name'), dynamic_filter.get('operator'), dynamic_filter.get('values')[0]))
                                else:
                                    field_type_origin = False
                                    if dynamic_filter.get('field_name') in field_by_name:
                                        field_type_origin = field_by_name.get(dynamic_filter.get('field_name')).field_type_origin
                                    if field_type_origin == 'jsonb':
                                        jsonb_filter_queries = []
                                        for res_lang_code in res_lang_codes:
                                            jsonb_filter_queries.append('%s->>\'%s\' %s $$%s$$' % (dynamic_filter.get('field_name'), res_lang_code, dynamic_filter.get('operator'), dynamic_filter.get('values')[0]))
                                        dashboard_filter_queries.append('(%s)' % ' OR '.join(jsonb_filter_queries))
                                    else:
                                        dashboard_filter_queries.append('(%s::TEXT %s $$%s$$)' % (dynamic_filter.get('field_name'), dynamic_filter.get('operator'), dynamic_filter.get('values')[0]))
                            else:
                                dashboard_filter_queries.append('(%s %s %s)' % (dynamic_filter.get('field_name'), dynamic_filter.get('operator'), dynamic_filter.get('values')[0]))
                        else:
                            field_type_origin = False
                            if dynamic_filter.get('field_name') in field_by_name:
                                field_type_origin = field_by_name.get(dynamic_filter.get('field_name')).field_type_origin
                            if field_type_origin == 'jsonb':
                                jsonb_filter_queries = []
                                for res_lang_code in res_lang_codes:
                                    jsonb_filter_queries.append('(%s->>\'%s\' in (%s))' % (dynamic_filter.get('field_name'), res_lang_code, f_values_query_string))
                                dashboard_filter_queries.append('(%s)' % ' OR '.join(jsonb_filter_queries))
                            else:                                
                                dashboard_filter_queries.append('(%s in (%s))' % (dynamic_filter.get('field_name'), f_values_query_string))
            # Process Action Filters
            # Action Filters Is Active When The Chart Is Clicked
            if kwargs.get('filters').get('action'):
                for action_filter in kwargs.get('filters').get('action'):
                    action_filter_field_name = action_filter.get('field_name')
                    action_filter_operator = action_filter.get('operator', '=')
                    action_filter_dimension_alias = action_filter.get('dimension_alias')
                    action_filter_value = action_filter.get('value')
                    if action_filter_dimension_alias and action_filter_dimension_alias in field_by_alias:
                        action_filter_field_name = field_by_alias[action_filter_dimension_alias]
                    if action_filter_field_name:
                        # Convert to UTC
                        action_domain = [[action_filter_field_name, action_filter_operator, action_filter_value]]
                        if action_filter_operator.lower() not in ('in', 'not in'):
                            action_domain = self.convert_domain_to_utc(action_domain)
                        if action_domain:
                            action_filter_value = action_domain[0][2]
                        # Check If Value Number
                        is_number = False
                        if type(action_filter_value) == int or type(action_filter_value) == float:
                            is_number = True
                        # Add Query
                        if is_number:
                            dashboard_filter_queries.append('(%s %s %s)' % (action_filter_field_name, action_filter_operator, action_filter_value))
                        else:
                            if action_filter_operator.lower() in ('in', 'not in'):
                                if type(action_filter_value) in (list, tuple):
                                    action_filter_value_str = []
                                    for val in action_filter_value:
                                        if type(val) in (int, float):
                                            action_filter_value_str.append(str(val))
                                        else:
                                            action_filter_value_str.append('$$%s$$' % val)
                                    action_filter_value_str = (',').join(action_filter_value_str)
                                    action_filter_value_str = '(%s)' % action_filter_value_str
                                    dashboard_filter_queries.append('(%s %s %s)' % (action_filter_field_name, action_filter_operator, action_filter_value_str))
                            else:
                                field_type_origin = False
                                if action_filter_field_name in field_by_name:
                                    field_type_origin = field_by_name.get(action_filter_field_name).field_type_origin
                                if field_type_origin == 'jsonb':
                                    jsonb_filter_queries = []
                                    for res_lang_code in res_lang_codes:
                                        jsonb_filter_queries.append('%s->>\'%s\' %s $$%s$$' % (action_filter_field_name, res_lang_code, action_filter_operator, action_filter_value))
                                    dashboard_filter_queries.append('(%s)' % ' OR '.join(jsonb_filter_queries))
                                else:
                                    dashboard_filter_queries.append('(%s %s $$%s$$)' % (action_filter_field_name, action_filter_operator, action_filter_value))
        if dashboard_filter_queries:
            dashboard_filter_query = (' and ').join(dashboard_filter_queries)
            filter_query += ' and (%s)' % dashboard_filter_query
            
        # Build Filter Temp Query
        # Temporary Filters is in Analysis View
        func_get_filter_temp_query = getattr(self, 'get_filter_temp_query_%s' % self.source_id.type)
        if 'filter_temp_values' in kwargs:
            for filter_value in kwargs.get('filter_temp_values'):
                result_query = func_get_filter_temp_query(**{'filter_value': filter_value, 'field_by_name': field_by_name, 'res_lang_codes': res_lang_codes})
                filter_temp_result_list.append(result_query)

        for filter_temp_result in filter_temp_result_list:
            if filter_temp_result is False:
                continue

            filter_sub_query = False
            filter_sub_query = ' {join_operator} '.format(
                join_operator=filter_temp_result.get('join_operator')).join(filter_temp_result.get('query'))

            if filter_sub_query:
                filter_query += ' and (%s)' % filter_sub_query

        # Build Sort Query
        for sort in self.sort_ids:
            if kwargs.get('drilldown_level') and drilldown_sort_field:
                if drilldown_field_format:
                    field_sort = func_get_field_sort(
                        **{'field_name': drilldown_sort_field.field_name, 'field_type': drilldown_sort_field.field_type,
                        'field_format': drilldown_field_format, 'sort': 'asc'})
                    sort_queries.append(field_sort)
                else:
                    sort_queries.append('%s %s' % (drilldown_sort_field.field_name, 'asc'))
                break
            elif kwargs.get('drilldown_level') and sort.dimension_id:
                continue
            elif sort.field_format:
                field_format = sort.field_format
                field_sort = func_get_field_sort(
                    **{'field_name': sort.field_id.field_name, 'field_type': sort.field_id.field_type,
                       'field_format': field_format, 'sort': sort.sort})
                sort_queries.append(field_sort)
            elif sort.field_calculation:
                sort_queries.append('%s(%s) %s' % (sort.field_calculation, sort.field_id.field_name, sort.sort))
            elif not sort.metric_id and not sort.dimension_id:
                for metric in self.metric_ids:
                    if metric.field_id.id == sort.field_id.id:
                        sort_queries.append('%s(%s) %s' % (metric.calculation, metric.field_id.field_name, sort.sort))
                        break
            else:
                sort_queries.append('%s %s' % (sort.field_id.field_name, sort.sort))

        # Build Query
        # SELECT operation(metric) FROM table WHERE filter GROUP BY dimension ORDER BY sort
        metric_query = ', '.join(metric_queries)
        dimension_query = ', '.join(dimension_queries)
        table_query = self.table_id.table_name
        sort_query = ', '.join(sort_queries)

        # Check
        if not self.table_id.table_name:
            if self.table_id.is_stored:
                table_query = self.table_id.store_table_name
            else:
                table_query = self.table_id.db_query.replace(';', '')
                if kwargs.get('allowed_company_ids'):
                    table_query = self.with_context(allowed_company_ids=kwargs.get('allowed_company_ids')).check_special_variable(table_query)
                else:
                    table_query = self.check_special_variable(table_query)
        if filter_query:
            filter_query = 'WHERE %s' % (filter_query)
        if dimension_query:
            dimension_query = 'GROUP BY %s' % (dimension_query)
        if sort_query:
            sort_query = 'ORDER BY %s' % (sort_query)
        if self.limit:
            if self.limit > 0:
                limit_query = 'LIMIT %s' % (self.limit)
            if kwargs.get('drilldown_limit') and kwargs.get('drilldown_limit') > 0:
                limit_query = 'LIMIT %s' % (kwargs.get('drilldown_limit'))
        
        query = '''
            SELECT
                %s
            FROM
                %s
            %s
            %s
            %s
            %s;
        ''' % (metric_query, table_query, filter_query, dimension_query, sort_query, limit_query)

        func_check_query = getattr(self.source_id, 'check_query_%s' % self.source_id.type)
        func_check_query(**{
            'query': table_query,
        })
        
        # Before Get Data
        # We Can Return The Domain Only For Open List View
        if self._context.get('action_return_domain'):
            return {
                'metric_query': metric_query, 
                'table_query': table_query, 
                'filter_query': filter_query, 
                'dimension_query': dimension_query, 
                'sort_query': sort_query, 
                'limit_query': limit_query,
                'query': query,
            }

        result = {'res_data': []}
        if self.table_id.is_stored:
            self.env.cr.execute(query)
            result['res_data'] = self.env.cr.dictfetchall()
        else:
            func_get_analysis_data = getattr(self, 'get_analysis_data_%s' % self.source_id.type)
            result = func_get_analysis_data(**{
                'query': query,
            })

        res_data = result.get('res_data')
        res_data = self._transform_json_data(res_data)

        for record in res_data:
            res_value = []
            for key in record:
                res_value.append(record[key])
            res_values.append(res_value)

        result = {
            'data': res_data,
            'metrics': res_metrics,
            'dimensions': res_dimensions,
            'fields': res_fields,
            'values': res_values,
            'field_by_alias': field_by_alias,
            'field_type_by_alias': field_type_by_alias,
        }

        if 'test_analysis' not in self._context:
            return result
        else:
            title = _("Successfully Get Data Analysis")
            message = _("""
                Your analysis looks fine!
                Sample Data:
                %s
            """ % (str(result.get('data')[0]) if result.get('data') else str(result.get('data'))))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': message,
                    'sticky': False,
                }
            }

    def get_records_by_query(self,metric_query, table_query, filter_query):
        query = '''
            SELECT
                *
            FROM
                %s
            %s;
        ''' % (table_query, filter_query)

        self.env.cr.execute(query)
        if self.table_id.is_stored:
            result['res_data'] = self.env.cr.dictfetchall()
        else:
            func_get_analysis_data = getattr(self, 'get_analysis_data_%s' % self.source_id.type)
            result = func_get_analysis_data(**{
                'query': query,
            })
        return result
    
    def convert_domain_to_utc(self, domain):
        new_domain = []
        for dm in domain:
            # Check if dm is list
            if type(dm) == list and len(dm) == 3:
                field_name = dm[0]
                operator = dm[1]
                value = dm[2]
                for field in self.field_ids:
                    if field.field_name == field_name and field.field_type == 'datetime':
                        try:
                            datetime.fromisoformat(value)
                            value += ' 00:00:00'
                        except ValueError:
                            pass
                        value = self.convert_to_utc(value)
                    elif self.model_id and field.field_name == field_name:
                        model_field = self.env['ir.model.fields'].search([('model_id', '=', self.model_id.id), ('name', '=', field_name), ('ttype', '=', 'selection')], limit=1)
                        if model_field:
                            selection = self.env[self.model_id.model]._fields[field_name].selection
                            selection_inverse_dict = {v: k for k,v in selection}
                            if value in selection_inverse_dict:
                                value = selection_inverse_dict[value]
                new_domain.append([field_name, operator, value])
        return new_domain

    def convert_to_utc(self, datetime_string):
        utc_datetime_string = datetime_string
        if self._context.get('tz'):
            utc_datetime_string = datetime.strftime(pytz.timezone(self._context.get('tz')).localize(datetime.strptime(datetime_string, "%Y-%m-%d %H:%M:%S")).astimezone(pytz.utc), "%Y-%m-%d %H:%M:%S")
        return utc_datetime_string
    
    def field_format_query(self, field_name, field_type, field_format):
        query = '%s' % (field_name)
        if not field_format:
            return query
        if field_type in ('date', 'datetime'):
            date_format = {
                'year': 'YYYY',
                'month': 'MON YYYY',
                'week': 'DD MON YYYY',
                'day': 'DD MON YYYY',
            }
            if field_format in date_format:
                query = '''to_char(date_trunc('%s', %s), '%s')''' % (
                    field_format, field_name, date_format[field_format])
        return query

    def get_date_range_by_date_format(self, date_format):
        # Today
        start_date = datetime.today()
        end_date = datetime.today()

        if date_format == 'this_week':
            start_date = start_date - timedelta(days=start_date.weekday())
            end_date = start_date + timedelta(days=6)
        elif date_format == 'last_week':
            start_date = start_date - timedelta(days=7)
            start_date = start_date - timedelta(days=start_date.weekday())
            end_date = start_date + timedelta(days=6)
        elif date_format == 'last_10':
            start_date = start_date - timedelta(days=10)
        elif date_format == 'last_30':
            start_date = start_date - timedelta(days=30)
        elif date_format == 'last_60':
            start_date = start_date - timedelta(days=60)
        elif date_format == 'before_today':
            start_date = start_date.replace(year=start_date.year - 50)
            end_date = end_date - timedelta(days=1)
        elif date_format == 'after_today':
            start_date = start_date + timedelta(days=1)
            end_date = end_date.replace(year=end_date.year + 50)
        elif date_format == 'before_and_today':
            start_date = start_date.replace(year=start_date.year - 50)
        elif date_format == 'today_and_after':
            end_date = end_date.replace(year=end_date.year + 50)
        elif date_format == 'this_month':
            start_date = start_date.replace(day=1)
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)
        elif date_format == 'mtd':
            start_date = start_date.replace(day=1)
            end_date = datetime.today()
        elif date_format == 'last_month':
            start_date = start_date.replace(day=1) - timedelta(days=1)
            start_date = start_date.replace(day=1)
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)
        elif date_format == 'last_two_months':
            next_month = start_date.replace(day=28) + timedelta(days=4)
            start_date = start_date.replace(day=1) - timedelta(days=1)
            start_date = start_date.replace(day=1)
            end_date = next_month - timedelta(days=next_month.day)
        elif date_format == 'last_three_months':
            next_month = start_date.replace(day=28) + timedelta(days=4)
            start_date = start_date.replace(day=1) - timedelta(days=1)
            start_date = start_date.replace(day=1) - timedelta(days=1)
            start_date = start_date.replace(day=1)
            end_date = next_month - timedelta(days=next_month.day)
        elif date_format == 'this_year':
            start_date = start_date.replace(day=1, month=1)
            end_date = end_date.replace(day=31, month=12)
        elif date_format == 'ytd':
            start_date = start_date.replace(day=1, month=1)
            end_date = datetime.today()
        elif date_format == 'last_year':
            start_date = start_date - relativedelta(years=1)
            start_date = start_date.replace(day=1, month=1)
            end_date = start_date.replace(day=31, month=12)

        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")
        start_datetime = start_date + ' 00:00:00'
        end_datetime = end_date + ' 23:59:59'

        return {
            'start_date': start_date,
            'end_date': end_date,
            'start_datetime': start_datetime,
            'end_datetime': end_datetime,
        }
    
    def get_filter_temp_query_model(self, filter):
        self.ensure_one()
        domain = []
        filter_field = filter[0]
        filter_type = filter[1]
        filter_list = filter[2]

        if filter_type == 'string_search':
            if filter_list:
                domain = [(filter_field, 'in', filter_list)]

        elif filter_type == 'date_range':
            if filter_list and len(filter_list) == 2:
                if filter_list[0]:
                    domain.append((filter_field, '>=', filter_list[0]))
                if filter_list[1]:
                    domain.append((filter_field, '<=', filter_list[1]))

        elif filter_type == 'date_format':
            if filter_list:
                date_format = filter_list[0]
                date_range = self.get_date_range_by_date_format(date_format)
                start_date = date_range.get('start_date')
                end_date = date_range.get('end_date')
                domain = [(filter_field, '>=', start_date), (filter_field, '<=', end_date)]

        return domain

    def run_data_script(self):
        self.ensure_one()
        res = {}
        try:
            if self.method == 'table':
                if self.table_id and self.table_id.cron_id:
                    res = {
                        'code': 200,
                        'response': self.table_id.cron_id.with_context(izi_table=self.table_id).method_direct_trigger(),
                    }
            elif self.method == 'data_script':
                if self.server_action_id:
                    res = {
                        'code': 200,
                        'response': self.server_action_id.run(),
                    }
        except Exception as e:
            res = {
                'code': 500,
                'message': str(e),
            }
        return res

class IZIAnalysisMetric(models.Model):
    _name = 'izi.analysis.metric'
    _description = 'IZI Analysis Metric'
    _order = 'sequence,id'

    sequence = fields.Integer('Sequence')
    analysis_id = fields.Many2one('izi.analysis', string='Analysis', required=True, ondelete='cascade')
    table_id = fields.Many2one('izi.table', string='Table', related='analysis_id.table_id')
    field_id = fields.Many2one('izi.table.field', string='Field', required=True, domain=[('field_type', 'in', ('numeric', 'number'))])
    field_type = fields.Char('Field Type', related='field_id.field_type')
    name = fields.Char('Name', related='field_id.name', store=True)
    name_alias = fields.Char(string="Alias")
    calculation = fields.Selection([
        ('count', 'Count'),
        ('sum', 'Sum'),
        ('avg', 'Avg'),
        ('csum', 'Cumulative Sum'),
    ], string='Calculation', required=True, default='sum')
    sort = fields.Selection([
        ('asc', 'Ascending'),
        ('desc', 'Descending'),
    ], string='Sort', required=False, default=False)
    prefix = fields.Char('Prefix')
    suffix = fields.Char('Suffix')
    locale_code = fields.Char('Locale Code', default='en-US')
    decimal_places = fields.Integer('Decimal Places', default=0)

    @api.onchange('field_id')
    def onchange_field_id(self):
        for metric in self:
            for sort in metric.analysis_id.sort_ids:
                if sort.field_id == metric._origin.field_id:
                    raise ValidationError(
                        'This metric field is used to sorting the analysis! Please remove the sort that using this'
                        + ' field and try to change this metric field again!')

    @api.onchange('calculation')
    def onchange_calculation(self):
        for metric in self:
            for sort in metric.analysis_id.sort_ids:
                if sort.field_id == metric._origin.field_id:
                    raise ValidationError(
                        'This metric field is used to sorting the analysis! Please remove the sort that using this'
                        + ' field and try to change this metric field again!')

class IZIAnalysisDrilldownDimension(models.Model):
    _name = 'izi.analysis.drilldown.dimension'
    _description = 'IZI Analysis Drilldown Demension'
    _order = 'sequence'

    sequence = fields.Integer('Sequence')
    analysis_id = fields.Many2one('izi.analysis', string='Analysis', required=True, ondelete='cascade')
    table_id = fields.Many2one('izi.table', string='Table', related='analysis_id.table_id')
    field_id = fields.Many2one('izi.table.field', string='Field', required=True, domain=[('field_type', 'not in', ('numeric', 'number'))])
    field_type = fields.Char('Field Type', related='field_id.field_type')
    field_format = fields.Selection(selection=[
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('quarter', 'Quarter'),
        ('year', 'Year'),
    ], string='Field Format')
    name = fields.Char('Name', related='field_id.name', store=True)
    name_alias = fields.Char(string="Alias")
    sort = fields.Selection([
        ('asc', 'Ascending'),
        ('desc', 'Descending'),
    ], string='Sort', required=False, default=False)

class IZIAnalysisDimension(models.Model):
    _name = 'izi.analysis.dimension'
    _description = 'IZI Analysis Demension'
    _order = 'sequence,id'

    sequence = fields.Integer('Sequence')
    analysis_id = fields.Many2one('izi.analysis', string='Analysis', required=True, ondelete='cascade')
    table_id = fields.Many2one('izi.table', string='Table', related='analysis_id.table_id')
    field_id = fields.Many2one('izi.table.field', string='Field', required=True, domain=[('field_type', 'not in', ('numeric', 'number'))])
    field_type = fields.Char('Field Type', related='field_id.field_type')
    field_format = fields.Selection(selection=[
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('quarter', 'Quarter'),
        ('year', 'Year'),
    ], string='Field Format')
    name = fields.Char('Name', related='field_id.name', store=True)
    name_alias = fields.Char(string="Alias")
    sort = fields.Selection([
        ('asc', 'Ascending'),
        ('desc', 'Descending'),
    ], string='Sort', required=False, default=False)

    @api.onchange('field_id')
    def onchange_field_id(self):
        for dimension in self:
            if dimension.field_type not in ['date', 'datetime']:
                dimension.field_format = False
            for sort in dimension.analysis_id.sort_ids:
                if sort.field_id == dimension._origin.field_id:
                    raise ValidationError(
                        'This dimension field is used to sorting the analysis! Please remove the sort that using this'
                        + ' field and try to change this dimension field again!')

    @api.onchange('field_format')
    def onchange_field_format(self):
        for dimension in self:
            for sort in dimension.analysis_id.sort_ids:
                if sort.field_id == dimension._origin.field_id:
                    raise ValidationError(
                        'This dimension field is used to sorting the analysis! Please remove the sort that using this'
                        + ' field and try to change this dimension field again!')


class IZIAnalysisFilterTemp(models.Model):
    _name = 'izi.analysis.filter.temp'
    _description = 'IZI Analysis Filter Temp'

    analysis_id = fields.Many2one('izi.analysis', string='Analysis', required=True, ondelete='cascade')
    table_id = fields.Many2one('izi.table', string='Table', related='analysis_id.table_id')
    field_id = fields.Many2one('izi.table.field', string='Field', required=True, ondelete='cascade')
    field_type = fields.Char('Field Type', related='field_id.field_type')
    type = fields.Selection(selection=[
        ('string_search', 'String Search'),
        ('date_range', 'Date Range'),
        ('date_format', 'Date Format'),
    ], string='Filter Type')
    name = fields.Char('Name', related='field_id.name', store=True)


class IZIAnalysisFilter(models.Model):
    _name = 'izi.analysis.filter'
    _description = 'IZI Analysis Filter'
    _order = 'id'

    analysis_id = fields.Many2one('izi.analysis', string='Analysis', required=True, ondelete='cascade')
    table_id = fields.Many2one('izi.table', string='Table', related='analysis_id.table_id')
    source_id = fields.Many2one('izi.data.source', string='Data Source', related='analysis_id.source_id')
    source_type = fields.Selection(string='Data Source Type', related='analysis_id.source_id.type')
    field_id = fields.Many2one('izi.table.field', string='Field', required=True, ondelete='cascade')
    operator_id = fields.Many2one(comodel_name='izi.analysis.filter.operator', string='Operator', required=True)
    field_type = fields.Char(string='Field Type', related='field_id.field_type')
    value = fields.Char(string='Value', required=True)
    open_bracket = fields.Boolean(string='Open Bracket')
    close_bracket = fields.Boolean(string='Close Bracket')
    condition = fields.Selection(string='Condition', selection=[
        ('and', 'AND'),
        ('or', 'OR'),
    ], required=True)


class IZIAnalysisFilterOperator(models.Model):
    _name = 'izi.analysis.filter.operator'
    _description = 'IZI Analysis Filter Operator'
    _order = 'id'

    name = fields.Char(string='Name')
    source_type = fields.Selection([], string='Source Type')


class IZIAnalysisSort(models.Model):
    _name = 'izi.analysis.sort'
    _description = 'IZI Analysis Sort'
    _order = 'id'

    sequence = fields.Integer(string='Sequence')
    analysis_id = fields.Many2one(comodel_name='izi.analysis', string='Analysis', required=True, ondelete='cascade')
    table_id = fields.Many2one(comodel_name='izi.table', string='Table', related='analysis_id.table_id')
    source_id = fields.Many2one(comodel_name='izi.data.source', string='Data Source', related='analysis_id.source_id')
    source_type = fields.Selection(string='Data Source Type', related='analysis_id.source_id.type')
    field_id = fields.Many2one(comodel_name='izi.table.field', string='Field', required=True)
    field_type = fields.Char(string='Field Type', related='field_id.field_type')
    metric_id = fields.Many2one(comodel_name='izi.analysis.metric', string='Metric', ondelete='cascade')
    dimension_id = fields.Many2one(comodel_name='izi.analysis.dimension', string='Dimension', ondelete='cascade')
    field_format = fields.Selection(string='Field Format', related='dimension_id.field_format')
    field_calculation = fields.Selection(string='Field Calculation', related='metric_id.calculation')
    sort = fields.Selection(string='Sort', selection=[
        ('asc', 'Ascending'),
        ('desc', 'Descending'),
    ], default='asc', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            analysis_id = self.env['izi.analysis'].browse(vals.get('analysis_id'))
            for dimension in analysis_id.dimension_ids:
                if dimension.field_id.id == vals.get('field_id'):
                    vals['dimension_id'] = dimension.id
                    break
            for metric in analysis_id.metric_ids:
                if metric.field_id.id == vals.get('field_id'):
                    vals['metric_id'] = metric.id
                    break
        recs = super(IZIAnalysisSort, self).create(vals_list)
        return recs
