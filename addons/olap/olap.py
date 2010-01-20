##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
import sqlalchemy
import time
from pyparsing import *

import wizard
import pooler
from osv import osv
from osv import fields,osv
import netsvc
import cube
from cube import levels


class olap_fact_database(osv.osv):
    _name = "olap.fact.database"
    _description = "Olap Fact Database"



    def _connection_get(self,cr,uid,ids,field_name,arg,context = {}):
        """
            Return a connection string url needed by SQL Alchemy. Exemple:
            'postgres://scott:tiger@localhost:5432/mydatabase'
        """
        res = {}
        for obj in self.browse(cr,uid,ids,context):
            res[obj.id] = '%s://%s:%s@%s:%d/%s' % (obj.type,obj.db_login,obj.db_password,obj.db_host,obj.db_port,obj.db_name)
        return res

    def test_connection(self,cr,uid,ids,context = {}):
        try:
            self_obj = self.browse(cr,uid,ids,context)
            for obj in self_obj:
                host = obj.db_host
                port = obj.db_port
                db_name = obj.db_name
                user = obj.db_login
                password = obj.db_password
                type = obj.type
                if type == 'postgres':
                    tdb = psycopg2.connect('host=%s port=%s dbname=%s user=%s password=%s' % (host,port,db_name,user,password))
                elif type == 'mysql':
                    try:
                        import MySQLdb
                        tdb = MySQLdb.connect(host = host,port = port,db = db,user = user,passwd = passwd)

                    except Exception,e:
                        raise osv.except_osv('Error (MySQLdb) : ',e)
                elif type == 'oracle':
                    try:
                        import cx_Oracle
                        tdb = cx_Oracle.connect(user,password,host)

                    except Exception,e:
                        raise osv.except_osv('Error (cx_Oracle) : ',e)

        except Exception,e:
            raise osv.except_osv('BI Error !',e)

        return True

    _columns = {
        'name': fields.char('Fact name',size = 64,required = True),
        'db_name': fields.char('Database name',size = 64,required = True , help = "Name of the database to be used for analysis."),
        'db_login': fields.char('Database login',size = 64,required = True, help = "Login for the database name specified."),
        'db_password': fields.char('Database password',size = 64,invisible = True,required = True, help = "Password for the login."),
        'db_host': fields.char('Database host',size = 64,required = True , help= "Give hostname to make connection to the database."),
        'db_port': fields.integer('Database port',required = True, help = " Port to be used in connection"),
        'type': fields.selection([('mysql','MySQL' ),('postgres','PostgreSQL' ),('oracle','Oracle' )],'Database type',required = True ),
        'connection_type': fields.selection([('socket','Socket' ),('port','Port' )],'Connection type',required = True ),
        'connection_url': fields.function(_connection_get,method = True,type = 'char',string = 'Connection URL',size = 128 ),
        'table_ids': fields.one2many('olap.database.tables','fact_database_id','Tables' ),
        'loaded': fields.boolean('Loaded',readonly = True ),
    }
    _defaults = {
        'type': lambda * args: 'postgres',
        'connection_type': lambda * args: 'port',
        'db_host': lambda * args: 'localhost',
        'db_name': lambda * args: 'terp',
        'db_port': lambda * args: '5432',
        'loaded' : lambda * args: False,
    }
olap_fact_database()

class olap_schema(osv.osv ):
    _name = "olap.schema"
    _description = "Olap Schema"

    def _app_detect(self,cr,uid,ids,field_name,arg,context = {}):
        """
            Return a Application type
        """
        res = {}

        for obj in self.browse(cr,uid,ids,context):
            if obj.database_id.type == 'postgres':
                e = sqlalchemy.create_engine(obj.database_id.connection_url)
                app_objs = self.pool.get('olap.application')
                app_ids = app_objs.search(cr,uid,[] )
                app_res = app_objs.browse(cr,uid,app_ids)
                for app_obj in app_res:
                    try:
                        result = e.execute(app_obj.query)
                        if result:
                            res[obj.id] = app_obj.name + ' Application'
                        continue
                    except:
                        continue
                if not res.has_key(obj.id):
                    res[obj.id] = "Unknown Application"
            else:
                res[obj.id] = "Unknown Application"
        return res

    _columns = {
        'name': fields.char('Schema name',size = 64,required = True),
        'note': fields.text('Schema description' ),
        'cube_ids': fields.one2many('olap.cube','schema_id','Cubes'),
        'database_id': fields.many2one('olap.fact.database','Database Connection',required = True),
        'loaded': fields.boolean('Loading Datastructure',readonly = True),
        'configure': fields.boolean('Configuring Datastructure',readonly = True),
        'ready': fields.boolean('Ready',readonly = True),
        'state': fields.selection([
            ('none','Nothing has been Configured'),
            ('dbconnect','Database Connected' ),
            ('dbload','The Structure is Loaded'),
            ('dbconfigure','The Structure is Configured.'),
            ('dbready','Schema is ready to use'),
            ('done','We Can Start building Cube'),
            ],'Schema State',readonly = True),
        'app_detect': fields.function(_app_detect,method = True,type = 'char',string = 'Connection URL',size = 128),

    }
    _defaults = {
        'loaded' : lambda * args: False,
        'state': lambda * a: 'none',
        'configure': lambda * a: False,
        'ready': lambda * a: False
        }

    def action_dbconnect(self,cr,uid,ids,context = {}):
        schema = self.browse(cr,uid,ids,context)[0]
        type = schema.database_id.type
        maxconn = 64
        try:
            if type == 'postgres':
                host = schema.database_id.db_host and "host=%s" % schema.database_id.db_host or ''
                port = schema.database_id.db_port and "port=%s" % schema.database_id.db_port or ''
                name = schema.database_id.db_name and "dbname=%s" % schema.database_id.db_name or ''
                user = schema.database_id.db_login and "user=%s" % schema.database_id.db_login or ''
                password = schema.database_id.db_password and "password=%s" % schema.database_id.db_password or ''
                tdb = psycopg2.connect('%s %s %s %s %s' % (host,port,name,user,password))

            elif type == 'mysql':
                try:
                    import MySQLdb
                    host = schema.database_id.db_host or ''
                    port = schema.database_id.db_port or ''
                    db = schema.database_id.db_name or ''
                    user = schema.database_id.db_login or ''
                    passwd = schema.database_id.db_password or ''
                    tdb = MySQLdb.connect(host = host,port = port,db = db,user = user,passwd = passwd)
                except Exception,e:
                    raise osv.except_osv('Error (MySQLdb) : ',e)

            elif type == 'oracle':
                try:
                    import cx_Oracle
                    host = schema.database_id.db_host or ''
                    port = schema.database_id.db_port or ''
                    db = schema.database_id.db_name or ''
                    user = schema.database_id.db_name.upper() or ''
                    password = int(schema.database_id.db_password) or ''
                    tdb = cx_Oracle.connect(user,password,host)
                except Exception,e:
                    raise osv.except_osv('Error (cx_Oracle) : ',e)

            for id in ids:
                self.write(cr,uid,id,{'state':'dbconnect'})
        except Exception,e:

            raise osv.except_osv('BI Error !',e)

        return True

    def action_dbload(self,cr,uid,ids,context = {}):
        for id in ids:
            id_change = self.browse(cr,uid,id)
            self.write(cr,uid,id,{'loaded':True})
            self.write(cr,uid,id,{'state':'dbload'})
        return True


    def action_dbconfigure(self,cr,uid,ids,context = {}):
        for id in ids:
            id_browsed = self.browse(cr,uid,id)
            if not id_browsed.state == 'dbconfigure':
                self.write(cr,uid,id,{'state':'dbconfigure'})
                self.write(cr,uid,id,{'configure':True})
        return True

    def action_dbready(self,cr,uid,ids,context = {}):
        for id in ids:
            self.write(cr,uid,id,{'ready':True})
            self.write(cr,uid,id,{'state':'done'})
        return True

    def action_done(self,cr,uid,ids,context = {}):
        for id in ids:
            self.write(cr,uid,id,{'state':'done'})
        return True

    def create_xml_schema(self,cr,uid,xml_schema,context = {}):
        """
            This function fill in the database according to a XML schema.
            Exemple of schema:
            <Schema>
            <Cube name="Sales">
                <Table name="sales_fact_1997"/>
                <Dimension name="Gender" foreignKey="customer_id">
                    <Hierarchy hasAll="true" allMemberName="All Genders" primaryKey="customer_id">
                        <Table name="customer"/>
                        <Level name="Gender" column="gender" uniqueMembers="true"/>
                    </Hierarchy>
                </Dimension>
                <Dimension name="Time" foreignKey="time_id">
                    <Hierarchy hasAll="false" primaryKey="time_id">
                        <Table name="time_by_day"/>
                        <Level name="Year" column="the_year" type="Numeric" uniqueMembers="true"/>
                        <Level name="Quarter" column="quarter" uniqueMembers="false"/>
                        <Level name="Month" column="month_of_year" type="Numeric" uniqueMembers="false"/>
                    </Hierarchy>
                </Dimension>
                <Measure name="Store Sales" column="store_sales" aggregator="sum" formatString="#,###.##"/>
                <Measure name="Store Cost" column="store_cost" aggregator="sum" formatString="#,###.00"/>
                <CalculatedMember name="Profit" dimension="Measures" formula="[Measures].
                    [Store Sales]-[Measures].[Store Cost]">
                    <CalculatedMemberProperty name="FORMAT_STRING" value="$#,##0.00"/>
                </CalculatedMember>
            </Cube>
            </Schema
        """
        raise 'Not implemented !'

    def request(self,cr,uid,name,request,context = {}):
        ids = self.search(cr,uid,[('name','=',name)])
        if not len(ids):
            raise 'Schema not found !'
        schema = self.browse(cr,uid,ids[0],context)
