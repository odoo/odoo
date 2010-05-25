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

import wizard
import threading
import pooler
from osv import osv
import optparse
import xmlrpclib
import time

import netsvc



class Log:
    def __init__(self):
        self.content= ""
        self.error= False
    def add(self,s,error=True):
        self.content= self.content + s
        if error:
            self.error= error
    def __call__(self):
        return self.content


def get_cube(self, cr, uid, context):
        pool = pooler.get_pool(cr.dbname).get('olap.cube')
        ids = pool.search(cr, uid, [])
        res = pool.read(cr, uid, ids, ['schema_id','name'], context)
        res=[(r['schema_id'], r['name']) for r in res]

        return res

def get_details(self, cr, uid,data, context):
         """
         To Fetch dimension of selected schema
         """
         pool = pooler.get_pool(cr.dbname).get('olap.cube')

         search_id=data['form']['cube_schema'][0]

         ids=pool.search(cr,uid,[('schema_id','=',search_id)])

         """
         ids now have the cube id from schema user selected
         """

         """
         To Fetch hiearchy of selected schema
         """
         pool = pooler.get_pool(cr.dbname).get('olap.dimension')

         id_dimension=pool.search(cr,uid,[('cube_id','=',ids[0])])
         res=pool.read(cr,uid,id_dimension,['id','name'],context)
         log_d=Log()
         for r in res:
             log_d.add(r['name'])
             log_d.add("\n")


         """
         To Fetch hiearchy id
         """
         pool=pooler.get_pool(cr.dbname).get('olap.hierarchy')

         id_hierarchy=pool.search(cr,uid,[('dimension_id','in',tuple(id_dimension))])
         res=pool.read(cr,uid,id_hierarchy,['id','name'],context)
         log_h=Log()
         for r in res:
             log_h.add(r['name'])
             log_h.add("\n")



         """
         To fetch level id
         """
         pool=pooler.get_pool(cr.dbname).get('olap.level')
         id_level=pool.search(cr,uid,[('hierarchy_id','in',tuple(id_hierarchy))])
         res=pool.read(cr,uid,id_level,['id','name'],context)
         log_l=Log()
         for r in res:
             log_l.add(r['name'])
             log_l.add("\n")

         """
         To fetch measures id
         """
         pool=pooler.get_pool(cr.dbname).get('olap.measure')
         id_level=pool.search(cr,uid,[('cube_id','in',tuple(ids))])
         res=pool.read(cr,uid,id_level,['id','name'],context)
         log_m=Log()
         for r in res:
             log_m.add(r['name'])
             log_m.add("\n")


         return {'hierarchy':log_h(),'dimension':log_d(),'level':log_l(),'measure':log_m()}




query_builder_form = """<?xml version="1.0"?>
<form string="Query Builder">
 <field name="dimension"/>
 <field name="hierarchy"/>
 <field name="level"/>
 <field name="measure"/>
 <field name="mdx_query" colspan="4" height="100" width="800"/>
 <field name="mdx_query_output" colspan="4" height="100" width="800"/>
</form>"""
query_builder_fields={


                      'dimension':{'string':'Dimension','type':'text'},
                      'hierarchy':{'string':'Hiearchy','type':'text'},
                      'level':{'string':'Level','type':'text'},
                      'measure':{'string':'Measure','type':'text'},
                      'mdx_query':{'string':'MDX Query','type':'text'},
                      'mdx_query_output':{'string':'MDX Query Output','type':'text'},
                      }

query_builder_fetch_form = """<?xml version="1.0"?>
<form string="Cube Fetcher">
  <field name="cube_schema"/>
</form>"""

query_builder_fetch_fields = {
    'cube_schema':{'string':'Select Cube','type':'selection','selection':get_cube},
}



def _execute_mdx(self, cr, uid, data, context):

    log=Log()

    pool = pooler.get_pool(cr.dbname).get('olap.schema')
    ids = pool.search(cr, uid, [('database_id','=',data['form']['cube_schema'][0])])
    res1 = pool.read(cr, uid, ids,['name'], context)

    """
        doing same using request method of olap.schema
        creating the object of olpa.schema and using its request method for parsing the query
    """
    r=data['form']['mdx_query']
    n=res1[0]['name']
    service=netsvc.LocalService("object_proxy")
    axis,data1=service.execute(cr.dbname,uid,'olap.schema','request',n,r,context={})
    output=''

    COLSPAN = 18
    ROWSPAN = 18
    if len(axis)>1:
        for i in range(8):
            ok = False
            for x in axis[1]:
                if len(x[0])==i:
                    ok = True
            if not ok:
                   continue
            #print ' '*COLSPAN,
            output =' '*COLSPAN
            log.add(output)
           # print (('%-'+str(ROWSPAN)+'s ' ) * len(axis[1])) % tuple(map(lambda x: str(len(x[0])==i and x[1] or ''),axis[1]))
            output=(('%-'+str(ROWSPAN)+'s ' ) * len(axis[1])) % tuple(map(lambda x: str(len(x[0])==i and x[1] or ''),axis[1]))
            log.add(output)

        for col in data1:
            x=(' '*(len(axis[0][0][0])-1)*2)
            print "--------------------------------------",x
            temp=(axis[0].pop(0)[1])
            print "--------------------------------------",temp
          #  print ('%-'+str(COLSPAN)+'s')% (' '*(len(axis[0][0][0])-1)*2 + (temp),),
            output =('%-'+str(COLSPAN)+'s')% (str(x)+str(temp))
            log.add("\n")
            log.add(output)
            #output=(temp)

            for row in col:
                if row==[False]:
          #          print ('%-'+str(ROWSPAN)+'s')%('',),
                    output=('%-'+str(ROWSPAN)+'s')%('')
                    log.add(output)

                else:
         #            print ('%-'+str(ROWSPAN)+'s')%(row,),
                     output=('%-'+str(ROWSPAN)+'s')%(row)
                     log.add(output)
        #print
        log.add("\n")
    return {'mdx_query_output':log()}

class wizard_query_builder(wizard.interface):
    states = {
        'init' : {
            'actions' : [],
            'result' : {'type':'form', 'arch':query_builder_fetch_form, 'fields':query_builder_fetch_fields, 'state':[('ok', 'Fetch Data')]}
        },
        'ok':{
            'actions' : [get_details],
            'result' : {'type':'form', 'arch':query_builder_form, 'fields':query_builder_fields, 'state':[('back','Change cube'),('exec', 'Execute'),('end', 'Cancel')]}
              },

        'exec': {
            'actions': [_execute_mdx],
            'result': {'type':'form','arch':query_builder_form,'fields':query_builder_fields,'state':[('back','Change cube'),('exec', 'Execute'),('end', 'Cancel')]},
        },
        'back':{
            'actions':[],
            'result':{'type':'form','arch':query_builder_fetch_form,'fields':query_builder_fetch_fields,'state':[('ok', 'Fetch Data')]},
        },
    }
wizard_query_builder('olap.query_builder')