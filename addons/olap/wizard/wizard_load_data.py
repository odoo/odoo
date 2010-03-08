##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
import psycopg2
import time

import wizard
import pooler
import netsvc

info = '''<?xml version="1.0"?>
<form string="Load Data">
    <label string="Your database structure has been correctly loaded"/>
</form>'''

form1 = '''<?xml version="1.0"?>

<form string="Load Database Structure">

    <label align="0.0" string="We will load the complete structure of the database by introspection,
     so that you will be able to work on it, and specify a better structure 
    according to your reporting needs." colspan="4" />
    <newline/>
    <label align="0.0" string="After having loaded the structure, you will be able to hide/show or 
    rename tables and columns to simplify end-users interface. The following database 
    will be loaded:" colspan="4"/>
    <field align="0.0" name='fact_table'/>
    <newline/>
    <field align="0.0" name='db_name' colspan="4"/>
</form>'''

field1 = {
    'fact_table': {'string':'Fact Name', 'type':'char','size':'64', 'required':True, 'readonly':True},
    'db_name': {'string':'Database Name', 'type':'char','size':'64', 'required':True, 'readonly':True},
}

def olap_db_connect(self,cr,uid,part,context={}):
    pool = pooler.get_pool(cr.dbname)
    lines=pool.get('olap.schema').browse(cr, uid, part['id'],context)
    id_db=lines.database_id.id
    type = lines.database_id.type
    db_name = lines.database_id.db_name
    tobj = pool.get('olap.database.tables')
    tcol = pool.get('olap.database.columns')
    if type == 'postgres':
        host = lines.database_id.db_host and "host=%s" % lines.database_id.db_host or ''
        port = lines.database_id.db_port and "port=%s" % lines.database_id.db_port or ''
        name = lines.database_id.db_name and "dbname=%s" % lines.database_id.db_name or ''
        user = lines.database_id.db_login and "user=%s" % lines.database_id.db_login or ''
        password = lines.database_id.db_password and "password=%s" % lines.database_id.db_password or ''
        tdb = psycopg2.connect('%s %s %s %s %s' % (host, port, name, user, password))
        cr_db = tdb.cursor()
        cr.execute('select table_db_name,id from olap_database_tables where fact_database_id=%d', (id_db,))
        tables = dict(cr.fetchall())
        tables_id = map(lambda x: str(tables[x]),tables)
        cols={}
        if tables_id:
            cr.execute('select column_db_name,id,table_id from olap_database_columns where table_id in (' + ','.join(tables_id) +')')
        else:
            cr.execute('select column_db_name,id,table_id from olap_database_columns')
      
        for data in cr.fetchall():
            cols[str(data[1])]=(data[0],int(data[2]))
            
        print 'Creating / Updating Tables...' 
        cr_db.execute("select table_name, table_catalog from INFORMATION_SCHEMA.tables as a where a.table_schema = 'public'")
        for table in cr_db.fetchall():
            val = {
                'fact_database_id':id_db,
                'table_db_name':table[0]
            }
           
            if table[0] in tables.keys():
                table_id=tobj.write(cr,uid,[tables[table[0]]], val, context)
            else:
                val['name']=table[0]
                tables[val['name']] = tobj.create(cr,uid,val, context)    
        print 'Creating / Updating Columns...' 
        cr_db.execute("""SELECT
                table_name, column_name, udt_name
            from
                INFORMATION_SCHEMA.columns
            WHERE table_schema = 'public'""")
        
        for col in cr_db.fetchall():
            val={
                'table_id': tables[col[0]],
                'column_db_name': col[1],
                'type': col[2],
            }
            
            id_made=filter(lambda x:(int(cols[x][1])==int(tables[col[0]])),cols)
            if col[1] in cols.keys() and col[0] in tables.keys()and id_made:
                col_id=tcol.write(cr,uid,cols[tables[str(col[0])]], val, context)
            else:
                val['name']=col[1]
                id_made = tcol.create(cr,uid,val, context)
                cols[str(id_made)] = (val['name'],int(val['table_id']))
        print 'Creating / Updating Constraints...' 
        cr_db.execute("""select 
                table_name,column_name 
            from 
                INFORMATION_schema.key_column_usage
            where 
                constraint_name in (
                            select constraint_name from INFORMATION_SCHEMA .table_constraints
                            where 
                                constraint_type = 'PRIMARY KEY')""")
        print "Updating the Primary Key Constraint" 
        for constraint in cr_db.fetchall():
            val={
                'primary_key':True
            }
            
            id_to_write=filter(lambda x:(int(cols[x][1])==int(tables[constraint[0]])and(constraint[1]==cols[x][0])),cols)
            col_id=tcol.write(cr,uid,int(id_to_write[0]),val,context) 
        print "Updating the Foreign key constraint" 
        cr_db.execute("""select 
                    constraint_name,table_name 
            from 
                INFORMATION_schema.constraint_column_usage 
            where
                constraint_name in (
                            select constraint_name from INFORMATION_SCHEMA.table_constraints 
                            where 
                                constraint_type = 'FOREIGN KEY')""")
        for_key=dict(cr_db.fetchall())
        
        cr_db.execute("""select 
                     table_name,column_name,constraint_name 
                 from 
                     INFORMATION_schema.key_column_usage
                 where 
                     constraint_name in (
                                 select constraint_name from INFORMATION_SCHEMA.table_constraints 
                                 where 
                                     constraint_type = 'FOREIGN KEY')""") 

        for constraint in cr_db.fetchall():
            val={
                'related_to':tables[for_key[constraint[2]]]
            }
            id_to_write=filter(lambda x:(int(cols[x][1])==int(tables[constraint[0]])and (constraint[1]==cols[x][0])),cols)
            col_id=tcol.write(cr,uid,int(id_to_write[0]),val,context) 
    
    
    elif type =='mysql':
        try:
            import MySQLdb
            host = lines.database_id.db_host or ''
            port = lines.database_id.db_port or ''
            db = lines.database_id.db_name or ''
            user = lines.database_id.db_login or ''
            passwd = lines.database_id.db_password or ''
            tdb = MySQLdb.connect(host = host,port = port, db = db, user = user, passwd = passwd)
            
        except Exception, e:
            raise osv.except_osv('MySQLdb Packages Not Installed.',e )
        
        cr_db = tdb.cursor()
        cr.execute('select table_db_name,id from olap_database_tables where fact_database_id=%d', (id_db,))
        tables = dict(cr.fetchall())
        tables_id = map(lambda x: str(tables[x]),tables)
        cols={}
        if tables_id:
            cr.execute('select column_db_name,id,table_id from olap_database_columns where table_id in (' + ','.join(tables_id) +')')
        else:
            cr.execute('select column_db_name,id,table_id from olap_database_columns')
        
        for data in cr.fetchall():
            cols[str(data[1])]=(data[0],int(data[2]))
        cr_db.execute("select table_name, table_catalog from INFORMATION_SCHEMA.tables where table_schema =%s",(db_name))
        
        for table in cr_db.fetchall():
            val = {
                'fact_database_id':id_db,
                'table_db_name':table[0]
            }
           
            if table[0] in tables.keys():
                table_id=tobj.write(cr,uid,[tables[table[0]]], val, context)
                
            else:
                val['name']=table[0]
                tables[val['name']] = tobj.create(cr,uid,val, context)
        cr_db.execute("""SELECT
                table_name, column_name, data_type
            from
                INFORMATION_SCHEMA.columns
            WHERE table_schema = %s""",(db_name))
        
        for col in cr_db.fetchall():
            
            val={
                'table_id': tables[col[0]],
                'column_db_name': col[1],
                'type': col[2],
            }
            
            id_made=filter(lambda x:(int(cols[x][1])==int(tables[col[0]])),cols)
            if col[1] in cols.keys() and col[0] in tables.keys()and id_made:
                col_id=tcol.write(cr,uid,cols[tables[str(col[0])]], val, context)
            else:
                val['name']=col[1]
                id_made = tcol.create(cr,uid,val, context)
                cols[str(id_made)] = (val['name'],int(val['table_id']))
       
        cr_db.execute("""select 
                REFERENCED_COLUMN_NAME,REFERENCED_TABLE_NAME,COLUMN_NAME,TABLE_NAME
            from 
                INFORMATION_schema.key_column_usage
            where table_schema= %s and 
                constraint_name in (
                            select constraint_name from INFORMATION_SCHEMA .table_constraints
                            where 
                                constraint_type in('PRIMARY KEY','FOREIGN KEY'))
                            """,(db_name)) 

        for constraint in cr_db.fetchall():
            
            if constraint[0]:
                val={
                     'related_to':tables[constraint[1]]
                     }
            else:
                
                val={
                     'primary_key':True
                     }
            id_to_write=filter(lambda x:(int(cols[x][1])==int(tables[constraint[3]])and(constraint[2]==cols[x][0])),cols)
            col_id=tcol.write(cr,uid,int(id_to_write[0]),val,context)  
    
    elif type == 'oracle':
        try:
            import cx_Oracle
            host = lines.database_id.db_host or ''
            port = lines.database_id.db_port or ''
            db = lines.database_id.db_name or ''
            user = lines.database_id.db_login.upper() or ''
            passwd = lines.database_id.db_password or ''
            tdb = cx_Oracle.connect(user, passwrd, host)
            
        except Exception, e:
                    raise osv.except_osv('cx_Oracle Packages Not Installed.',e )

        cr_db = tdb.cursor()
        cr.execute('select table_db_name,id from olap_database_tables where fact_database_id=%d', (id_db,))
        tables = dict(cr.fetchall())
        tables_id = map(lambda x: str(tables[x]),tables)
        cols={}
        if tables_id:
            cr.execute('select column_db_name,id,table_id from olap_database_columns where table_id in (' + ','.join(tables_id) +')')
        else:
            cr.execute('select column_db_name,id,table_id from olap_database_columns')
        
        for data in cr.fetchall():
            cols[str(data[1])]=(data[0],int(data[2]))

        cr_db.execute("select table_name from all_tables where owner =%s",(user))
        temp = cr_db.fetchall()
        for table in temp:
            val = {
                'fact_database_id':id_db,
                'table_db_name':table[0]
            }
            
            if table[0] in tables.keys():
                table_id=tobj.write(cr,uid,[tables[table[0]]], val, context)
                
            else:
                val['name']=table[0]
                tables[val['name']] = tobj.create(cr,uid,val, context)

        cr_db.execute("""SELECT
                table_name, column_name, data_type
            from
                all_tab_columns 
            WHERE owner = %s""",(user))
        temp = cr_db.fetchall()
        for col in temp:
            if col[2]=='NUMBER':
                type_col='numeric'
            elif col[2]=='DATE':
                type_col='date'
            elif col[2]=='VARCHAR2':
                type_col='varchar'
            else:
                type_col=col[2]
            val={
                'table_id': tables[col[0]],
                'column_db_name': col[1],
                'type': type_col,
            }
            
            id_made=filter(lambda x:(int(cols[x][1])==int(tables[col[0]])),cols)
            if col[1] in cols.keys() and col[0] in tables.keys()and id_made:
                col_id=tcol.write(cr,uid,cols[tables[str(col[0])]], val, context)
            else:
                val['name']=col[1]
                id_made = tcol.create(cr,uid,val, context)
                cols[str(id_made)] = (val['name'],int(val['table_id']))

        cr_db.execute("""select 
                table_name,column_name,constraint_name
            from 
                all_cons_columns
            where
                constraint_name in (
                            select constraint_name from all_constraints
                            where 
                                constraint_type = 'P' and owner= %s)
                            """,(user)) 
        temp = cr_db.fetchall()
        pk_table = {}        
        for constraint in temp:
            val={
                'primary_key' : True
            }
            pk_table[constraint[2]] = constraint[0]

            id_to_write=filter(lambda x : (int(cols[x][1])==int(tables[constraint[0]])and(constraint[1]==cols[x][0])),cols)
            col_id=tcol.write(cr,uid,int(id_to_write[0]),val,context)

        cr_db.execute("""select 
                        constraint_name,r_constraint_name from all_constraints
                            where 
                                constraint_type = 'R'  and owner = %s
                            """,(user))
        constraints_map={}
        for data in cr_db.fetchall():
            constraints_map[data[0]]=data[1]

        cr_db.execute("""select 
                table_name,column_name,constraint_name
            from 
                all_cons_columns
            where
                constraint_name in (
                            select constraint_name from all_constraints
                            where 
                                constraint_type = 'R' and owner = %s)
                            """,(user))
            

        temp = cr_db.fetchall()
        for constraint in temp:
            rel_constraint_name=constraints_map[constraint[2]]
            req_table = pk_table[rel_constraint_name]
            val={
                'related_to' : tables[req_table]
            }
            id_to_write=filter(lambda x:(int(cols[x][1])==int(tables[constraint[0]])and (constraint[1]==cols[x][0])),cols)
            col_id=tcol.write(cr,uid,int(id_to_write[0]),val,context)
            
    pooler.get_pool(cr.dbname).get('olap.fact.database').write(cr,uid,[id_db],{'loaded':True})
    wf_service = netsvc.LocalService('workflow')
    wf_service.trg_validate(uid, 'olap.schema', part['id'], 'dbload', cr)
    return {}

def _getdata(self,cr,uid,part,context={}):
    lines=pooler.get_pool(cr.dbname).get('olap.schema').browse(cr, uid, part['id'],context)
    part['form']['fact_table']=lines.database_id.name
    part['form']['db_name']=lines.database_id.db_name
    return part['form']

class wizard_data_loader(wizard.interface):
    states = {
       'init': {
            'actions': [_getdata],
            'result': {'type':'form','arch':form1, 'fields':field1, 'state':[('end','Cancel'),('ok','Load Database Structure')]}
        },
        'ok': {
            'actions': [olap_db_connect],
            'result': {'type':'form','arch':info,'fields':{}, 'state':[('end','Continue and Configure Structure')]}
        },
        'info': {
            'actions': [],
            'result': {'type':'form', 'arch':info, 'fields':{}, 'state':[('end','Ok')]}
        },
      }
wizard_data_loader('olap.load.table')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