#        warehouse = cube.warehouse()
#        find_table = warehouse.match_table(cr, uid, request, context)
        print 'Parsing MDX...'
        print '\t',request
        mdx_parser = cube.mdx_parser()
        mdx = mdx_parser.parse(request)

        print 'Validating MDX...'
        mdx.preprocess()
        validate,cubex = mdx.validate(schema)

        print 'Running MDX...'
        res_comp = self.pool.get('res.company').search(cr,uid,([]))
        res_comp = self.pool.get('res.company').browse(cr,uid,res_comp)
        currency = res_comp[0].currency_id.name
        print " Default Currency",currency
        data = mdx.run(currency)
#        qry_obj = self.pool.get('olap.query.logs')
#        qry_id = qry_obj.search(cr, uid, [('query','=', request)])
#        
#        flag = True
#        if qry_id:
#            qry = qry_obj.browse(cr, uid, qry_id)[0]
#            
#            if qry.count >=3 and qry.table_name!='':
#                data = warehouse.run(currency, qry)
#                flag = False
#                qry.count = qry.count +1
#                qry_obj.write(cr, uid, qry_id, {'count': qry.count})
#            else:
#                data = mdx.run(currency)
#        else:
#            data = mdx.run(currency)
        print 'Running Done...'
        print 'Formatting Output...'
#        if cubex.query_log and flag:
        if cubex.query_log:
            log = context.get('log')
            if log:
                connection = schema.database_id.connection_url
#                warehouse.log(cr,uid,cubex,request,data,connection,context)
                mdx.log(cr,uid,cubex,request,context)
        return cube.mdx_output(data)
olap_schema()

class olap_database_tables(osv.osv):
    _name = "olap.database.tables"
    _description = "Olap Database Tables"
    _columns = {
        'table_db_name': fields.char('Table Name',size = 64,required = True,readonly = True),
        'name': fields.char('End-User Name',size = 64,required = True),
        'columns': fields.one2many('olap.database.columns','table_id','Columns'),
        'fact_database_id': fields.many2one('olap.fact.database','Database Id',required = True,ondelete = 'cascade',readonly = True),
        'active': fields.boolean('Active'),
        'hide': fields.boolean('Hidden'),
    }
    _defaults = {
        'active': lambda * args: True,
        'hide': lambda * args: False
    }
    def name_get(self,cr,uid,ids,context = {}):
        result = []
        for t in self.browse(cr,uid,ids,context):
            if t.name <> t.table_db_name:
                result.append((t.id,t.name + ' (' + t.table_db_name + ')'))
            else:
                result.append((t.id,t.name))
        return result

    def show_col_view(self,cr,uid,ids,context = {}):
        ids_cols = self.pool.get('olap.database.columns').search(cr,uid,([('table_id','=',ids[0])]))
        id = self.pool.get('ir.ui.view').search(cr,uid,([('name','=','olap.database.columns.tree')]),context = {})[0]
        return {
            'domain': "[('id','in', [" + ','.join(map(str,ids_cols)) + "])]",
            'name': 'Database Columns',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'olap.database.columns',
            'views': [(id,'tree'),(False,'form')],
            'type': 'ir.actions.act_window',
        }

    def hide_col(self,cr,uid,ids,context = {}):
        # To hide all the related columns also
        for id in ids:
             self.write(cr,uid,id,{'hide':True})
        return {}

    def show_col(self,cr,uid,ids,context = {}):
        # To show or unhide all the columns also
        for id in ids:
             self.write(cr,uid,id,{'hide':False})
        return {}


olap_database_tables()

