import wizard
import osv
from datetime import date
import time
import pooler
import xmlrpclib
import re
import os
import sys
import string
from zipfile import ZipFile, ZIP_DEFLATED

move_module_form = '''<?xml version="1.0"?>
<form string="Transfer Module">
    <field name="module_name" colspan="4"/>
    <newline/>
    <newline/>
</form>'''

finish_form ='''<?xml version="1.0"?>
<form string="Finish">
    <label string="Module Zipped successfully !!!" colspan="4"/>
</form>
'''

class move_module_wizard(wizard.interface):
    def _get_module(self, cr, uid, context):
        module_obj=pooler.get_pool(cr.dbname).get('ir.module.module')
        ids=module_obj.search(cr, uid, [])
        modules=module_obj.browse(cr, uid, ids)
        return [(modules_rec.name,modules_rec.name) for modules_rec in modules]

    def zippy(self,path, archive):
        paths = os.listdir(path)
        for p in paths:
            if p=='.svn':
                continue
            p = os.path.join(path, p) # Make the path relative
            if os.path.isdir(p): # Recursive case
                self.zippy(p, archive)
            else:
                ext=p.split('/')
                if ext[len(ext)-1]=='__terp__.py':
                    archive.write(p)
                    continue
                ext=p.split('.')[1]
                if ext=='py':
                    continue
                archive.write(p) # Write the file to the zipfile
        return

    def zipit(self,path, archname):
        # Create a ZipFile Object primed to write
        archive = ZipFile(archname, "w", ZIP_DEFLATED) # "a" to append, "r" to read
        # Recurse or not, depending on what path is
        if os.path.isdir(path):
            self.zippy(path, archive)
        else:
            archive.write(path)
        archive.close()
        return "Compression of \""+path+"\" was successful!"

    def createzip(self, cr, uid, data, context):
        try:
            fromurl=os.getcwd()
            fromurl=fromurl+'/addons/'+data['form']['module_name']
            tourl = fromurl+'.zip'
            status=self.zipit(fromurl,tourl)

        except Exception,e:

            if hasattr(e,'args'):
                print "Items::",e.args;
                if len(e.args) == 2:
                    if e.args[0] == -2:
                        return 'wrong_server_name'
                    #end if e.args[0] == -2:
                else:
                    return 'wrong_server_name'
                #end if len(e.args) == 2:
            #end if hasattr(e,'args'):

            return 'wrong_server_name'
        return 'finish'

    #end def createzip(self, cr, uid, data, context):

    move_module_fields = {
        'module_name': {'string':'Module Name', 'type':'selection', 'selection':_get_module,'required':True},

    }

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':move_module_form, 'fields':move_module_fields, 'state':[('end','Cancel'),('makezip','Create Zip')]}
        },
        'makezip': {
            'actions': [],
            'result':{'type':'choice', 'next_state': createzip}
        },
        'finish':{
            'actions': [],
            'result':{'type':'form', 'arch':finish_form,'fields':{},'state':[('end','OK')]}
                  }
    }
move_module_wizard('tmp.wizard')
