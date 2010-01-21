import sqlalchemy
from olap.cube import common
from olap.cube import axis_map
from level_interface import level_interface

class level_normal(level_interface):
    def run(self, level, metadata, table):
        col = common.col_get(sqlalchemy.Table(level.object.table_name,metadata), level.object.column_name)
        col_id = common.col_get(sqlalchemy.Table(level.object.table_name,metadata), level.object.column_name)
        result = {
                  'column': [col_id],
                  'column_name': [col],
                  'axis_mapping': [axis_map.column_mapping],
                  'where_clause': [col_id == level.name ]
                  }
        return result

    def children(self, level, metadata, table):
        col = common.col_get(sqlalchemy.Table(level.object.table_name,metadata), level.object.column_name)
        col_id = common.col_get(sqlalchemy.Table(level.object.table_name,metadata), level.object.column_name)
        result = {
                  'column': [col_id],
                  'column_name': [col],
                  'axis_mapping': [axis_map.column_mapping],
                  'where_clause': []
                  }
        return result

    def validate(self, level, name):
        return 1

# vim: ts=4 sts=4 sw=4 si et
