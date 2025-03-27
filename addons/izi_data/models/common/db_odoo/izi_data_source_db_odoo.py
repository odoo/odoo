# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class IZIDataSourceDBOdoo(models.Model):
    _inherit = 'izi.data.source'

    type = fields.Selection(
        selection_add=[
            ('db_odoo', 'Database Odoo'),
        ])

    @api.model
    def create_source_db_odoo(self):
        if not self.search([('type', '=', 'db_odoo')], limit=1):
            data_source = self.create({
                'name': 'Odoo',
                'type': 'db_odoo'
            })
            data_source.get_source_tables()
        return True

    def get_cursor_db_odoo(self):
        return self.env.cr

    def close_cursor_db_odoo(self, cursor):
        pass

    def get_schema_db_odoo(self):
        return 'public'

    def dictfetchall_db_odoo(self, cursor):
        return cursor.dictfetchall()

    def authenticate_db_odoo(self):
        self.ensure_one()
        self.state = 'ready'

    def get_foreignkey_field_db_odoo(self):
        self.ensure_one()

        cursor = self.get_cursor_db_odoo()
        schema_name = self.get_schema_db_odoo()

        # Get Foreign Key Field
        cursor.execute('''
            SELECT
                kcu.table_schema,
                kcu.constraint_name,
                kcu.table_name,
                kcu.column_name,
                ccu.table_schema foreign_table_schema,
                ccu.table_name foreign_table_name,
                ccu.column_name foreign_column_name
            FROM
                information_schema.key_column_usage kcu
            JOIN information_schema.table_constraints tc ON
                (kcu.constraint_name = tc.constraint_name AND kcu.table_schema = tc.table_schema)
            JOIN information_schema.constraint_column_usage ccu ON
                (kcu.constraint_name = ccu.constraint_name AND kcu.table_schema = ccu.table_schema)
            WHERE
                tc.constraint_type = 'FOREIGN KEY'
                AND kcu.table_schema = '{schema_name}'
                AND ccu.table_schema = '{schema_name}'
        '''.format(schema_name=schema_name))
        fkey_records = self.dictfetchall_db_odoo(cursor)
        fkey_by_table_column = {}
        for fkey in fkey_records:
            fkey_by_table_column['%s,%s' % (fkey.get('table_name'), fkey.get('column_name'))] = fkey

        return fkey_by_table_column

    def get_source_tables_db_odoo(self, **kwargs):
        self.ensure_one()

        Table = self.env['izi.table']
        Field = self.env['izi.table.field']

        table_by_name = kwargs.get('table_by_name')
        field_by_name = kwargs.get('field_by_name')

        # Get Tables
        domain = [('transient', '=', False)]
        if self.table_filter:
            table_filters = self.table_filter.split(',')
            table_filters = [tf.strip().replace('_', '.') for tf in table_filters]
            domain.append(('model', 'in', table_filters))
        models = self.env['ir.model'].search(domain)
        for model in models:
            table_name = model.model.replace('.', '_')
            table_desc = model.name

            # Create or Get Tables
            # Commented Out To Get All Tables Including Table View
            # self.env.cr.execute('''
            #     SELECT FROM 
            #         pg_tables
            #     WHERE 
            #         tablename  = '%s'
            #     ''' % (table_name));
            # if not self.env.cr.fetchall():
            #     continue
            table = table_by_name.get(table_name)
            if table_name not in table_by_name:
                table = Table.create({
                    'active': True,
                    'name': table_desc,
                    'table_name': table_name,
                    'source_id': self.id,
                    'is_stored': False,
                    'user_defined': False,
                    'model_id': model.id,
                })
                field_by_name[table_name] = {}
            else:
                table.write({
                    'active': True,
                    'name': table_desc,
                    'table_name': table_name,
                    'source_id': self.id,
                    'is_stored': False,
                    'user_defined': False,
                    'model_id': model.id,
                })
                table_by_name.pop(table_name)
            
            # Get Fields
            field_type_mapping = {
                'datetime': 'datetime',
                'boolean': 'boolean',
                'monetary': 'number',
                'char': 'string',
                'many2one': 'foreignkey',
                'integer': 'number',
                'one2many': 'foreignkey',
                'many2many': 'foreignkey',
                'date': 'date',
                'selection': 'string',
                'text': 'string',
                'float': 'number',
                'binary': 'byte',
            }
            for field in model.field_id:
                title = field.field_description
                field_name = field.name
                ttype = field.ttype
                if ttype not in field_type_mapping:
                    continue
                field_type = field_type_mapping[ttype]
                foreign_table = False
                foreign_column = False
                if ttype == 'many2one':
                    foreign_table = field.relation
                    foreign_column = 'id'
                # Skip One2Many Many2Many
                elif ttype in ('many2many', 'one2many'):
                    continue
                # Skip Computed Field
                if not field.store:
                    continue

                if field_name not in field_by_name[table_name]:
                    field = Field.create({
                        'name': title,
                        'field_name': field_name,
                        'field_type': field_type,
                        'field_type_origin': ttype,
                        'table_id': table.id,
                        'foreign_table': foreign_table,
                        'foreign_column': foreign_column,
                    })
                else:
                    field = field_by_name[table_name][field_name]
                    field.write({
                        'name': title,
                        'field_name': field_name,
                        'field_type': field_type,
                        'field_type_origin': ttype,
                        'table_id': table.id,
                        'foreign_table': foreign_table,
                        'foreign_column': foreign_column,
                    })
                    field_by_name[table_name].pop(field_name)

        return {
            'table_by_name': table_by_name,
            'field_by_name': field_by_name
        }

    def get_source_fields_db_odoo(self, **kwargs):
        self.ensure_one()
        raise ValidationError('')

    def check_query_db_odoo(self, **kwargs):
        query = kwargs.get('query')
        if query is False or query is None:
            return True

        escape_characters = ['\"', '\'', '\\', '\n', '\r', '\t', '\b', '\f']
        for char in escape_characters:
            query = query.replace(char, ' ')
        query = " ".join(query.split()).lower()

        forbidden_queries = ['drop database', 'drop schema', 'drop table', 'truncate table', 'delete from',
                             'delete user', 'select true', 'insert into', 'create table']
        for forbidden_query in forbidden_queries:
            if forbidden_query in query.lower():
                raise ValidationError("Query is not allowed to contain '%s'" % forbidden_query)

    def get_source_query_filters_db_odoo(self):
        self.ensure_one()
        table_filter_query = ''
        if self.table_filter:
            table_filters = []
            for table_filter in self.table_filter.split(','):
                table_filters.append('$$%s$$' % table_filter)
            table_filter_query = ','.join(table_filters)
            table_filter_query = 'AND table_name IN (%s)' % table_filter_query
        return table_filter_query
