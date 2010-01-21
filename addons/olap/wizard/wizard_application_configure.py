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
import time

import wizard
import pooler
from osv import osv
import netsvc

info = '''<?xml version="1.0"?>
<form string="Auto Configure">
    <label string="Your database structure (Open ERP) has been sucessfully configured."/>
</form>'''

form1 = '''<?xml version="1.0"?>
<form string=" Auto Configure ">
    <label string="This will Auto Configure Application"/>
</form>'''

class wizard_application_configure(wizard.interface):
    
    def configure_application(self,cr,uid,data,context):
        
        vals={}
        apptabnew_vals={}
        appfieldnew_vals={}
        
        ids=pooler.get_pool(cr.dbname).get('olap.schema').browse(cr,uid,data['id'])
        
        if ids.app_detect == "Unknown Application":
            raise wizard.except_wizard('Warning', 'The Application is Unknown, we can not configure it automatically.')

        else:
            app_objs = pooler.get_pool(cr.dbname).get('olap.application')
            app_ids = app_objs.search(cr, uid, [])
            app_res = app_objs.browse(cr,uid, app_ids)
            app_id=''
            for x_app in app_res:
                  app_id = x_app['id']
                  
            apptab_objs = pooler.get_pool(cr.dbname).get('olap.application.table')
            apptab_ids = apptab_objs.search(cr, uid, [])
            apptab_res = apptab_objs.browse(cr,uid, apptab_ids)
            apptab_name=[]
            for aptab in apptab_res:
                apptab_name.append(aptab.name)

            appfield_objs = pooler.get_pool(cr.dbname).get('olap.application.field')
            appfield_ids = appfield_objs.search(cr, uid, [])
            appfield_res = appfield_objs.browse(cr,uid, appfield_ids)
            appcol_name=[]
            for apcol in appfield_res:
                appcol_name.append(apcol.name)
            

            apptab_objs = pooler.get_pool(cr.dbname).get('olap.application.table')
            apptab_ids = apptab_objs.search(cr, uid, [])
            apptab_res = apptab_objs.browse(cr,uid, apptab_ids)