class olap_database_columns(osv.osv):
    _name = "olap.database.columns"
    _description = "Olap Database Columns"
    datatypes = {
        'timestamp': 'TimeStamp without Time Zone',
        'timestampz': 'TimeStamp with Time Zone',
        'numeric': 'Numeric',
        'int': 'Integer',
        'float8': 'Double Precesion',
        'varchar': 'Character Varying',
        'bool': 'Boolean',
        'bytea':'Byte A',
        'int2':'Small Integer',
        'int4':'Integer',
        'int8':'Big Integer',
        'text':'Text',
        'date':'Date',
        'time': 'TimeStamp without Time Zone',
    'number':'NUMBER',
    }
    def _datatypes_get(self,*args,**argv):
        return self.datatypes.items()
    _columns = {
        'column_db_name': fields.char('Column DBName',size = 64,required = True,readonly = True),
        'name': fields.char('Column Name',size = 64,required = True),
        'table_id': fields.many2one('olap.database.tables','Table Id',required = True,ondelete = 'cascade',select = True,readonly = True),
        'primary_key': fields.boolean('Primary Key'),
        'type': fields.selection(_datatypes_get,'Type',size = 64,required = True,readonly = True),
        'related_to': fields.many2one('olap.database.tables','Related To',required = False,readonly = True),
        'active': fields.boolean('Active'),
        'hide': fields.boolean('Hidden'),
    }
    _defaults = {
        'hide': lambda * args: False,
        'active': lambda * args: True,
        'primary_key': lambda * args: False,
    }
    def name_get(self,cr,uid,ids,context = {}):
        result = []
        for t in self.browse(cr,uid,ids,context):
            if t.name <> t.column_db_name:
                result.append((t.id,t.table_id.table_db_name + ' (' + t.name + ')'))
            else:
                result.append((t.id,t.table_id.table_db_name + ' (' + t.name + ')'))
        return result


    def search(self,cr,uid,args,offset = 0,limit = None,order = None,
            context = None,count = False):
        if not context:
            return super(olap_database_columns,self).search(cr,uid,args,offset,limit,
                    order,context = context,count = count)
        col_pool = self.pool.get('olap.database.columns')
        if context and context.has_key('fk') and context['fk']:
            if context.has_key('dim_x') and context['dim_x']:
                dim_obj = self.pool.get('olap.dimension').browse(cr,uid,int(context['dim_x']))
                make_ids = []
                make_ids.append(dim_obj.cube_id.table_id.column_link_id.table_id.id)

                for lines in  dim_obj.cube_id.table_id.line_ids:
                    make_ids.append(lines.field_id.related_to.id)
                    make_ids.append(lines.field_id.table_id.id)
                args = [('table_id','in',make_ids),('related_to','<>',False),('hide','<>',True),('active','<>',False)]
                return super(olap_database_columns,self).search(cr,uid,args,offset,limit,order,context = context,count = count)

        if args and context and context.has_key('flag') and context['flag']:
            ids = args[0][2][0][2]

            if ids:
                col_obj = col_pool.browse(cr,uid,ids)
                make_ids = []
                for lines in col_obj:
                    make_ids.append(lines.related_to.id)
                link_id = col_pool.browse(cr,uid,int(context['link_col']))
                make_ids.append(link_id.table_id.id)
                args = ['|',('table_id','in',make_ids),('related_to','in',make_ids),('primary_key','<>',True),('hide','<>',True),('active','<>',False)]
                ids = super(olap_database_columns,self).search(cr,uid,args,offset,limit,order,context = context,count = count)
                return ids
            elif context and context.has_key('master_dim') and context['master_dim']:
                make_ids = []
                col_obj = col_pool.browse(cr,uid,int(context['link_col']))
                args = ['|',('table_id','=',col_obj.related_to.id),('related_to','=',col_obj.table_id.id),('hide','<>',True),('active','<>',False)]
                return  super(olap_database_columns,self).search(cr,uid,args,offset,limit,order,context = context,count = count)
            else:
                col = col_pool.browse(cr,uid,int(context['link_col']))
                base_table = col.table_id
                args = ['|',('table_id','=',base_table.id),('related_to','=',base_table.id),('hide','<>',True),('active','<>',False)]
                return super(olap_database_columns,self).search(cr,uid,args,offset,limit,order,context = context,count = count)


        if context and context.has_key('filter_cols_cube'):
            cube_obj = self.pool.get('olap.cube').browse(cr,uid,int(context['filter_cols_cube']))
            make_ids = []
            make_ids.append(cube_obj.table_id.column_link_id.related_to.id)
            for lines in cube_obj.table_id.line_ids:
                make_ids.append(lines.table_id.id)
            if make_ids:
                make_ids.append(cube_obj.table_id.line_ids[len(cube_obj.table_id.line_ids) - 1].field_id.related_to.id)
                args = [('table_id','in',make_ids),('related_to','=',False),('primary_key','<>',True),('type','not in',['date','timestamp','timestampz','time']),('hide','<>',True),('active','<>',False)]
                ids = super(olap_database_columns,self).search(cr,uid,args,offset,limit,
                    order,context = context,count = count)
                return ids

        elif context and context.has_key('filter_cols_hier'):
            hier_obj = self.pool.get('olap.hierarchy').browse(cr,uid,int(context['filter_cols_hier']))
            make_ids = []
            if hier_obj.table_id.line_ids:
                for lines in hier_obj.table_id.line_ids:
                    make_ids.append(lines.field_id.related_to.id)

                if make_ids:
                    make_ids.append(hier_obj.table_id.column_link_id.related_to.id)
                    make_ids.append(hier_obj.table_id.column_link_id.table_id.id)
                    args = [('table_id','in',make_ids),('hide','<>',True),('active','<>',False)]
                    ids = super(olap_database_columns,self).search(cr,uid,args,offset,limit,
                        order,context = context,count = count)
                    return ids
            else:
                args = [('table_id','=',hier_obj.table_id.column_link_id.related_to.id)]
                ids = super(olap_database_columns,self).search(cr,uid,args,offset,limit,
                        order,context = context,count = count)
                return ids
        elif context and context.has_key('fk') and context['fk']:
            args = [('primary_key','=',True),('hide','<>',True),('active','<>',False)]

        else:
            if context and context.has_key('master_dim') and context['master_dim']:
                dim_obj = self.pool.get('olap.dimension').browse(cr,uid,int(context['master_dim']))
                lines = dim_obj.cube_id.table_id.line_ids
                table_ids = []
                for line in lines:
                    table_ids.append(line.table_id.id)
                args = [('table_id','in',table_ids),('related_to','<>',False),('hide','<>',True),('active','<>',False)]
            elif context and context.has_key('master_schema') and context['master_schema']:
                    args = [('primary_key','=','True')]
        return super(olap_database_columns,self).search(cr,uid,args,offset,limit,
                    order,context = context,count = count)


    def hide_col(self,cr,uid,ids,context = {}):
        for id in ids:
             self.write(cr,uid,id,{'hide':True})
        return {}

    def show_col(self,cr,uid,ids,context = {}):
        for id in ids:
             self.write(cr,uid,id,{'hide':True})
        return {}

    def field_add(self,cr,uid,ids,context = {}):
        col_data = self.pool.get('olap.database.columns').read(cr,uid,ids,[],context)[0]
        ctx_list = []
        if col_data['related_to']:
            table_id = col_data['related_to'][0]
        else:
            table_id = col_data['table_id'][0]
        if context['parent_id']:
            parent_id = context['parent_id']
            val = {
            'cube_table_id':parent_id,
            'table_id':table_id,
            'field_id':ids[0]
            }
            id = self.pool.get('olap.cube.table.line').create(cr,uid,val,context)
        else:
            parent_id = self.pool.get('olap.cube.table').create(cr,uid,{'name':col_data['table_id'][1]},context)
            ctx_list = [('client','web'),('app','bi'),('id',parent_id)]
        return ctx_list

    def make_hierarchy(self,cr,uid,ids,context = {}):
        col_data = self.pool.get('olap.database.columns').read(cr,uid,ids,[],context)[0]
        ctx_list = []
        if context and context.has_key('hier_parent_id')and context['hier_parent_id']:
            hier_obj = self.pool.get('olap.hierarchy').browse(cr,uid,context['hier_parent_id'])
            pk_table = hier_obj.table_id.name
        elif context and context.has_key('hier_parent_table'):
            cube_table_obj = self.pool.get('olap.cube.table').browse(cr,uid,context['hier_parent_table'])
            pk_table = cube_table_obj.name
        val = {
             'field_name':col_data['name'],
             'name':col_data['name'],
             'primary_key_table':pk_table
        }
        if context['hier_parent_id']:
            id = self.pool.get('olap.hierarchy').write(cr,uid,context['hier_parent_id'],val,context)
        else:
            if context['parent_name']: val['name'] = context['parent_name']
            if context['parent_dimension'] :val['dimension_id'] = context['parent_dimension']
            if context['hier_parent_table'] : val['table_id'] = context['hier_parent_table']
            if context['parent_field_name'] : val['field_name'] = context['parent_field_name']
            if context['parent_level'] : val['level_ids'] = conext['parent_level']
            if context['parent_member_all']: val['member_all'] = context['parent_member_all']
            if context['parent_member_default'] : val['member_default'] = context['parent_member_default']
            if context['parent_type']: val['type'] = context['parent_type']
            val['primary_key_table'] = col_data['table_id'][1]
            id = self.pool.get('olap.hierarchy').create(cr,uid,val,context)
            ctx_list = [('client','web'),('app','bi'),('id',id)]
        return ctx_list

olap_database_columns()

