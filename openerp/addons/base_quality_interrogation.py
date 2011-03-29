# -*- coding: utf-8 -*-
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
import socket

admin_passwd = 'admin'
waittime = 10
wait_count = 0
wait_limit = 12

def to_decode(s):
    try:
        return s.encode('utf-8')
    except UnicodeError:
        try:
            return s.encode('latin')
        except UnicodeError:
            try:
                return s.decode('ascii')
            except UnicodeError:
                return s

def start_server(root_path, port, netport, addons_path):
    os.system('python2.5 %sopenerp-server  --pidfile=openerp.pid  --no-xmlrpcs --xmlrpc-port=%s --netrpc-port=%s --addons-path=%s' %(root_path, str(port),str(netport),addons_path))
def clean():
    if os.path.isfile('openerp.pid'):
        ps = open('openerp.pid')
        if ps:
            pid = int(ps.read())
            ps.close()
            if pid:
                os.kill(pid,9)

def execute(connector, method, *args):
    global wait_count
    res = False
    try:
        res = getattr(connector,method)(*args)
    except socket.error,e:
        if e.args[0] == 111:
            if wait_count > wait_limit:
                print "Server is taking too long to start, it has exceeded the maximum limit of %d seconds."%(wait_limit)
                clean()
                sys.exit(1)
            print 'Please wait %d sec to start server....'%(waittime)
            wait_count += 1
            time.sleep(waittime)
            res = execute(connector, method, *args)
        else:
            raise e
    wait_count = 0
    return res

def login(uri, dbname, user, pwd):
    conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/common')
    uid = execute(conn,'login',dbname, user, pwd)
    return uid

def import_translate(uri, user, pwd, dbname, translate_in):
    uid = login(uri, dbname, user, pwd)
    if uid:
        conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/wizard')
        wiz_id = execute(conn,'create',dbname, uid, pwd, 'base.language.import')
        for trans_in in translate_in:
            lang,ext = os.path.splitext(trans_in.split('/')[-1])
            state = 'init'
            datas = {'form':{}}
            while state!='end':
                res = execute(conn,'execute',dbname, uid, pwd, wiz_id, datas, state, {})
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


def check_quality(uri, user, pwd, dbname, modules, quality_logs):
    uid = login(uri, dbname, user, pwd)
    quality_logs += 'quality-logs'
    if uid:
        conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/object')
        final = {}
        for module in modules:
            qualityresult = {}
            test_detail = {}
            quality_result = execute(conn,'execute', dbname, uid, pwd,'module.quality.check','check_quality',module)
            detail_html = ''
            html = '''<html><body><a name="TOP"></a>'''
            html +="<h1> Module: %s </h1>"%(quality_result['name'])
            html += "<h2> Final score: %s</h2>"%(quality_result['final_score'])
            html += "<div id='tabs'>"
            html += "<ul>"
            for x,y,detail in quality_result['check_detail_ids']:
                test = detail.get('name')
                msg = detail.get('message','')
                score = round(float(detail.get('score',0)),2)
                html += "<li><a href=\"#%s\">%s</a></li>"%(test.replace(' ','-'),test)
                detail_html +='''<div id=\"%s\"><h3>%s (Score : %s)</h3><font color=red><h5>%s</h5></font>%s</div>'''%(test.replace(' ', '-'), test, score, msg, detail.get('detail', ''))
                test_detail[test] = (score,msg,detail.get('detail',''))
            html += "</ul>"
            html += "%s"%(detail_html)
            html += "</div></body></html>"
            if not os.path.isdir(quality_logs):
                os.mkdir(quality_logs)
            fp = open('%s/%s.html'%(quality_logs,module),'wb')
            fp.write(to_decode(html))
            fp.close()
            #final[quality_result['name']] = (quality_result['final_score'],html,test_detail)

        #fp = open('quality_log.pck','wb')
        #pck_obj = pickle.dump(final,fp)
        #fp.close()
        #print "LOG PATH%s"%(os.path.realpath('quality_log.pck'))
        return True
    else:
        print 'Login Failed...'
        clean()
        sys.exit(1)



def wait(id,url=''):
    progress=0.0
    sock2 = xmlrpclib.ServerProxy(url+'/xmlrpc/db')
    while not progress==1.0:
        progress,users = execute(sock2,'get_progress',admin_passwd, id)
    return True


def create_db(uri, dbname, user='admin', pwd='admin', lang='en_US'):
    conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/db')
    obj_conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/object')
    wiz_conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/wizard')
    login_conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/common')
    db_list = execute(conn, 'list')
    if dbname in db_list:
        drop_db(uri, dbname)
    id = execute(conn,'create',admin_passwd, dbname, True, lang)
    wait(id,uri)    
    install_module(uri, dbname, ['base_module_quality'],user=user,pwd=pwd)
    return True

def drop_db(uri, dbname):
    conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/db')
    db_list = execute(conn,'list')
    if dbname in db_list:
        execute(conn, 'drop', admin_passwd, dbname)
    return True

