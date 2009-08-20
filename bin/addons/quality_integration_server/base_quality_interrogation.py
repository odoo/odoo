# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import xmlrpclib
import ConfigParser
import optparse
import sys
import thread
import threading
import os
import time
import pickle
import base64

admin_passwd = 'admin'

def start_server(root_path, port, addons_path):
    if root_path:
        root_path += '/'
    os.system('python '+root_path+'openerp-server.py  --pidfile=openerp.pid  --port=%s --no-netrpc --addons-path=%s' %(str(port),addons_path))    
def clean():
    if os.path.isfile('openerp.pid'):
        ps = open('openerp.pid') 
        if ps:
            pid = int(ps.read())
            ps.close()  
            if pid:    
                os.kill(pid,9)

def login(uri, dbname, user, pwd):
    conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/common')
    uid = conn.login(dbname, user, pwd) 
    return uid

def import_translate(uri, user, pwd, dbname, translate_in):      
    uid = login(uri, dbname, user, pwd)    
    if uid:        
        conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/wizard')
        wiz_id = conn.create(dbname, uid, pwd, 'module.lang.import')
        for trans_in in translate_in:
            lang,ext = os.path.splitext(trans_in.split('/')[-1])                
            state = 'init'  
            datas = {'form':{}}
            while state!='end':                
                res = conn.execute(dbname, uid, pwd, wiz_id, datas, state, {})
                if 'datas' in res:
                    datas['form'].update( res['datas'].get('form',{}) )
                if res['type']=='form':
                    for field in res['fields'].keys():
                        datas['form'][field] = res['fields'][field].get('value', False)
                    state = res['state'][-1][0]
                    trans_obj = open(trans_in)
                    datas['form'].update({
                        'name': lang,
                        'code': lang,
                        'data' : base64.encodestring(trans_obj.read())
                    })
                    trans_obj.close()
                elif res['type']=='action':
                    state = res['state']                    
                
        
def check_quality(uri, user, pwd, dbname, modules):       
    uid = login(uri, dbname, user, pwd)
    if uid:
        conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/object')
        qualityresult = {}  
        final = {}   
        test_detail = {}
        for module in modules:            
            quality_result = conn.execute(dbname, uid, pwd,'module.quality.check','check_quality',module)
            detail_html = ''
            html = '''<html><html><html><html><body><a name="TOP"></a>'''
            html +="<h1> Module : %s </h1>"%(quality_result['name'])   
            html += "<h2> Final score : %s</h2>"%(quality_result['final_score'])
            html += "<oi>"
            for x,y,detail in quality_result['check_detail_ids']:
                if detail.get('detail') != '':
                    test = detail.get('name')
                    score = round(float(detail.get('score',0)),2)
                    html += "<li><a href=\"#%s\">%s (%.2f)</a></li>"%(test,test,score)
                    detail_html +="<a name=\"%s\"><h3>%s (Score : %s)</h3>%s</a>"%(test,test,score,detail.get('detail'))
                    detail_html +='''<a href="#TOP">Go to Top</a>'''
                    test_detail[test] = (score,detail.get('detail',''))
            html += "</oi>%s</body></html></html></html></html></html>"%(detail_html) 
            final[quality_result['name']] = (quality_result['final_score'],html,test_detail)

        fp = open('quality_log.pck','wb')
        pck_obj = pickle.dump(final,fp)
        fp.close()
        print "LOG PATH%s"%(os.path.realpath('quality_log.pck'))
        return final
    else:
        print 'Login Failed...'        
        clean()
        sys.exit(1)   



def wait(id,url=''):
    progress=0.0
    sock2 = xmlrpclib.ServerProxy(url+'/db')
    while not progress==1.0:
        progress,users = sock2.get_progress(admin_passwd, id)
    return True


def create_db(uri, dbname, user='admin', pwd='admin', lang='en_US'):
    conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/db')
    obj_conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/object')
    wiz_conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/wizard')
    login_conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/common')
    db_list = conn.list()
    if dbname not in db_list:
        id = conn.create(admin_passwd, dbname, True, lang) 
        wait(id,uri)
    uid = login_conn.login(dbname, user, pwd)   

    wiz_id = wiz_conn.create(dbname, uid, user, 'base_setup.base_setup')

    state = 'init'
    datas = {'form':{}}

    while state!='config':        
        res = wiz_conn.execute(dbname, uid, pwd, wiz_id, datas, state, {})
        if state=='init':
            datas['form'].update( res['datas'] )
        if res['type']=='form':
            for field in res['fields'].keys():               
                datas['form'][field] = datas['form'].get(field,False)
            state = res['state'][-1][0]
            datas['form'].update({
                'profile': -1                
            })
        elif res['type']=='state':
            state = res['state']
    res = wiz_conn.execute(dbname, uid, pwd, wiz_id, datas, state, {})
    install_module(uri, dbname, ['base_module_quality'],user,pwd)
    return True