class olap_cube_table(osv.osv):
    _name = "olap.cube.table"
    _description = "Olap cube table"

    def write(self,cr,uid,ids,vals,context = None):
        if vals and vals.get('available_table_ids',0) and context and (context.has_key('master_dim') or context.has_key('d_id') or context.has_key('parent_schema_id')):
            new_fields = vals['available_table_ids'][0][2]
            final = []
            for data in self.browse(cr,uid,ids):
                orignal_lines = []
                for line in data.line_ids:
                    orignal_lines.append(line.id)

                orignal_fields = []
                for line in data.line_ids:
                    orignal_fields.append(line.field_id.id)
                if len(orignal_fields) < len(new_fields):
                    if new_fields[:len(orignal_fields)] == orignal_fields:
                        new_fields = new_fields[len(orignal_fields):]
                        cols_obj = self.pool.get('olap.database.columns').browse(cr,uid,new_fields)
                        val = {}
                        val['cube_table_id'] = ids[0]
                        for col in cols_obj:
                            val['table_id'] = col.table_id.id
                            val['field_id'] = col.id
                        id = self.pool.get('olap.cube.table.line').create(cr,uid,val,context = context)
                    else:
                        cols_obj = self.pool.get('olap.database.columns').unlink(cr,uid,orignal_lines)
                        cols_obj = self.pool.get('olap.database.columns').browse(cr,uid,new_fields)
                        val = {}
                        val['cube_table_id'] = ids[0]
                        for col in cols_obj:
                            val['table_id'] = col.table_id.id
                            val['field_id'] = col.id
                        id = self.pool.get('olap.cube.table.line').create(cr,uid,val,context = context)

                elif len(orignal_fields) > len(new_fields):
                    if orignal_fields[:len(new_fields)] == new_fields:
                        remove_id = orignal_lines[len(new_fields):]
                        id = self.pool.get('olap.cube.table.line').unlink(cr,uid,remove_id,context = context)
                    else:
                        val = {}
                        id = self.pool.get('olap.cube.table.line').unlink(cr,uid,orignal_lines ,context = context)
                        cols_obj = self.pool.get('olap.database.columns').browse(cr,uid,new_fields)
                        val = {}
                        val['cube_table_id'] = ids[0]
                        for col in cols_obj:
                            val['table_id'] = col.table_id.id
                            val['field_id'] = col.id
                        id = self.pool.get('olap.cube.table.line').create(cr,uid,val,context = context)
            return  super(olap_cube_table,self).write(cr,uid,ids,vals,context)

    def create(self,cr,uid,vals,context = None):
        cube_table_id = super(olap_cube_table,self).create(cr,uid,vals,context)
        if vals and vals.get('available_table_ids',0) and context and (context.has_key('d_id') or context.has_key('parent_schema_id') or context.has_key('master_dim') or context.has_key('d_id')):
            lines_ids = vals['available_table_ids'][0][2]
            cols_obj = self.pool.get('olap.database.columns').browse(cr,uid,lines_ids)
            val = {}
            val['cube_table_id'] = cube_table_id
            for col in cols_obj:
                val['table_id'] = col.table_id.id
                val['field_id'] = col.id
                id = self.pool.get('olap.cube.table.line').create(cr,uid,val,context = context)
        return cube_table_id

    def search(self,cr,uid,args,offset = 0,limit = None,order = None,
            context = None,count = False):
        if context and context.has_key('parent_schema_id'):
            args = [('schema_id','=',context['parent_schema_id'])]
        if context and context.has_key('d_id'):
            dim_obj = self.pool.get('olap.dimension').browse(cr,uid,int(context['d_id']))
            args = [('schema_id','=',dim_obj.cube_id.schema_id.id)]
        return super(olap_cube_table,self).search(cr,uid,args,offset,limit,order,context = context,count = count)

    def _available_table_get(self,cr,uid,ids,name,arg,context = None):
        result = {}
        parent_table_id = []
        parent_table_ids = []
        field_obj = self.pool.get('olap.database.columns')
        for table in self.browse(cr,uid,ids,context):
            if table.line_ids:
                ids = []
                ids = map(lambda x: x.field_id.id,table.line_ids)
                result[table.id] = ids
            else:
                result[table.id] = []
        return result

    def _set_schema(self,cr,uid,context = {}):
        if context and context.has_key('d_id'):
            dim_obj = self.pool.get('olap.dimension').browse(cr,uid,int(context['d_id']))
            return dim_obj.cube_id.schema_id.id
        if context and context.has_key('parent_schema_id'):
            return context['parent_schema_id']

    def _set_name(self,cr,uid,context = {}):
        if context and context.has_key('d_id'):
            dim_obj = self.pool.get('olap.dimension').browse(cr,uid,int(context['d_id']))
            return dim_obj.cubeAid.table_id.name

    def _get_id(self,cr,uid,ids,context = {}):
        if context and context.has_key('d_id'):
            dim_obj = self.pool.get('olap.dimension').browse(cr,uid,int(context['d_id']))
            table_id = self.pool.get('olap.database.tables').search(cr,uid,[('table_db_name','in',[dim_obj.cube_id.table_id.name]),('fact_database_id','=',dim_obj.cube_id.schema_id.database_id.id)])
            col_ids = self.pool.get('olap.database.columns').search(cr,uid,[('table_id','in',table_id),('hide','<>',True),('related_to','<>',False)])
        else:
            col_ids = self.pool.get('olap.database.columns').search(cr,uid,[('primary_key','=',True),('hide','<>',True)])
        return col_ids

    def _def_set(self,cr,uid,context = {}):
        return []

    _columns = {
        'name': fields.char('Table name',size = 64,required = True),
        'line_ids': fields.one2many('olap.cube.table.line','cube_table_id','Database Tables',required = True),
        'schema_id':fields.many2one('olap.schema','Schema id',ondelete = 'cascade'),
        'column_link_id':fields.many2one('olap.database.columns','Relational Column' ,required = True),
        'available_table_ids': fields.function(
            _available_table_get,
            method = True,
            relation = 'olap.database.columns',
            string = 'Available Tables',
            type = "many2many"
       ),
    }
    _defaults = {
        'schema_id':_set_schema,
    }
    def field_add(self,cr,uid,ids,context = {}):
        return {}
olap_cube_table()

class olap_cube_table_line(osv.osv):
    _name = "olap.cube.table.line"
    _description = "Olap cube table"
    _rec_name = 'table_id'
    _columns = {
        'cube_table_id': fields.many2one('olap.cube.table','Cube Table',required = True,ondelete = 'cascade'),
        'table_id': fields.many2one('olap.database.tables','Database Table',required = True,ondelete = 'cascade'),
        'field_id': fields.many2one('olap.database.columns','Link Field'),
    }
    # Set the Table when changing field_id
    def onchange_field_id(self,*args,**argv):
        pass
olap_cube_table_line()

class olap_cube(osv.osv):
    _name = "olap.cube"
    _description = "Olap cube"

    def _set_schema(self,cr,uid,context = {}):
        if context and context.has_key('schema_id'):
            return context['schema_id']
        return False

    _columns = {
        'name': fields.char('Cube name',size = 64,required = True),
        'table_id': fields.many2one('olap.cube.table','Fact table',size = 64,required = True, help="Table(s) for cube."),
        'schema_id': fields.many2one('olap.schema','Schema',readonly = True),
        'dimension_ids': fields.one2many('olap.dimension','cube_id','Dimensions'),
        'measure_ids': fields.one2many('olap.measure','cube_id','Measures'),
        'query_log': fields.boolean('Query Logging', help = "Enabling  this will log all the queries in the browser"),
        'query_ids': fields.one2many('olap.query.logs','cube_id','Queries'),
    }
    _defaults = {
                 'schema_id':_set_schema
                 }
olap_cube()

class olap_query_logs(osv.osv):
    _name = "olap.query.logs"
    _description = "Olap query logs"
    _columns = {
        'user_id' : fields.many2one('res.users','Tiny ERP User'),
        'query':fields.text('Query',required = True),
        'time':fields.datetime('Time',required = True),
        'result_size':fields.integer('Result Size',readonly = True),
        'cube_id': fields.many2one('olap.cube','Cube',required = True),
        'count': fields.integer('Count', readonly=True),
        'schema_id': fields.many2one('olap.schema','Schema',readonly = True),
#        'table_name': fields.char('Table Name', size=164, readonly = True),
    }
    
    _defaults = {
                 'count':lambda * args: 0
                 }
olap_query_logs()


class olap_dimension(osv.osv):
    _name = "olap.dimension"
    _description = "Olap dimension"

    def _set_cube(self,cr,uid,context = {}):
        if context and context.has_key('cube_id'):
            return context['cube_id']
        return False

    _columns = {
        'name': fields.char('Dimension name',size = 64,required = True),
        'cube_id': fields.many2one('olap.cube','Cube',required = True),
        'hierarchy_ids': fields.one2many('olap.hierarchy','dimension_id','Hierarchies'),
    }
    _defaults = {
                 'cube_id':_set_cube,
    }

olap_dimension()

class olap_hierarchy(osv.osv):
    _name = "olap.hierarchy"
    _description = "Olap hierarchy"
    _order = "sequence, id"
    hierarchy_type = {
        'date': 'Date',
        'date_year': 'Year of Date',
        'date_quarter': 'Quarter of Date',
        'date_month': 'Month of Date',
        'many2one': 'Many2one'
    }

    def _set_dimension(self,cr,uid,context = {}):
        if context and context.has_key('dimension_id'):
            return context['dimension_id']
        return False

    def _set_name(self,cr,uid,context = {}):
        if context and context.has_key('dimension_id'):
            dim_obj = self.pool.get('olap.dimension').browse(cr,uid,int(context['dimension_id']))
            return dim_obj.name
        return False

    def _hierarchy_get(self,*args,**argv):
        return self.hierarchy_type.items()

    _columns = {
        'name': fields.char('Hierarchy name',size = 64,required = True),
        'primary_key': fields.char('Primary key',size = 64),
        'primary_key_table': fields.char('Primary key table',size = 64),
        'sequence': fields.integer('Sequence',required = True),
        'dimension_id': fields.many2one('olap.dimension','Dimension',required = True),
        'level_ids': fields.one2many('olap.level','hierarchy_id','Levels'),
        'table_id': fields.many2one('olap.cube.table','Fact table(s)',required = True , help ="Table(s) to make hierarchy on the cube."),
    }
    _defaults = {
        'sequence': lambda * args: 1,
        'primary_key': lambda * args: 'id',
        'dimension_id':_set_dimension,
        'name':_set_name
    }

olap_hierarchy()

class olap_level(osv.osv):
    _name = "olap.level"
    _description = "Olap level"
    _order = "sequence, id"
    _types = {
        'normal': levels.level_normal(),
        'date_year': levels.level_date_year(),
        'date_quarter': levels.level_date_quarter(),
        'date_month': levels.level_date_month()
    }

    def _set_hierarchy(self,cr,uid,context = {}):
        if context and context.has_key('hierarchy_id'):
            return context['hierarchy_id']
        return False

    def _set_name(self,cr,uid,context = {}):
        if context and context.has_key('hierarchy_id'):
            hier_obj = self.pool.get('olap.hierarchy').browse(cr,uid,int(context['hierarchy_id']))
            return hier_obj.name

    def onchange_column_name(self,cr,uid,ids,column,context = {}):
        if not column:
            return {}
        val = {}
        col = self.pool.get('olap.database.columns').browse(cr,uid,column)
        val['table_name'] = col.table_id.table_db_name
        val['column_id_name'] = col.column_db_name
        if (col.type == 'date'):
            val['type'] = 'date_year'
        return {'value':val}

    def _type_get(self,cr,uid,*args,**argv):
        keys = self._types.keys()
        return map(lambda x: (x,x),keys)


    _columns = {
        'name': fields.char('Level name',size = 64,required = True),
        'column_name':fields.many2one('olap.database.columns','Columns Name',required = True),
        'column_id_name': fields.char('Column ID',size = 64,required = True),
        'type': fields.selection(selection = _type_get,string = 'Level class',size = 64,required = True),
        'table_name': fields.char('Table name',size = 64,required = True,help = "The name of the table on which the column is defined. If False, take the table from the hierarchy."),
        'sequence': fields.integer('Sequence',required = True),
        'hierarchy_id': fields.many2one('olap.hierarchy','Hierarchy',required = True),
    }

    _defaults = {
        'column_id_name': lambda * args: 'name',
        'sequence':lambda * args: '1',
        'type':lambda * args:'normal',
        'hierarchy_id':_set_hierarchy,
        'name':_set_name
    }

