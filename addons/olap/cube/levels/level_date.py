
import sqlalchemy
from level_interface import level_interface

from olap.cube import common
from olap.cube import axis_map

#
# To Be Fixed:
#   Mapping of QX and Month
#

class level_date_month(level_interface):
    def run(self, level, metadata, table):
        col = common.col_get(sqlalchemy.Table(level.object.table_name,metadata), level.object.column_name)
        col_id = common.col_get(sqlalchemy.Table(level.object.table_name,metadata), level.object.column_name)
        result = {
            'column': [sqlalchemy.func.date_part('month',col_id)],
            'column_name': [sqlalchemy.func.date_part('month', col)],
            'axis_mapping': [axis_map.column_mapping],
            'where_clause': [sqlalchemy.func.date_part('month',col_id) == level.name]
        }
        return result

    def children(self, level, metadata, table):
        col = common.col_get(sqlalchemy.Table(level.object.table_name,metadata), level.object.column_name)
        col_id = common.col_get(sqlalchemy.Table(level.object.table_name,metadata), level.object.column_name)
        qexpr = sqlalchemy.literal('Q')+ sqlalchemy.sql.cast(sqlalchemy.func.date_part('QUARTER',col_id), sqlalchemy.types.String) + sqlalchemy.sql.cast(sqlalchemy.func.date_part('month',col_id),sqlalchemy.types.String)
        return  {
            'column': [sqlalchemy.func.date_part('month',col)],
            'column_name':[sqlalchemy.func.date_part('month',col)],
            'axis_mapping': [axis_map.column_mapping]
        }

    def validate(self, level, name):
        
        return 1

class level_date_year(level_interface):
    def run(self, level, metadata, table):
        col = common.col_get(sqlalchemy.Table(level.object.table_name,metadata),level.object.column_name)
        col_id = common.col_get(sqlalchemy.Table(level.object.table_name,metadata), level.object.column_name)
        result = {
            'column': [sqlalchemy.func.date_part('year',col_id)],
            'column_name': [sqlalchemy.func.date_part('year', col)],
            'axis_mapping': [axis_map.column_mapping],
            'where_clause': [sqlalchemy.func.date_part('year',col_id) == level.name]
        }
        return result

    def children(self, level, metadata, table):
        col = common.col_get(sqlalchemy.Table(level.object.table_name,metadata), level.object.column_name)
        col_id = common.col_get(sqlalchemy.Table(level.object.table_name,metadata), level.object.column_name)
        return  {
            'column': [sqlalchemy.func.date_part('year',col_id)],
            'column_name':[sqlalchemy.func.date_part('year',col)],
            'axis_mapping': [axis_map.column_mapping],
            'where_clause':[]
        }

    def validate(self, level, name):
        return 1

#
# To Do: Create your own axis mapping
#
class level_date_quarter(level_interface):

    def run(self, level, metadata, table):
        quarters = {
            'Q1': [1,2,3],
            'Q2': [4,5,6],
            'Q3': [7,8,9],
            'Q4': [10,11,12]
            }
        col = common.col_get(sqlalchemy.Table(level.object.table_name,metadata), level.object.column_name)
        col_id = common.col_get(sqlalchemy.Table(level.object.table_name,metadata), level.object.column_name)
        qexpr = sqlalchemy.literal('Q')+ sqlalchemy.sql.cast(sqlalchemy.func.date_part('QUARTER',col_id), sqlalchemy.types.String)
        if not level.name in quarters:
            raise 'Quarter should be in Q1,Q2,Q3,Q4 !'

        result = {
            'column': [qexpr],
            'column_name': [qexpr],
            'axis_mapping': [axis_map.column_static],
            'where_clause': [
                (sqlalchemy.func.date_part('month',col_id)==quarters[level.name][0]) |
                (sqlalchemy.func.date_part('month',col_id)==quarters[level.name][1]) |
                (sqlalchemy.func.date_part('month',col_id)==quarters[level.name][2])
            ]
        }
        return result



    def children(self, level, metadata, table):
        table = sqlalchemy.Table(level.object.table_name, metadata)
        col =common.col_get(table, level.object.column_name)
        col_id = common.col_get(table,level.object.column_name)
        qexpr = sqlalchemy.literal('Q')+ sqlalchemy.sql.cast(sqlalchemy.func.date_part('QUARTER',col_id), sqlalchemy.types.String)
        return  {
            'column': [qexpr],
            'column_name': [qexpr],
            'axis_mapping': [axis_map.column_mapping_value]
        }

    def validate(self, level, name):
        return 1
# vim: ts=4 sts=4 sw=4 si et
