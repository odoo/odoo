# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
import ast
import json
from psycopg2 import extensions
from datetime import datetime, timedelta
import psycopg2
import math
import random
import pandas

_logger = logging.getLogger(__name__)

class IZITools(models.TransientModel):
    _name = 'izi.tools'
    _description = 'IZI Tools'

    @api.model
    def lib(self, key):
        lib = {
           'json': json,
           'datetime': datetime,
           'timedelta': timedelta,
           'psycopg2': psycopg2,
           'math': math,
           'random': random,
           'pandas': pandas,
           'models': models,
           'fields': fields,
           'api': api,
        }
        if key not in lib:
            raise UserError('Library Not Found')
        return lib[key]

    def check_su(self):
        if not (self.user_has_groups('base.group_system') or self.env.su):
            raise UserError('Access Restricted Only For Odoo Administrator!')
    
    def get_db_cursor(self, dbtype, kwargs):
        self.check_su()
        if dbtype == 'psql':
            try:
                conn = psycopg2.connect(**kwargs)
                cur = conn.cursor()
                return cur
            except Exception as e:
                raise ValidationError(e)
        return False
        
    @api.model
    def alert(self, message):
        raise UserError(message)

    @api.model
    def log(self, message):
        _logger.info('IZI_TOOLS_LOGGER > ' + message)

    @api.model
    def literal_eval(self, data):
        self.check_su()
        return ast.literal_eval(data)
    
    @api.model
    def query_insert(self, table_name, data, return_id=False):
        self.check_su()
        if type(data) is not dict:
            raise UserError('Data must be in dictionary!')
        insert_query = 'INSERT INTO %s (%s) VALUES %s'
        if return_id:
            insert_query += ' RETURNING id'
        insert_query = self.env.cr.mogrify(insert_query, (extensions.AsIs(table_name), extensions.AsIs(
            ','.join(data.keys())), tuple(data.values())))
        self.env.cr.execute(insert_query)
        new_id = False
        if return_id:
            new_id = self.env.cr.fetchone()[0]
        return new_id
    
    @api.model
    def query_check(self, query):
        self.check_su()
        self.env.cr.execute(query)
        res = self.env.cr.dictfetchall()
        raise UserError('''
            Total Rows: %s
            Query Results:
            
            %s
        ''' % (len(res), str(res)))
    
    @api.model
    def query_fetch(self, query):
        self.check_su()
        try:
            self.env.cr.execute(query)
        except Exception as e:
            self.env.cr.rollback()
            raise UserError(str(e))
        return self.env.cr.dictfetchall()
    
    @api.model
    def query_execute(self, query, check=False):
        self.check_su()
        if 'UPDATE' in query.upper() or 'DELETE' in query.upper():
            if 'WHERE' not in query.upper():
                raise UserError('YOUR QUERY DO NOT HAVE WHERE CLAUSE. IT IS VERY DANGEROUS!')
        self.env.cr.execute(query)
        if check:
            res = self.env.cr.dictfetchall()
            raise UserError('''
                Total Rows: %s
                Query Results:
                
                %s
            ''' % (len(res), str(res)))