olap_level()


class olap_measure(osv.osv):
    _name = "olap.measure"
    _description = "Olap measure"

    def _set_cube(self,cr,uid,context = {}):
        if context and context.has_key('cube_id'):
            return context['cube_id']
        return False

    def onchange_measure_name(self,cr,uid,ids,column,context = {}):
        val = {}
        if not column:
            return {}
        col = self.pool.get('olap.database.columns').browse(cr,uid,column)
        val['table_name'] = col.table_id.table_db_name
        val['value_column_id_name'] = col.column_db_name
        val['name'] = col.column_db_name
        return {'value':val}

    _columns = {
        'name': fields.char('Measure name',size = 64,required = True),
        'cube_id': fields.many2one('olap.cube','Cube',required = True),
        'value_column': fields.many2one('olap.database.columns','Fact Table Column'),
        'value_column_id_name': fields.char('Column ID',size = 64),
        'table_name': fields.char('Table name',size = 64,help = "The name of the table on which the column is defined. If False, take the table from the cube."),
        'measure_type':fields.selection([('fact_column','Fact Table Column'),('sql_expr','SQL Expression')],'Measure Type',required = True,help = "Select between auto column or sql expression for the measures"),
        'value_sql': fields.char('SQL Expression',size = 200,help = "You can provide valid sql expression. Make sure it have function with fully qualified column name like (sum,avg ...)(tablename.columnname (+,- ...) tablename.columnname)"),
        'agregator': fields.selection([('sum','Sum'),('count','count'),('avg','Average')],'Agregator',required = True),
        'datatype': fields.selection([('int','Integer'),('float','Float')],'Datatype',required = True),
        'formatstring': fields.selection([
                                           ('none','None (0000.00)'),
                                           ('cr_prefix','Prefix Default Currency (EUR 0000.00)'),
                                           ('cr_postfix','Postfix Default Currency(0000.00 EUR)'),
                                           ('cr_prefix_comma','Prefix Default Currency with comma seperator (EUR 0,000.00)'),
                                           ('cr_postfix_comma','Postfix Default Currency with comma seperator (0,000.00 EUR)'),
                                           ('comma_sep', 'Comma Seperator (0,000)')
                                           ],
                                           'Format string',required = True, help=" Let you specify how the measure to be displayed in cube browser"),
    }
    _defaults = {
        'agregator': lambda * args: 'sum',
        'datatype': lambda * args: 'float',
        'formatstring': lambda * args: 'none',
        'cube_id':_set_cube,
        'measure_type':lambda * args:'fact_column',
    }
olap_measure()

class olap_application(osv.osv):
    _name = "olap.application"
    _description = "Olap application"
    _columns = {
        'name': fields.char('Application name',size = 64,required = True),
        'query':fields.text('Application Query'),
        'table_ids':fields.one2many('olap.application.table','application_id','Tables'),
        'field_ids': fields.one2many('olap.application.field','application_id','Fields'),
    }
olap_application()


class olap_application_table(osv.osv):
    _name = "olap.application.table"
    _description = "Olap application table"
    _columns = {
        'name': fields.char('Application table name',size = 64,required = True),
        'table_name': fields.char('Table name',size = 64,required = True),
        'is_hidden': fields.boolean('Hidden'),
        'application_id':  fields.many2one('olap.application','Application Id',required = True),
    }
olap_application_table()

class olap_application_field(osv.osv):
    _name = "olap.application.field"
    _description = "Olap application field"
    _columns = {
        'name': fields.char('Application field name',size = 64,required = True),
        'table_name':  fields.char('Application table name',size = 64),
        'field_name':fields.char('Field name',size = 64),
        'is_hidden': fields.boolean('Hidden'),
        'application_id':  fields.many2one('olap.application','Application Id',required = True),
    }
olap_application_field()

class olap_saved_query(osv.osv):
    _name = "olap.saved.query"
    _decription = "Olap Saved Query"
#   _rec_name = 'user_id'
    _columns = {
                'name': fields.text('Query Name',size = 64),
                'user_id' : fields.many2one('res.users','User'),
                'query': fields.text('Query',required = True),
                'cube_id': fields.many2one('olap.cube','Cube',required = True),
                'mdx_id': fields.char('Module', size=64),
                'schema_id': fields.many2one('olap.schema','Schema',required = True),
                'time':fields.datetime('Time',required = True),
                'axis_keys': fields.text('Axis Keys'),
                }
olap_saved_query()
# Wizard for the Load Data Structure
# Replacement for the Load Wizard according to the new structure
class bi_load_db_wizard(osv.osv_memory):
    _name = 'bi.load.db.wizard'

    def _get_fact_table(self,cr,uid,ctx):
        if ctx and ctx.has_key('active_id'):
            schema_obj = self.pool.get('olap.schema').browse(cr,uid,ctx['active_id'])
            return schema_obj.name
        return False

    def _get_db_name(self,cr,uid,ctx):
        if ctx and ctx.has_key('active_id'):
            schema_obj = self.pool.get('olap.schema').browse(cr,uid,ctx['active_id'])
            return schema_obj.database_id.name
        return False

    _columns = {
        'fact_table':fields.char('Fact Name' ,size = 64,readonly = True),
        'db_name':fields.char('Database Name',size = 64,readonly = True)
    }

    _defaults = {
        'fact_table':_get_fact_table,
        'db_name':_get_db_name,
    }

    def action_load(self,cr,uid,ids,context = None):
        if context and context.has_key('active_id'):
            lines = self.pool.get('olap.schema').browse(cr,uid,context['active_id'])
            pool = pooler.get_pool(cr.dbname)
#            lines=pool.get('olap.schema').browse(cr, uid, part['id'],context)
            id_db = lines.database_id.id
            type = lines.database_id.type
            db_name = lines.database_id.db_name
            tobj = pool.get('olap.database.tables')
            tcol = pool.get('olap.database.columns')
            if type == 'postgres':
