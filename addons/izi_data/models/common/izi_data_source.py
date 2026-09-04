# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
from odoo import models, fields, api


class IZIDataSourceItem(models.Model):
    _name = 'izi.data.source.item'
    _description = 'IZI Data Source Item'

    name = fields.Char(string='Name', required=True)
    type = fields.Selection(string='Type', selection=[], required=True)
    table_id = fields.Many2one('izi.table', string='Table')
    source_id = fields.Many2one('izi.data.source', string='Data Source')
    limit = fields.Integer('Limit', default=10000)
    action_to_field = fields.Selection(string='Action to Fields', selection=[
        ('replace', 'Replace Existing Fields'),
        ('map', 'Map New Fields To Existing'),
        ('add', 'Add New Fields'),
    ], required=True, default='replace')
    # status = 'active', 'inactive'
    # field_ids = Fields From Source Item
    # field_map_ids = Fields Mapping, From Source Item to Table Fields

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._context.get('table_id', False):
            table_id = self._context.get('table_id')
            table = self.env['izi.table'].browse(table_id)
            action_to_field = 'replace'
            if table.field_ids:
                action_to_field = 'map'
            res['action_to_field'] = action_to_field
            res['table_id'] = table_id
            res['name'] = table.name
            if table.source_id:
                res['source_id'] = table.source_id.id
        else:
            source = self.env['izi.data.source'].search([], limit=1)
            if source:
                res['source_id'] = source.id
        return res

    def process_data(self):
        return True

class IZIDataSource(models.Model):
    _name = 'izi.data.source'
    _description = 'IZI Data Source'

    name = fields.Char(string='Name', required=True)
    type = fields.Selection(string='Type', selection=[])
    table_ids = fields.One2many(comodel_name='izi.table', inverse_name='source_id', string='Tables')
    table_filter = fields.Char('Table Filter')
    state = fields.Selection(selection=[('new', 'New'), ('ready', 'Ready')], default='new', string='State')
    item_ids = fields.One2many(comodel_name='izi.data.source.item', inverse_name='source_id', string='Sources')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Data Source Name Already Exist.')
    ]

    def authenticate(self):
        func_authenticate = getattr(self, 'authenticate_%s' % self.type)
        return func_authenticate()

    def get_source_tables(self):
        self.ensure_one()

        Table = self.env['izi.table']
        Field = self.env['izi.table.field']

        # Get existing table and field
        table_by_name = {}
        field_by_name = {}
        for izi_table in Table.search([('source_id', '=', self.id), ('model_id', '!=', False)]):
            table_name = izi_table.table_name
            if table_name is False:
                table_name = izi_table.store_table_name
            table_by_name[table_name] = izi_table
            field_by_name[table_name] = {}
            for izi_field in Field.search([('table_id', '=', izi_table.id)]):
                field_by_name[table_name][izi_field.field_name] = izi_field

        # Table Filter
        func_get_source_query_filters = getattr(self, 'get_source_query_filters_%s' % self.type)
        table_filter_query = func_get_source_query_filters()

        func_get_source_tables = getattr(self, 'get_source_tables_%s' % self.type)
        result = func_get_source_tables(**{
            'table_by_name': table_by_name,
            'field_by_name': field_by_name,
            'table_filter_query': table_filter_query,
        })

        table_by_name = result.get('table_by_name')
        field_by_name = result.get('field_by_name')

        for table_name in field_by_name:
            for field_name in field_by_name[table_name]:
                if not field_by_name[table_name][field_name].table_id.table_name:
                    continue
                for dimension in field_by_name[table_name][field_name].analysis_dimension_ids:
                    dimension.unlink()
                for metric in field_by_name[table_name][field_name].analysis_metric_ids:
                    metric.unlink()
                field_by_name[table_name][field_name].unlink()
        for table_name in table_by_name:
            if not table_by_name[table_name].table_name:
                table_by_name[table_name].get_table_fields()
                continue
            # table_by_name[table_name].unlink()

    def get_source_fields(self):
        self.ensure_one()

        Table = self.env['izi.table']
        Field = self.env['izi.table.field']

        # Table Filter
        table_filter_query = []
        if self.table_filter:
            for table_filter in self.table_filter.split(','):
                table_filter_query.append(table_filter)

        # Get existing table and field
        table_by_name = {}
        field_by_name = {}
        table_search_domain = [('source_id', '=', self.id), ]
        if table_filter_query:
            table_search_domain = [('source_id', '=', self.id), ('model_id', '!=', False), ('table_name', 'in', table_filter_query), ]
        for izi_table in Table.search(table_search_domain):
            table_name = izi_table.table_name
            if table_name is False:
                table_name = izi_table.store_table_name
            table_by_name[table_name] = izi_table
            field_by_name[table_name] = {}
            for izi_field in Field.search([('table_id', '=', izi_table.id)]):
                field_by_name[table_name][izi_field.field_name] = izi_field

        func_get_source_fields = getattr(self, 'get_source_fields_%s' % self.type)
        result = func_get_source_fields(**{
            'table_by_name': table_by_name,
            'field_by_name': field_by_name,
        })

        field_by_name = result.get('field_by_name')

        for table_name in field_by_name:
            for field_name in field_by_name[table_name]:
                if not field_by_name[table_name][field_name].table_id.table_name:
                    continue
                for dimension in field_by_name[table_name][field_name].analysis_dimension_ids:
                    dimension.unlink()
                for metric in field_by_name[table_name][field_name].analysis_metric_ids:
                    metric.unlink()
                field_by_name[table_name][field_name].unlink()