def make_links(uri, uid, dbname, source, destination, module, user, pwd):
    if module in ('base','quality_integration_server'):
        return True
    if os.path.islink(destination + '/' + module):
        os.unlink(destination + '/' + module)                
    for path in source:
        if os.path.isdir(path + '/' + module):
            os.symlink(path + '/' + module, destination + '/' + module)
            obj_conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/object')
            execute(obj_conn, 'execute', dbname, uid, pwd, 'ir.module.module', 'update_list')
            module_ids = execute(obj_conn, 'execute', dbname, uid, pwd, 'ir.module.module', 'search', [('name','=',module)])
            if len(module_ids):
                data = execute(obj_conn, 'execute', dbname, uid, pwd, 'ir.module.module', 'read', module_ids[0],['name','dependencies_id'])
                dep_datas = execute(obj_conn, 'execute', dbname, uid, pwd, 'ir.module.module.dependency', 'read', data['dependencies_id'],['name'])
                for dep_data in dep_datas:
                    make_links(uri, uid, dbname, source, destination, dep_data['name'], user, pwd)
    return False

def install_module(uri, dbname, modules, addons='', extra_addons='',  user='admin', pwd='admin'):
    uid = login(uri, dbname, user, pwd)
    if extra_addons:
        extra_addons = extra_addons.split(',')
    if uid:
        if addons and extra_addons:
            for module in modules:
                make_links(uri, uid, dbname, extra_addons, addons, module, user, pwd)

        obj_conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/object')
        wizard_conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/wizard')
        module_ids = execute(obj_conn, 'execute', dbname, uid, pwd, 'ir.module.module', 'search', [('name','in',modules)])
        execute(obj_conn, 'execute', dbname, uid, pwd, 'ir.module.module', 'button_install', module_ids)
        wiz_id = execute(wizard_conn, 'create', dbname, uid, pwd, 'module.upgrade.simple')
        state = 'init'
        datas = {}
        #while state!='menu':
        while state!='end':
            res = execute(wizard_conn, 'execute', dbname, uid, pwd, wiz_id, datas, state, {})
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
        module_ids = execute(obj_conn, 'execute', dbname, uid, pwd, 'ir.module.module', 'search', [('name','in',modules)])
        execute(obj_conn, 'execute', dbname, uid, pwd, 'ir.module.module', 'button_upgrade', module_ids)
        wiz_id = execute(wizard_conn, 'create', dbname, uid, pwd, 'module.upgrade.simple')
        state = 'init'
        datas = {}
        #while state!='menu':
        while state!='end':
            res = execute(wizard_conn, 'execute', dbname, uid, pwd, wiz_id, datas, state, {})
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
parser.add_option("--quality-logs", dest="quality_logs", help="specify the path of quality logs files which has to stores")
parser.add_option("--root-path", dest="root_path", help="specify the root path")
parser.add_option("-p", "--port", dest="port", help="specify the TCP port", type="int")
parser.add_option("--net_port", dest="netport",help="specify the TCP port for netrpc")
parser.add_option("-d", "--database", dest="db_name", help="specify the database name")
parser.add_option("--login", dest="login", help="specify the User Login")
parser.add_option("--password", dest="pwd", help="specify the User Password")
parser.add_option("--translate-in", dest="translate_in",
                     help="specify .po files to import translation terms")
parser.add_option("--extra-addons", dest="extra_addons",
                     help="specify extra_addons and trunkCommunity modules path ")

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
    'quality-logs' : opt.quality_logs or '',
    'root-path' : opt.root_path or '',
    'translate-in': [],
    'port' : opt.port or 8069,
    'netport':opt.netport or 8070,
    'database': opt.db_name or 'terp',
    'modules' : opt.modules or [],
    'login' : opt.login or 'admin',
    'pwd' : opt.pwd or '',
    'extra-addons':opt.extra_addons or []
}

options['modules'] = opt.modules and map(lambda m: m.strip(), opt.modules.split(',')) or []
# Hint:i18n-import=purchase:ar_AR.po+sale:fr_FR.po,nl_BE.po
if opt.translate_in:
    translate = opt.translate_in
    for module_name,po_files in map(lambda x:tuple(x.split(':')),translate.split('+')):
        for po_file in po_files.split(','):
            if module_name == 'base':
                po_link = '%saddons/%s/i18n/%s'%(options['root-path'],module_name,po_file)
            else:
                po_link = '%s/%s/i18n/%s'%(options['addons-path'], module_name, po_file)
            options['translate-in'].append(po_link)

uri = 'http://localhost:' + str(options['port'])

server_thread = threading.Thread(target=start_server,
                args=(options['root-path'], options['port'],options['netport'], options['addons-path']))
try:
    server_thread.start()
    if command == 'create-db':
        create_db(uri, options['database'], options['login'], options['pwd'])
    if command == 'drop-db':
        drop_db(uri, options['database'])
    if command == 'install-module':
        install_module(uri, options['database'], options['modules'],options['addons-path'],options['extra-addons'],options['login'], options['pwd'])
    if command == 'upgrade-module':
        upgrade_module(uri, options['database'], options['modules'], options['login'], options['pwd'])
    if command == 'check-quality':
        check_quality(uri, options['login'], options['pwd'], options['database'], options['modules'], options['quality-logs'])
    if command == 'install-translation':
        import_translate(uri, options['login'], options['pwd'], options['database'], options['translate-in'])
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