#                host = lines.database_id.db_host and "host=%s" % lines.database_id.db_host or ''
#                port = lines.database_id.db_port and "port=%s" % lines.database_id.db_port or ''
#                name = lines.database_id.db_name and "dbname=%s" % lines.database_id.db_name or ''
#                user = lines.database_id.db_login and "user=%s" % lines.database_id.db_login or ''
#                password = lines.database_id.db_password and "password=%s" % lines.database_id.db_password or ''
#                tdb = psycopg2.connect('%s %s %s %s %s' % (host, port, name, user, password))
#                cr_db = tdb.cursor()
#                cr.execute('select table_db_name,id from olap_database_tables where fact_database_id=%d', (id_db,))
#                tables = dict(cr.fetchall())
#                # Format for storing the tables
#                # tables['table_db_name']=id
#                tables_id = map(lambda x: str(tables[x]),tables)
#                cols={}
#                if tables_id:
#                    cr.execute('select column_db_name,id,table_id from olap_database_columns where table_id in (' + ','.join(tables_id) +')')
#                else:
#                    cr.execute('select column_db_name,id,table_id from olap_database_columns')
#              
#                for data in cr.fetchall():
#                    cols[str(data[1])]=(data[0],int(data[2]))
#                # Format of storing the cols 
#                # cols['id']=(col_db_name,table_id)    
#                print 'Creating / Updating Tables...' 
#                cr_db.execute("select table_name, table_catalog from INFORMATION_SCHEMA.tables as a where a.table_schema = 'public'")
#                for table in cr_db.fetchall():
#                    val = {
#                        'fact_database_id':id_db,
#                        'table_db_name':table[0]
#                    }
#                   
#                    if table[0] in tables.keys():
#                        table_id=tobj.write(cr,uid,[tables[table[0]]], val, context)
#                    else:
#                        val['name']=table[0]
#                        tables[val['name']] = tobj.create(cr,uid,val, context)    
#                print 'Creating / Updating Columns...' 
#                cr_db.execute("""SELECT
#                        table_name, column_name, udt_name
#                    from
#                        INFORMATION_SCHEMA.columns
#                    WHERE table_schema = 'public'""")
#                
#                for col in cr_db.fetchall():
#                    val={
#                        'table_id': tables[col[0]],
#                        'column_db_name': col[1],
#                        'type': col[2],
#                    }
#                    
#                    id_made=filter(lambda x:(int(cols[x][1])==int(tables[col[0]])),cols)
#                    if col[1] in cols.keys() and col[0] in tables.keys()and id_made:
#                        col_id=tcol.write(cr,uid,cols[tables[str(col[0])]], val, context)
#                    else:
#                        val['name']=col[1]
#                        id_made = tcol.create(cr,uid,val, context)
#                        cols[str(id_made)] = (val['name'],int(val['table_id']))
#                print 'Creating / Updating Constraints...' 
#                cr_db.execute("""select 
#                        table_name,column_name 
#                    from 
#                        INFORMATION_schema.key_column_usage
#                    where 
#                        constraint_name in (
#                                    select constraint_name from INFORMATION_SCHEMA .table_constraints
#                                    where 
#                                        constraint_type = 'PRIMARY KEY')""")
#                print "Updating the Primary Key Constraint" 
#                for constraint in cr_db.fetchall():
#                    val={
#                        'primary_key':True
#                    }
#                    
#                    id_to_write=filter(lambda x:(int(cols[x][1])==int(tables[constraint[0]])and(constraint[1]==cols[x][0])),cols)
#                    col_id=tcol.write(cr,uid,int(id_to_write[0]),val,context) 
#                print "Updating the Foreign key constraint" 
#                cr_db.execute("""select 
#                            constraint_name,table_name 
#                    from 
#                        INFORMATION_schema.constraint_column_usage 
#                    where
#                        constraint_name in (
#                                    select constraint_name from INFORMATION_SCHEMA.table_constraints 
#                                    where 
#                                        constraint_type = 'FOREIGN KEY')""")
#                for_key=dict(cr_db.fetchall())
#                
#                cr_db.execute("""select 
#                             table_name,column_name,constraint_name 
#                         from 
#                             INFORMATION_schema.key_column_usage
#                         where 
#                             constraint_name in (
#                                         select constraint_name from INFORMATION_SCHEMA.table_constraints 
#                                         where 
#                                             constraint_type = 'FOREIGN KEY')""") 

#                for constraint in cr_db.fetchall():
#                    val={
#                        'related_to':tables[for_key[constraint[2]]]
#                    }
#                    id_to_write=filter(lambda x:(int(cols[x][1])==int(tables[constraint[0]])and (constraint[1]==cols[x][0])),cols)
#                    col_id=tcol.write(cr,uid,int(id_to_write[0]),val,context) 

                host = lines.database_id.db_host and "host=%s" % lines.database_id.db_host or ''
                port = lines.database_id.db_port and "port=%s" % lines.database_id.db_port or ''
                name = lines.database_id.db_name and "dbname=%s" % lines.database_id.db_name or ''
                user = lines.database_id.db_login and "user=%s" % lines.database_id.db_login or ''
                password = lines.database_id.db_password and "password=%s" % lines.database_id.db_password or ''
                tdb = psycopg2.connect('%s %s %s %s %s' % (host,port,name,user,password))
                cr_db = tdb.cursor()
                cr.execute('select table_db_name,id from olap_database_tables where fact_database_id=%d',(id_db,))
                tables = dict(cr.fetchall())
                # Format for storing the tables
                # tables['table_db_name']=id
                tables_id = map(lambda x: str(tables[x]),tables)
                # Format of storing the cols 
                # cols['id']=(col_db_name,table_id)    
                print 'Creating / Updating Tables...'
                cr_db.execute("select table_name, table_catalog from INFORMATION_SCHEMA.tables as a where a.table_schema = 'public'")
                for table in cr_db.fetchall():
                    val = {
                        'fact_database_id':id_db,
                        'table_db_name':table[0]
                    }
                    if table[0] in tables.keys():
                        table_id = tobj.write(cr,uid,[tables[table[0]]],val,context)
                    else:
                        val['name'] = table[0]
                        tables[val['name']] = tobj.create(cr,uid,val,context)

                print 'Creating / Updating Columns ....'
                cols = {}
                if tables_id:
                    cr.execute('select column_db_name,id,table_id from olap_database_columns where table_id in (' + ','.join(tables_id) + ')')
                else:
