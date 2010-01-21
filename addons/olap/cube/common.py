import sqlalchemy
from sqlalchemy import *
import common

def measure_sql_exp_col(metadata,col):
    temp = col.split(".")
    table_name =  filter(lambda x: x.name==temp[0],metadata.table_iterator(reverse=False))
    if table_name:
        if not col  in table_name[0].c:
            col = sqlalchemy.Column(temp[1], sqlalchemy.Float)
            table_name[0].append_column(col)
            return col
        else:
            for k in table_name[0].c:
                if temp[1] == k.name:
                    return k
    else:
        print "The table %s  do not exist or match to cube fact table"%(temp[0])
# To be Improved
# I am sure it exist something better in SA
def col_get(table, col_obj):
#   table = sqlalchemy table object
#   level = level object

    # Check for the columns
    
    datatypes = {
        'timestamp': sqlalchemy.DateTime,
        'timestampz': sqlalchemy.DateTime,
        'numeric': sqlalchemy.Numeric,
        'int': sqlalchemy.Integer,
        'float8': sqlalchemy.Float,
        'varchar': sqlalchemy.String,
        'bool': sqlalchemy.Boolean,
        'bytea':'Byte A', # Not Clear 
        'int2':sqlalchemy.SmallInteger,
        'int4':sqlalchemy.Integer,
        'int8':sqlalchemy.Integer,
        'text':sqlalchemy.String,
        'date':sqlalchemy.Date,
        'time': sqlalchemy.Time,
        'number':sqlalchemy.Numeric,
    }
    if not  ('.').join([col_obj.table_id.table_db_name,col_obj.column_db_name]) in table.c:
        col = sqlalchemy.Column(col_obj.column_db_name, datatypes[col_obj.type])
        table.append_column(col)
        return col
    else:
        for k in table.c:
            if col_obj.column_db_name == k.name:
                return k

def get_primary_key(table):
    for cols in table.columns:
        if cols.primary_key == True:
            return cols


# It gets the olap_cube_table browse object
def table_get(metadata, table):
    result = False
    table1 = False
    table2 = False
    if table.line_ids:
        temp = 0
        for i in range(len(table.line_ids)):
            table1 = sqlalchemy.Table(table.line_ids[i].table_id.table_db_name,metadata)
            pk = get_primary_key(table.line_ids[i].table_id)
            if result:
                
                result = join(result,table1, onclause=col_get(table1,pk)==col_get(table2,table.line_ids[i-1].field_id))
            elif table2:
                result = join(table1, table2, onclause=col_get(table1,pk)==col_get(table2,table.line_ids[i-1].field_id))
            else:
                table2=table1
            temp=i
            
        if not result:
            result = table1
        pk = get_primary_key(table.line_ids[temp].table_id)
        tab = sqlalchemy.Table(table.line_ids[temp].field_id.related_to.table_db_name,metadata)
        result = join(result, tab,onclause=col_get(tab,pk)
                 ==col_get(sqlalchemy.Table(table.line_ids[temp].table_id.table_db_name,metadata),table.line_ids[temp].field_id))
                 
    else:
        if table.column_link_id.related_to:
            result = sqlalchemy.Table(table.column_link_id.related_to.table_db_name,metadata)
        else:
            result = sqlalchemy.Table(table.column_link_id.table_id.table_db_name,metadata)

    return result

def xcombine(*seqin):
    """
        Cartesian product of the list of list that produce all distinct
        subsets of my query.
    """
    def rloop(seqin,comb):
        '''recursive looping function'''
        if seqin:
            for item in seqin[0]:
                newcomb=comb+[item]
                for item in rloop(seqin[1:],newcomb):
                    yield item
        else:
            yield comb
    return rloop(seqin, [])

# vim: ts=4 sts=4 sw=4 si et
