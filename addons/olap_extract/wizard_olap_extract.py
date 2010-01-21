# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

import wizard
import pooler
import csv
import os
import time
import netsvc
import zipfile


form1 = '''<?xml version="1.0"?>
<form string="New Module Name">
    <field name='module_name'/>
</form>'''

field1 = {
    'module_name': {'string':'Module Name', 'type':'char','size':'64', 'required':True},
}


class wizard_olap_extract(wizard.interface):
    
    def zipper(self,zipname,filename,mode="a"):
        z = zipfile.ZipFile(zipname+".zip", mode)
        z.write(filename)
        print "\n",z.printdir()
 
    
    def write_csv(self,filename,content=[]):
        fid = open(filename, 'w')        
        if fid == -1:
            print 'File: temp.csv not found or could not be opened'
            return False
        else:
            writer=csv.writer(fid, 'TINY',delimiter=',')
            for row in content:
                writer.writerow(row)
            fid.close    
        return True
    
    def table_depth(self,cr,uid,list=[],context={}):

        res={}
        templeft={}
        tempright={}
        for table_id in list:
            lines=pooler.get_pool(cr.dbname).get('olap.cube.table').browse(cr, uid,table_id,context)            
            res[str(lines.id)] = ["cubetable_"+str(lines.id),lines.name and lines.name or '',lines.table_alias and lines.table_alias or '',lines.key_left and lines.key_left or '',lines.key_right and lines.key_right or '',lines.table_left_id.id and "cubetable_"+str(lines.table_left_id.id) or '',lines.table_right_id.id and "cubetable_"+str(lines.table_right_id.id) or '']
            if(lines.table_left_id.id):
                templeft = self.table_depth(cr,uid,[lines.table_left_id.id],context)
        
                if templeft:
                    for temp in templeft:
                        if not res.has_key(temp):
                            res[temp]= templeft[temp]


            if(lines.table_right_id.id):
                tempright = self.table_depth(cr,uid,[lines.table_right_id.id],context) 
        
                if tempright:
                    for temp in tempright:
                        if not res.has_key(temp):
                            res[temp]= tempright[temp]
        return res
        
    
    def _extract_schema(self, cr, uid, data, context={}):

        _name = data['form']['module_name']
        _modulename = "olap_"+_name
        
        dirname = _modulename
        if not os.path.isdir("./addons/" + dirname + "/"):
            os.mkdir("./addons/" + dirname + "/")        
        
        os.chdir("./addons/"+dirname)

        _init = "import %s" % _modulename
        f = open("__init__.py","w")
        f.write(_init)
        f.close()
        self.zipper(_modulename, "__init__.py","w")
        
        _init_files = {
                       "1":"olap.fact.database.csv",
                       "2":"olap.schema.csv",
                       "5":"olap.cube.table.csv",
                       "6":"olap.cube.csv",
                       "7":"olap.dimension.csv",
                       "8":"olap.hierarchy.csv",
                       "9":"olap.level.csv",
                       "10":"olap.measure.csv"                    
                       }        
        _init_xml = """"%(1)s",
                    "%(2)s",
                    "%(5)s",
                    "%(6)s",
                    "%(7)s",
                    "%(8)s",
                    "%(9)s",
                    "%(10)s",
        """ % _init_files
        
        data['modulename'] = _modulename
        data['init_xml'] = _init_xml

        _terp= """{
                "name" : "%(modulename)s",
                "version" : "0.1",
                "author" : "Tiny",
                "website" : "http://tinyerp.com/",
                "depends" : ["olap"],
                "category" : "Generic Modules/Others",
                "description": "Module will load the data in olap tables",
                "init_xml" :[
                    %(init_xml)s
                    ],
                "update_xml" : [],
                "demo_xml" : [],
                "active": False,
                "installable": True
            }"""%data

        f = open("__terp__.py","w")
        f.write(_terp)
        f.close()        
        self.zipper(_modulename, "__terp__.py")  
                  

        schema_id = data['id']

        lines=pooler.get_pool(cr.dbname).get('olap.schema').browse(cr, uid, schema_id,context)
        
        _extract=[]
        _extract.append(['id','name','db_name','db_login','db_password'])
        _extract.append(["db_"+str(lines.database_id.id),lines.database_id.name,lines.database_id.db_name,lines.database_id.db_login,lines.database_id.db_password])
        self.write_csv('olap.fact.database.csv',_extract)
        self.zipper(_modulename, "olap.fact.database.csv")
        
        _extract=[]
        _extract.append(['id','name','database_id:id','loaded','configure','ready','state','note'])
        _extract.append(["schema_"+str(lines.id),lines.name,"db_"+str(lines.database_id.id),lines.loaded and lines.loaded or '',lines.configure and lines.configure or '', lines.ready and lines.ready or '',lines.state,lines.note and lines.note or ''])
        self.write_csv('olap.schema.csv',_extract)
        self.zipper(_modulename, "olap.schema.csv")                
        
        cube_ids = lines.cube_ids
        _extractcubes=[]
        _extractcubes.append(['id','name','table_id:id','schema_id:id'])
        
        _extractmeasures=[]
        _extractmeasures.append(['id','name','cube_id:id','value_column','value_sql','agregator','datatype','formatstring'])        
        
        _extractdimension=[]
        _extractdimension.append(['id','name','foreign_key','foreign_key_table','cube_id:id'])
        
        _extracthiers=[]
        _extracthiers.append(['id','name','primary_key','primary_key_table','field_name','member_all','member_default','sequence','type','dimension_id:id','table_id:id'])

        _extractlevels=[]
        _extractlevels.append(['id','name','column_name','column_id_name','type','table_name','sequence','hierarchy_id:id'])

        _cube_table_ids = []
        for cube in cube_ids:
            _extractcubes.append(["cube_"+str(cube.id),cube.name,"cubetable_"+str(cube.table_id.id),"schema_"+str(cube.schema_id.id)])    
            _cube_table_ids.append(cube.table_id.id)   
            
            measure_ids = cube.measure_ids
            for measure in measure_ids:
                _extractmeasures.append(["msr_"+str(measure.id),measure.name,"cube_"+str(measure.cube_id.id),measure.value_column and measure.value_column or '',measure.value_sql and measure.value_sql or '',measure.agregator,measure.datatype and measure.datatype or '',measure.formatstring])        
            
            dimension_ids = cube.dimension_ids
            for dimension in dimension_ids:
                _extractdimension.append(["dim_"+str(dimension.id),dimension.name,dimension.foreign_key and dimension.foreign_key or '',dimension.foreign_key_table and dimension.foreign_key_table or '',"cube_"+str(dimension.cube_id.id)])
                
                hiers_ids = dimension.hierarchy_ids
                for hier in hiers_ids:
                    _extracthiers.append(["hier_"+str(hier.id),hier.name,hier.primary_key,hier.primary_key_table and hier.primary_key_table or '',hier.field_name,hier.member_all,hier.member_default,hier.sequence,hier.type,"dim_"+str(hier.dimension_id.id),"cubetable_"+str(hier.table_id.id)])
                    _cube_table_ids.append(hier.table_id.id)
                    
                    level_ids = hier.level_ids
                    for level in level_ids:
                        _extractlevels.append(["lvl_"+str(level.id),level.name,level.column_name,level.column_id_name,level.type,level.table_name,level.sequence,"hier_"+str(level.hierarchy_id.id)])
                        
        res={}
        _extract=[]
        _extract.append(['id','name','table_alias','key_left','key_right','table_left_id:id','table_right_id:id'])
        res = self.table_depth(cr,uid,_cube_table_ids,context)
        key = res.keys()
        key = map(lambda x: int(x),key)
        key.sort()
        
        for k in key:
            _extract.append(res[str(k)])
        
        self.write_csv('olap.cube.csv',_extractcubes)
        self.zipper(_modulename, "olap.cube.csv")
        
        self.write_csv('olap.measure.csv',_extractmeasures)
        self.zipper(_modulename, "olap.measure.csv")   
        
        self.write_csv('olap.dimension.csv',_extractdimension)
        self.zipper(_modulename, "olap.dimension.csv")
        
        self.write_csv('olap.hierarchy.csv',_extracthiers)
        self.zipper(_modulename, "olap.hierarchy.csv")      
        
        self.write_csv('olap.level.csv',_extractlevels)
        self.zipper(_modulename, "olap.level.csv")                                    

        self.write_csv('olap.cube.table.csv',_extract)
        self.zipper(_modulename, "olap.cube.table.csv")      

        return {}
        
    states = {
              
       'init': {
            'actions': [],
            'result': {'type':'form','arch':form1, 'fields':field1, 'state':[('end','Cancel'),('ok','OK')]}
        },              
              
        'ok' : {
            'actions' : [],
            'result' : {'type' : 'action' ,'action':_extract_schema,'state':'end'}
        }
      }

wizard_olap_extract('olap.extract.schema')