#                    cr.execute('select column_db_name,id,table_id from olap_database_columns ')
                    cr.execute("select olap_database_columns.column_db_name, olap_database_columns.id, olap_database_columns.table_id from olap_database_columns join olap_database_tables on olap_database_columns.table_id = olap_database_tables.id where olap_database_tables.fact_database_id=%d",(id_db,))
                table_col = {}
                cols_name = {}
                for x in tables:
                    table_col[str(tables[x])] = [{}]
                for data in cr.fetchall():
                    cols[str(data[1])] = (data[0],int(data[2]))
                    table_col[str(data[2])][0][data[0]] = data[1]
                    cols_name[str(data[0])] = (data[1],int(data[2]))
                cr_db.execute("""SELECT
                        table_name, column_name, udt_name
                    from
                        INFORMATION_SCHEMA.columns
                    WHERE table_schema = 'public'""")
                for col in cr_db.fetchall():
                    val = {
                        'table_id': tables[col[0]],
                        'column_db_name': col[1],
                        'type': col[2],
                    }
                    id_made = filter(lambda x:(int(cols[x][1]) == int(tables[col[0]])),cols)
                    if col[0] in tables.keys() and col[1] in cols_name.keys() and id_made:
                        if table_col[str(tables[col[0]])][0] and col[1] in table_col[str(tables[col[0]])][0].keys():
                            col_id = tcol.write(cr,uid,table_col[str(tables[col[0]])][0][col[1]],val,context)
                        else:
                            val['name'] = col[1]
                            id_made = tcol.create(cr,uid,val,context)
                            cols[str(id_made)] = (val['name'],int(val['table_id']))
                    else:
                        val['name'] = col[1]
                        id_made = tcol.create(cr,uid,val,context)
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
                    val = {
                        'primary_key':True
                    }

                    id_to_write = filter(lambda x:(int(cols[x][1]) == int(tables[constraint[0]])and(constraint[1] == cols[x][0])),cols)
                    col_id = tcol.write(cr,uid,int(id_to_write[0]),val,context)

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
                for_key = dict(cr_db.fetchall())

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
                    val = {
                        'related_to':tables[for_key[constraint[2]]]
                    }
                    id_to_write = filter(lambda x:(int(cols[x][1]) == int(tables[constraint[0]])and (constraint[1] == cols[x][0])),cols)
                    if id_to_write:
                        col_id = tcol.write(cr,uid,int(id_to_write[0]),val,context)


            elif type == 'mysql':
                try:
                    import MySQLdb
                    host = lines.database_id.db_host or ''
                    port = lines.database_id.db_port or ''
                    db = lines.database_id.db_name or ''
                    user = lines.database_id.db_login or ''
                    passwd = lines.database_id.db_password or ''
                    tdb = MySQLdb.connect(host = host,port = port,db = db,user = user,passwd = passwd)

                except Exception,e:
                    raise osv.except_osv('MySQLdb Packages Not Installed.',e)

                cr_db = tdb.cursor()
                cr.execute('select table_db_name,id from olap_database_tables where fact_database_id=%d',(id_db,))
                tables = dict(cr.fetchall())
                tables_id = map(lambda x: str(tables[x]),tables)
                cols = {}
                if tables_id:
                    cr.execute('select column_db_name,id,table_id from olap_database_columns where table_id in (' + ','.join(tables_id) + ')')
                else:
                    cr.execute('select column_db_name,id,table_id from olap_database_columns')

                for data in cr.fetchall():
                    cols[str(data[1])] = (data[0],int(data[2]))
                cr_db.execute("select table_name, table_catalog from INFORMATION_SCHEMA.tables where table_schema =%s",(db_name))

                for table in cr_db.fetchall():
                    val = {
                        'fact_database_id':id_db,
                        'table_db_name':table[0]
                    }

                    if table[0] in tables.keys():
                        table_id = tobj.write(cr,uid,[tables[table[0]]],val,context)

                    else:
                        val['name'] = table[0]
                        tables[val['name']] = tobj.create(cr,uid,val,context)
                cr_db.execute("""SELECT
                        table_name, column_name, data_type
                    from
                        INFORMATION_SCHEMA.columns
                    WHERE table_schema = %s""",(db_name))

                for col in cr_db.fetchall():

                    val = {
                        'table_id': tables[col[0]],
                        'column_db_name': col[1],
                        'type': col[2],
                    }

                    id_made = filter(lambda x:(int(cols[x][1]) == int(tables[col[0]])),cols)
                    if col[1] in cols.keys() and col[0] in tables.keys()and id_made:
                        col_id = tcol.write(cr,uid,cols[tables[str(col[0])]],val,context)
                    else:
                        val['name'] = col[1]
                        id_made = tcol.create(cr,uid,val,context)
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
        #            lines=pool.get('olap.schema').browse(cr, uid, part['id'],context)
                for constraint in cr_db.fetchall():

                    if constraint[0]:
                        val = {
                             'related_to':tables[constraint[1]]
                             }
                    else:

                        val = {
                             'primary_key':True
                             }
                    id_to_write = filter(lambda x:(int(cols[x][1]) == int(tables[constraint[3]])and(constraint[2] == cols[x][0])),cols)
                    col_id = tcol.write(cr,uid,int(id_to_write[0]),val,context)

            elif type == 'oracle':
                try:
                    import cx_Oracle
                    host = lines.database_id.db_host or ''
                    port = lines.database_id.db_port or ''
                    db = lines.database_id.db_name or ''
                    user = lines.database_id.db_login.upper() or ''
                    passwd = lines.database_id.db_password or ''
                    tdb = cx_Oracle.connect(user,passwrd,host)

                except Exception,e:
                            raise osv.except_osv('cx_Oracle Packages Not Installed.',e)

                cr_db = tdb.cursor()
                cr.execute('select table_db_name,id from olap_database_tables where fact_database_id=%d',(id_db,))
                tables = dict(cr.fetchall())
                tables_id = map(lambda x: str(tables[x]),tables)
                cols = {}
                if tables_id:
                    cr.execute('select column_db_name,id,table_id from olap_database_columns where table_id in (' + ','.join(tables_id) + ')')
                else:
                    cr.execute('select column_db_name,id,table_id from olap_database_columns')

                for data in cr.fetchall():
                    cols[str(data[1])] = (data[0],int(data[2]))

                cr_db.execute("select table_name from all_tables where owner =%s",(user))
                temp = cr_db.fetchall()
                for table in temp:
                    val = {
                        'fact_database_id':id_db,
                        'table_db_name':table[0]
                    }

                    if table[0] in tables.keys():
                        table_id = tobj.write(cr,uid,[tables[table[0]]],val,context)

                    else:
                        val['name'] = table[0]
                        tables[val['name']] = tobj.create(cr,uid,val,context)

                cr_db.execute("""SELECT
                        table_name, column_name, data_type
                    from
                        all_tab_columns 
                    WHERE owner = %s""",(user))
                temp = cr_db.fetchall()
                for col in temp:
                    if col[2] == 'NUMBER':
                        type_col = 'numeric'
                    elif col[2] == 'DATE':
                        type_col = 'date'
                    elif col[2] == 'VARCHAR2':
                        type_col = 'varchar'
                    else:
                        type_col = col[2]
                    val = {
                        'table_id': tables[col[0]],
                        'column_db_name': col[1],
                        'type': type_col,
                    }

                    id_made = filter(lambda x:(int(cols[x][1]) == int(tables[col[0]])),cols)
                    if col[1] in cols.keys() and col[0] in tables.keys()and id_made:
                        col_id = tcol.write(cr,uid,cols[tables[str(col[0])]],val,context)
                    else:
                        val['name'] = col[1]
                        id_made = tcol.create(cr,uid,val,context)
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
                    val = {
                        'primary_key' : True
                    }
                    pk_table[constraint[2]] = constraint[0]

                    id_to_write = filter(lambda x : (int(cols[x][1]) == int(tables[constraint[0]])and(constraint[1] == cols[x][0])),cols)
                    col_id = tcol.write(cr,uid,int(id_to_write[0]),val,context)

                cr_db.execute("""select 
                                constraint_name,r_constraint_name from all_constraints
                                    where 
                                        constraint_type = 'R'  and owner = %s
                                    """,(user))
                constraints_map = {}
                for data in cr_db.fetchall():
                    constraints_map[data[0]] = data[1]

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
                    rel_constraint_name = constraints_map[constraint[2]]
                    req_table = pk_table[rel_constraint_name]
                    val = {
                        'related_to' : tables[req_table]
                    }
                    id_to_write = filter(lambda x:(int(cols[x][1]) == int(tables[constraint[0]])and (constraint[1] == cols[x][0])),cols)
                    col_id = tcol.write(cr,uid,int(id_to_write[0]),val,context)

            temp = pooler.get_pool(cr.dbname).get('olap.fact.database').write(cr,uid,[id_db],{'loaded':True})
            wf_service = netsvc.LocalService('workflow')
            wf_service.trg_validate(uid,'olap.schema',context['active_id'],'dbload',cr)
            model_data_ids = self.pool.get('ir.model.data').search(cr,uid,[('model','=','ir.ui.view'),('name','=','view_olap_schema_form')])
            resource_id = self.pool.get('ir.model.data').read(cr,uid,model_data_ids,fields = ['res_id'])[0]['res_id']

            return {'type':'ir.actions.act_window_close' }
#            return{
#           'domain': [],
#           'name': 'view_olap_schema_form',
#           'view_type': 'form',
#           'view_mode': 'form,tree',
#           'res_id': context['active_id'],
#           'res_model': 'olap.schema',
#           'view': [(resource_id,'form')],
#           'type': 'ir.actions.act_window_close'
#            }
#

    def action_cancel(self,cr,uid,ids,context = None):

        return {'type':'ir.actions.act_window_close' }

bi_load_db_wizard()



# Wizard for the Automatic Application Configuration
# Replacement for the Load Wizard according to the new structure
class bi_auto_configure_wizard(osv.osv_memory):
    _name = 'bi.auto.configure.wizard'


    def _get_name(self,cr,uid,ctx):
        if ctx and ctx.has_key('active_id'):
            schema_obj = self.pool.get('olap.schema').browse(cr,uid,ctx['active_id'])
            return schema_obj.name
        return False

    _columns = {
        'name':fields.char('Fact Name' ,size = 64,readonly = True),

        }

    _defaults = {
                   'name':_get_name,
                   }

    def action_load(self,cr,uid,ids,context = None):
        vals = {}
        apptabnew_vals = {}
        appfieldnew_vals = {}

        ids = pooler.get_pool(cr.dbname).get('olap.schema').browse(cr,uid,context['active_id'])

        if ids.app_detect == "Unknown Application":
            raise wizard.except_wizard('Warning','The Application is Unknown, we can not configure it automatically.')

        else:
            app_objs = pooler.get_pool(cr.dbname).get('olap.application')
            app_ids = app_objs.search(cr,uid,[])
            app_res = app_objs.browse(cr,uid,app_ids)
            app_id = ''
            for x_app in app_res:
                  app_id = x_app['id']

            apptab_objs = pooler.get_pool(cr.dbname).get('olap.application.table')
            apptab_ids = apptab_objs.search(cr,uid,[])
            apptab_res = apptab_objs.browse(cr,uid,apptab_ids)
            apptab_name = []
            map_apptab_name = {}
            map_apptab_name_id = {}
            for aptab in apptab_res:
                apptab_name.append(aptab.name)
                map_apptab_name_id[aptab.table_name] = aptab

            appfield_objs = pooler.get_pool(cr.dbname).get('olap.application.field')
            appfield_ids = appfield_objs.search(cr,uid,[])
            appfield_res = appfield_objs.browse(cr,uid,appfield_ids)
            appfield_data_res = appfield_objs.browse(cr,uid,appfield_ids)
            appcol_name = []
            for apcol in appfield_res:
                appcol_name.append(apcol.name)

            dbtab_obj = pooler.get_pool(cr.dbname).get('olap.database.tables')
