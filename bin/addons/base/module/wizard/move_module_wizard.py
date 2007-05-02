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

move_module_form = '''<?xml version="1.0"?>
<form string="Transfer Module">
    <field name="fromurl" colspan="4"/>
    <newline/>
    <label/>
    <label> Give full path of Directory </label>
    <newline/>
    <field name="tourl" colspan="4"/>
    <newline/>
    <label/>
    <label> Give full path with zip file name and .zip extension </label>
</form>'''

move_module_fields = {
    'fromurl': {'string':'Model Name', 'type':'char', 'size':128, 'required':True },
    'tourl': {'string':'Server URL', 'type':'char', 'size':128 , 'required':True},
}
finish_form ='''<?xml version="1.0"?>
<form string="Finish">
    <label string="Module Zipped successfully !!!" colspan="4"/>
</form>
'''

class move_module_wizard(wizard.interface):
    def createzip(self, cr, uid, data, context):
        try:
            fromurl = data['form']['fromurl']
            tourl = data['form']['tourl'];
            if (sys.platform.startswith('win')):
                include_terp="pkzip -r '%s' %s  -i \*terp*.*" % (tourl, ''.join(fromurl))
                exclude_py="pkzip -r '%s' %s  -x \*.py \*.svn*" % (tourl, ''.join(fromurl))
            elif (sys.platform.startswith('linux')):
                include_terp="zip -r '%s' %s  -i \*terp*.*" % (tourl, ''.join(fromurl))
                exclude_py="zip -r '%s' %s  -x \*.py \*.svn*" % (tourl, ''.join(fromurl))

            if os.system(include_terp) == 0:
                    print 'Successful backup to', tourl
            else:
                    print 'Backup FAILED'

            if os.system(exclude_py) == 0:
                    print 'Successful backup to', tourl
            else:
                    print 'Backup FAILED'

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


    def _init_wizard(self, cr, uid, data, context):
        return {'fromurl':'/home/admin/Desktop/project','tourl':'/home/admin/Desktop/supportzip/myzip.zip'}


    states = {
        'init': {
            'actions': [_init_wizard],
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
