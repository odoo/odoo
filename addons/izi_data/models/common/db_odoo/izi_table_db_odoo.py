# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
from odoo import models
from datetime import date, datetime
from odoo.exceptions import ValidationError


class IZITableDBOdoo(models.Model):
    _inherit = 'izi.table'

    def get_table_fields_db_odoo(self, **kwargs):
        self.ensure_one()
        izi_analysis_obj = self.env['izi.analysis']
        cursor = self.source_id.get_cursor_db_odoo()

        Field = self.env['izi.table.field']

        field_by_name = kwargs.get('field_by_name')
        table_query = kwargs.get('table_query')
        table_query = izi_analysis_obj.check_special_variable(table_query)
        # fkey_by_table_column = self.source_id.get_foreignkey_field_db_odoo()
        fkey_by_table_column = {}

        # Get mapping oid and field type FROM pg_type
        typ_by_oid = {}
        cursor.execute("SELECT oid, typname FROM pg_type")
        dict_typs = self.source_id.dictfetchall_db_odoo(cursor)
        for typ in dict_typs:
            typ_by_oid[typ.get('oid')] = typ.get('typname')

        try:
            if not self.is_query and not self.user_defined and self.table_name:
                cursor.execute('SELECT * FROM %s LIMIT 1' % self.table_name)
            else:
                cursor.execute('SELECT * FROM %s LIMIT 1' % table_query)
        except Exception as e:
            raise ValidationError('''Failed to create fields from the table. There are errors on your query. 
Errors: %s''' % (str(e)))
        # Get and loop column description with env.cr.description from query given above
        for desc in cursor.description:
            field_name = desc.name
            field_title = field_name.replace('_', ' ').title()
            field_type_origin = typ_by_oid.get(desc.type_code)
            field_type = Field.get_field_type_mapping(field_type_origin, self.source_id.type)
            foreign_table = None
            foreign_column = None
            if fkey_by_table_column.get('%s,%s' % (self.table_name, field_name)) is not None:
                fkey = fkey_by_table_column.get('%s,%s' % (self.table_name, field_name))
                field_type = 'foreignkey'
                foreign_table = fkey.get('foreign_table_name')
                foreign_column = fkey.get('foreign_column_name')

            # Check to create or update field
            if field_name not in field_by_name:
                field = Field.create({
                    'name': field_title,
                    'field_name': field_name,
                    'field_type': field_type,
                    'field_type_origin': field_type_origin,
                    'table_id': self.id,
                    'foreign_table': foreign_table,
                    'foreign_column': foreign_column,
                })
            else:
                field = field_by_name[field_name]
                if field.name != field_title or field.field_type_origin != field_type_origin or \
                        field.field_type != field_type:
                    field.name = field_title
                    field.field_type_origin = field_type_origin
                    field.field_type = field_type
                if fkey_by_table_column.get('%s,%s' % (self.table_name, field_name)) is not None:
                    if field.field_type != field_type or field.foreign_table != foreign_table or \
                            field.foreign_column != foreign_column:
                        field.field_type = field_type
                        field.foreign_table = foreign_table
                        field.foreign_column = foreign_column
                field_by_name.pop(field_name)

        self.source_id.close_cursor_db_odoo(cursor)

        return {
            'field_by_name': field_by_name
        }

    def get_table_datas_db_odoo(self, **kwargs):
        self.ensure_one()
        cursor = self.source_id.get_cursor_db_odoo()

        cursor.execute(kwargs.get('query'))
        res_data = self.source_id.dictfetchall_db_odoo(cursor)
        self.source_id.close_cursor_db_odoo(cursor)
        return {
            'data': res_data,
        }

    def get_data_query_db_odoo(self, **kwargs):
        self.ensure_one()
        cursor = self.source_id.get_cursor_db_odoo()

        cursor.execute(kwargs.get('query'))
        res_data = self.source_id.dictfetchall_db_odoo(cursor)
        self.source_id.close_cursor_db_odoo(cursor)
        return res_data

    def get_field_type_origin_db_odoo(self, **kwargs):
        self.ensure_one()
        value = kwargs.get('value')
        type_origin = 'varchar'
        if type(value) == bool:
            type_origin = 'boolean'
        elif self.check_if_datetime_format(value) or isinstance(value, datetime):
            type_origin = 'timestamp'
        elif self.check_if_date_format(value) or isinstance(value, date):
            type_origin = 'date'
        elif isinstance(value, int):
            type_origin = 'int4'
        elif isinstance(value, float):
            type_origin = 'float8'
        return type_origin