#            apptab_data_res = apptab_objs.read(cr,uid, apptab_ids,[])[0]
            
            apptab_name=[]
            map_apptab_name_id={}
            for aptab in apptab_res:
                apptab_name.append(aptab.name)
                map_apptab_name_id[aptab.table_name]=aptab
            
            appfield_objs = pooler.get_pool(cr.dbname).get('olap.application.field')
            appfield_ids = appfield_objs.search(cr, uid, [])
            appfield_res = appfield_objs.browse(cr,uid, appfield_ids)
            appfield_data_res = appfield_objs.read(cr,uid, appfield_ids,[])
            
            appcol_name=[]
            for apcol in appfield_res:
                appcol_name.append(apcol.name)
                
            id_tables=pooler.get_pool(cr.dbname).get('olap.database.tables').search(cr,uid,[('fact_database_id','=',ids.database_id.id),('table_db_name','not in',['inherit','res_roles','user_rule_group_rel','res_roles_users_rel','group_rule_group_rel'])])
            tables=pooler.get_pool(cr.dbname).get('olap.database.tables').read(cr,uid,id_tables,[])
            
            for tables in tables:
                if not(tables['table_db_name'].startswith('ir') or tables['table_db_name'].startswith('wkf') or tables['table_db_name'].startswith('res_groups')):
                    vals={}
                    if len(apptab_ids)==0 and (tables['table_db_name'] not in apptab_name):
                        vals['table_name']=tables['table_db_name']
                        vals['name']=(" ").join(map(lambda x:x.capitalize(),tables['name'].split("_")))
                        vals['is_hidden']=tables['hide']
                        vals['application_id']=app_id
                        apptab_new_obj=apptab_objs.create(cr,uid,vals)
                    else:
                        if map_apptab_name_id.has_key(tables['table_db_name']):
                            app_table = map_apptab_name_id[tables['table_db_name']]
                            if ((app_table['table_name']==tables['table_db_name']) and not (app_table['table_name']==tables['name'])):
                                vals['name']=aptable_obj.table_name
                                vals['hide']=aptable_obj.is_hidden
                                tables_obj_new=apptab_objs.write(cr,uid,tables['id'],vals)
                        else:
                            vals['table_name']=tables['table_db_name']
                            vals['name']=(" ").join(map(lambda x:x.capitalize(),tables['name'].split("_")))
                            vals['is_hidden']=tables['hide']
                            vals['application_id']=app_id
                            apptab_new_obj=apptab_objs.create(cr,uid,vals)
                    
            id_columns=pooler.get_pool(cr.dbname).get('olap.database.columns').search(cr,uid,[('table_id','in',id_tables)])
            columns=pooler.get_pool(cr.dbname).get('olap.database.columns').read(cr,uid,id_columns,[])
            for columns in columns:
                vals={}
                if len(appfield_ids) == 0 and (columns['column_db_name'] not in appcol_name):
                    vals['field_name']=columns['column_db_name']
                    vals['table_name']=columns['table_id'][1]
                    vals['name']=(" ").join(map(lambda x:x.capitalize(),columns['name'].split("_")))
                    vals['is_hidden']=columns['hide']
                    vals['application_id']=x_app['id']                      
                    appfield_new_obj=appfield_objs.create(cr,uid,vals)
                else:
                    if map_apptab_name_id.has_key(columns['table_id'][1]):
                        table_id_write = map_apptab_name_id[columns['table_id'][1]]
                        filter_column=filter(lambda x: columns['column_db_name']==x['field_name'] and columns['table_id'][1]==x['table_name'],appfield_data_res)
                        vals['name']=(" ").join(map(lambda x:x.capitalize(),columns['name'].split("_")))
                        vals['is_hidden']=columns['hide']
                        appfield_new_obj=appfield_objs.write(cr,uid,filter_column[0]['id'],vals)
                    else:
                        vals['field_name']=columns['column_db_name']
                        vals['table_name']=columns['table_id'][1]
                        vals['name']=(" ").join(map(lambda x:x.capitalize(),columns['name'].split("_")))
                        vals['is_hidden']=columns['hide']
                        vals['application_id']=x_app['id']                      
                        appfield_new_obj=appfield_objs.create(cr,uid,vals)
        
        
            database_tables = pooler.get_pool(cr.dbname).get('olap.database.tables')
            id_tables=database_tables.search(cr,uid,[('fact_database_id','=',ids.database_id.id)])
            tables=database_tables.read(cr,uid,id_tables,[])
            make_id=[]
            for table in tables:
                vals={}
                if (table['table_db_name'].startswith('ir') or table['table_db_name'].startswith('wkf')) or (table['table_db_name'].startswith('res_groups')) or (table['table_db_name'] in ['inherit','res_roles','user_rule_group_rel','res_roles_users_rel','group_rule_group_rel']):            
                    vals['hide']=True
                    vals['active']=False
                    make_id.append(table['id'])
                    database_tables.write(cr,uid,table['id'],vals)
                    
            database_columns=pooler.get_pool(cr.dbname).get('olap.database.columns')
            id_columns=database_columns.search(cr,uid,[('table_id','in',make_id)])
            columns=database_columns.read(cr,uid,id_columns,[])
            for col in columns:
                val={}
                vals['hide']=True
                vals['active']=False
                database_columns.write(cr,uid,col['id'],vals)
                
            
        wf_service = netsvc.LocalService('workflow')
        wf_service.trg_validate(uid, 'olap.schema', data['id'], 'dbconfigure', cr)
        return {}
      
    
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':form1, 'fields':{}, 'state':[('configure','Configure'),('end','Cancel')]}
        },
        'configure': {
            'actions': [configure_application],
            'result': {'type':'form', 'arch':info, 'fields':{}, 'state':[('end','Ok')]}   
        },

      }


wizard_application_configure('olap.application.configuration')
# vim: ts=4 sts=4 sw=4 si et