#            id_tables=dbtab_obj.search(cr,uid,[('fact_database_id','=',ids.database_id.id),('table_db_name','not in',['inherit','res_roles','user_rule_group_rel','res_roles_users_rel','group_rule_group_rel'])])
            id_tables = dbtab_obj.search(cr,uid,[('fact_database_id','=',ids.database_id.id)])
            tables_main = dbtab_obj.read(cr,uid,id_tables,context = {'wizard':True})
            for tables in tables_main:
                end_user_name = {'name':(" ").join(map(lambda x:x.capitalize(),tables['table_db_name'].split("_")))}
                table_new = dbtab_obj.write(cr,uid,tables['id'],end_user_name)
                if not(tables['table_db_name'].startswith('ir') or tables['table_db_name'].startswith('wkf') or tables['table_db_name'].startswith('res_groups') or tables['table_db_name'].startswith('res_role')) and tables['table_db_name'] not in ['inherit','user_rule_group_rel','group_rule_group_rel']:
                    vals = {}

                    if len(apptab_ids) == 0 and (tables['table_db_name'] not in apptab_name):
                        vals['table_name'] = tables['table_db_name']
                        vals['name'] = (" ").join(map(lambda x:x.capitalize(),tables['name'].split("_")))
                        vals['is_hidden'] = tables['hide']
                        vals['application_id'] = app_id
                        table_new = dbtab_obj.write(cr,uid,tables['id'],{'hide':False})
                        apptab_new_obj = apptab_objs.create(cr,uid,vals)
                    else:
                        if map_apptab_name_id.has_key(tables['table_db_name']):
                            app_table = map_apptab_name_id[tables['table_db_name']]
                            if ((app_table['table_name'] == tables['table_db_name']) and not (app_table['table_name'] == tables['name'])):
                                vals['name'] = (" ").join(map(lambda x:x.capitalize(),tables['name'].split("_")))
                                vals['is_hidden'] = tables['hide']
                                tables_obj_new = apptab_objs.write(cr,uid,app_table['id'],vals)
                        else:
                            vals['table_name'] = tables['table_db_name']
                            vals['name'] = (" ").join(map(lambda x:x.capitalize(),tables['table_db_name'].split("_")))
                            vals['is_hidden'] = tables['hide']
                            vals['application_id'] = app_id
                            apptab_new_obj = apptab_objs.create(cr,uid,vals)
            id_columns = pooler.get_pool(cr.dbname).get('olap.database.columns').search(cr,uid,[('table_id','in',id_tables)])
            columns = pooler.get_pool(cr.dbname).get('olap.database.columns').read(cr,uid,id_columns,[])
            for columns in columns:
                vals = {}
                if len(appfield_ids) == 0 and (columns['column_db_name'] not in appcol_name):
                    vals['field_name'] = columns['column_db_name']
                    vals['table_name'] = columns['table_id'][1]
                    vals['name'] = (" ").join(map(lambda x:x.capitalize(),columns['name'].split("_")))
                    vals['is_hidden'] = columns['hide']
                    vals['application_id'] = x_app['id']
                    appfield_new_obj = appfield_objs.create(cr,uid,vals)
                else:
                    filter_column = filter(lambda x: columns['column_db_name'] == x['field_name'] and columns['table_id'][1] == x['table_name'],appfield_data_res)
                    if map_apptab_name_id.has_key(columns['table_id'][1]) and filter_column:
                        table_id_write = map_apptab_name_id[columns['table_id'][1]]
                        vals['name'] = (" ").join(map(lambda x:x.capitalize(),columns['name'].split("_")))
                        vals['is_hidden'] = columns['hide']
                        appfield_new_obj = appfield_objs.write(cr,uid,filter_column[0]['id'],vals)
                    else:
                        vals['field_name'] = columns['column_db_name']
                        vals['table_name'] = columns['table_id'][1]
                        vals['name'] = (" ").join(map(lambda x:x.capitalize(),columns['name'].split("_")))
                        vals['is_hidden'] = columns['hide']
                        vals['application_id'] = x_app['id']
                        appfield_new_obj = appfield_objs.create(cr,uid,vals)


            database_tables = pooler.get_pool(cr.dbname).get('olap.database.tables')
            id_tables = database_tables.search(cr,uid,[('fact_database_id','=',ids.database_id.id)])
            tables = database_tables.read(cr,uid,id_tables,[])
            make_id = []
            for table in tables:
                vals = {}
                if (table['table_db_name'].startswith('ir') or table['table_db_name'].startswith('wkf')) or (table['table_db_name'].startswith('res_groups')) or (table['table_db_name'] in ['inherit','res_roles','user_rule_group_rel','res_roles_users_rel','group_rule_group_rel']):
                    vals['hide'] = True
                    vals['active'] = False
                    make_id.append(table['id'])
                    database_tables.write(cr,uid,table['id'],vals)

            database_columns = pooler.get_pool(cr.dbname).get('olap.database.columns')
            id_columns = database_columns.search(cr,uid,[('table_id','in',make_id)])
            columns = database_columns.read(cr,uid,id_columns,[])
            for col in columns:
                val = {}
                vals['hide'] = True
                vals['active'] = False
                database_columns.write(cr,uid,col['id'],vals)


            wf_service = netsvc.LocalService('workflow')
            wf_service.trg_validate(uid,'olap.schema',context['active_id'],'dbconfigure',cr)
            model_data_ids = self.pool.get('ir.model.data').search(cr,uid,[('model','=','ir.ui.view'),('name','=','view_olap_schema_form')])
            resource_id = self.pool.get('ir.model.data').read(cr,uid,model_data_ids,fields = ['res_id'])[0]['res_id']

            return {'type':'ir.actions.act_window_close' }

    def action_cancel(self,cr,uid,ids,context = None):

        return {'type':'ir.actions.act_window_close' }

bi_auto_configure_wizard()


class olap_warehouse_wizard(osv.osv_memory):
    _name = "olap.warehouse.wizard"
    _description = "Olap Warehouse"
    
    def _get_queries(self, cr, uid, context = {}):
        query_obj = self.pool.get('olap.query.logs')
        qry_ids = query_obj.search(cr, uid, [('user_id','=',uid),('count','>=',3)])
        if qry_ids:
            query = ''
            for id in query_obj.browse(cr,uid,qry_ids,context):
                if query == '':
                    query = id.query
                else:
                    query = query + '\n'+id.query
            return query
        else:
            return ''
    def action_ok(self, cr, uid, ids, context = {}):
        return {'type':'ir.actions.act_window_close' }
    
    _columns = {
                'query': fields.text('Query', readonly=True),
                }
    _defaults = {
        'query': _get_queries,
        }
olap_warehouse_wizard()
class olap_parameters_config_wizard(osv.osv_memory):
    _name = "olap.parameters.config.wizard"
    _description = "Olap Server Parameters"

    def _get_host(self,cr,uid,context = None):
        obj = self.pool.get('olap')
        objid = self.pool.get('ir.model.data')
        aid = objid._get_id(cr,uid,'olap','menu_url_cube_browser')
        aid = objid.browse(cr,uid,aid,context = context).res_id
        aid = self.pool.get('ir.actions.url').browse(cr,uid,aid,context = context)
        s_p = Literal("http://").suppress() + Word(alphanums + "_" + ".") + Literal(":").suppress() + Word(nums) + Literal("/").suppress() + Word(alphanums + "_" + " ").suppress()
        return s_p.parseString(aid.url)[0]

    def _get_port(self,cr,uid,context = None):
        obj = self.pool.get('olap')
        objid = self.pool.get('ir.model.data')
        aid = objid._get_id(cr,uid,'olap','menu_url_cube_browser')
        aid = objid.browse(cr,uid,aid,context = context).res_id
        aid = self.pool.get('ir.actions.url').browse(cr,uid,aid,context = context)
        s_p = Literal("http://").suppress() + Word(alphanums + "_" + ".") + Literal(":").suppress() + Word(nums) + Literal("/").suppress() + Word(alphanums + "_" + " ").suppress()
        return s_p.parseString(aid.url)[1]

    _columns = {
        'host_name' : fields.char('Server Name',size = 64,help = "Put here the server address or IP \
                Put localhost if its not clear.",required = True),
        'host_port' : fields.char('Port',size = 4,help = "Put the port for the server. Put 8080 if \
                its not clear.",required = True),
            }

    _defaults = {
        'host_name': _get_host,
        'host_port': _get_port,
        }

    def action_cancel(self,cr,uid,ids,conect = None):
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
         }

    def action_config(self,cr,uid,ids,context = None):
        conf = self.browse(cr,uid,ids[0],context)
        obj = self.pool.get('olap')
        objid = self.pool.get('ir.model.data')
        aid = objid._get_id(cr,uid,'olap','menu_url_cube_browser')
        aid = objid.browse(cr,uid,aid,context = context).res_id
        self.pool.get('ir.actions.url').write(cr,uid,[aid],{'url': 'http://' + (conf.host_name or 'localhost') + ':' + (conf.host_port or '8080') + '/browser'})

        aid = objid._get_id(cr,uid,'olap','menu_url_cube_designer')
        aid = objid.browse(cr,uid,aid,context = context).res_id
        self.pool.get('ir.actions.url').write(cr,uid,[aid],{'url': 'http://' + (conf.host_name or 'localhost') + ':' + (conf.host_port or '8080') + '/designer'})

        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
        }
olap_parameters_config_wizard()

# vim: ts=4 sts=4 sw=4 si et