def drop_db(uri, dbname):
    conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/db')
    db_list = conn.list()
    if dbname in db_list:
        conn.drop(admin_passwd, dbname)    
    return True

def install_module(uri, dbname, modules, user='admin', pwd='admin'):
    uid = login(uri, dbname, user, pwd)
    if uid: 
        obj_conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/object')
        wizard_conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/wizard')
        module_ids = obj_conn.execute(dbname, uid, pwd, 'ir.module.module', 'search', [('name','in',modules)])  
        obj_conn.execute(dbname, uid, pwd, 'ir.module.module', 'button_install', module_ids)           
        wiz_id = wizard_conn.create(dbname, uid, pwd, 'module.upgrade.simple')
        state = 'init'
        datas = {}
        #while state!='menu':
        while state!='end':                
            res = wizard_conn.execute(dbname, uid, pwd, wiz_id, datas, state, {})                
            if state == 'init':
                state = 'start'
            elif state == 'start':
                state = 'end'                                  
    return True

def upgrade_module(uri, dbname, modules, user='admin', pwd='admin'):
    uid = login(uri, dbname, user, pwd)
    if uid: 
        obj_conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/object')
        wizard_conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/wizard')        
        module_ids = obj_conn.execute(dbname, uid, pwd, 'ir.module.module', 'search', [('name','in',modules)])  
        obj_conn.execute(dbname, uid, pwd, 'ir.module.module', 'button_upgrade', module_ids)           
        wiz_id = wizard_conn.create(dbname, uid, pwd, 'module.upgrade.simple')
        state = 'init'
        datas = {}
        #while state!='menu':
        while state!='end':                
            res = wizard_conn.execute(dbname, uid, pwd, wiz_id, datas, state, {})                
            if state == 'init':
                state = 'start'
            elif state == 'start':
                state = 'end'                                  
                            
    return True





usage = """%prog command [options]

Basic Commands:
    start-server         Start Server
    create-db            Create new database
    drop-db              Drop database
    install-module       Install module 
    upgrade-module       Upgrade module
    install-translation  Install translation file
    check-quality        Calculate quality and dump quality result into quality_log.pck using pickle
"""
parser = optparse.OptionParser(usage)            
parser.add_option("--modules", dest="modules",
                     help="specify modules to install or check quality")
parser.add_option("--addons-path", dest="addons_path", help="specify the addons path")
parser.add_option("--root-path", dest="root_path", help="specify the root path")
parser.add_option("-p", "--port", dest="port", help="specify the TCP port", type="int")
parser.add_option("-d", "--database", dest="db_name", help="specify the database name")  
parser.add_option("--login", dest="login", help="specify the User Login") 
parser.add_option("--password", dest="pwd", help="specify the User Password")  
parser.add_option("--translate-in", dest="translate_in",
                     help="specify .po files to import translation terms")
(opt, args) = parser.parse_args()
if len(args) != 1:
    parser.error("incorrect number of arguments")
command = args[0]
if command not in ('start-server','create-db','drop-db','install-module','upgrade-module','check-quality','install-translation'):
    parser.error("incorrect command")    

def die(cond, msg):
    if cond:
        print msg
        sys.exit(1)

die(opt.modules and (not opt.db_name),
        "the modules option cannot be used without the database (-d) option")

die(opt.translate_in and (not opt.db_name),
        "the translate-in option cannot be used without the database (-d) option")

options = {
    'addons-path' : opt.addons_path or 'addons',
    'root-path' : opt.root_path or '',
    'translate-in': opt.translate_in,
    'port' : opt.port or 8069,        
    'database': opt.db_name or 'terp',
    'modules' : opt.modules or [],
    'login' : opt.login or 'admin',
    'pwd' : opt.pwd or '',
}

options['modules'] = opt.modules and map(lambda m: m.strip(), opt.modules.split(',')) or []
options['translate_in'] = opt.translate_in and map(lambda m: m.strip(), opt.translate_in.split(',')) or []
uri = 'http://localhost:' + str(options['port'])

server_thread = threading.Thread(target=start_server,
                args=(options['root-path'], options['port'], options['addons-path']))
try:    
    server_thread.start()   
    print 'Please wait 20 sec to start server....',uri
    time.sleep(20) 
    if command == 'create-db': 
        create_db(uri, options['database'], options['login'], options['pwd'])
    if command == 'drop-db': 
        drop_db(uri, options['database'])
    if command == 'install-module': 
        install_module(uri, options['database'], options['modules'], options['login'], options['pwd'])
    if command == 'upgrade-module': 
        upgrade_module(uri, options['database'], options['modules'], options['login'], options['pwd'])
    if command == 'check-quality':
        check_quality(uri, options['login'], options['pwd'], options['database'], options['modules'])
    if command == 'install-translation':        
        import_translate(uri, options['login'], options['pwd'], options['database'], options['translate_in'])
    clean()
    sys.exit(0)
    
except xmlrpclib.Fault, e:
    print e.faultString
    clean()
    sys.exit(1)
except Exception, e:
    print e
    clean()
    sys.exit(1)



