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

def clear_log_dir(path):
    dirpath = os.path.realpath(path)
    if os.path.isdir(path):
        for file in os.listdir(dirpath):
            sub_path = dirpath + os.sep + file
            if os.path.isdir(sub_path):
                clear_log_dir(sub_path)
            else:
                os.remove(sub_path)
        os.rmdir(path)
    return True

def start_server(root_path, port, netport, addons_path):
    logfile = 'test_logs/logs.txt'
    os.system('python2.5 %sopenerp-server.py  --pidfile=openerp.pid  --no-xmlrpcs --xmlrpc-port=%s --netrpc-port=%s --addons-path=%s --logfile=%s' %(root_path, str(port),str(netport),addons_path, logfile))


def create_db(url, dbname, user='admin', pwd='admin', lang='en_US'):
    conn = xmlrpclib.ServerProxy(url + '/xmlrpc/db')
    obj_conn = xmlrpclib.ServerProxy(url + '/xmlrpc/object')
    wiz_conn = xmlrpclib.ServerProxy(url + '/xmlrpc/wizard')
    login_conn = xmlrpclib.ServerProxy(url + '/xmlrpc/common')
    db_list = execute(conn, 'list')
    if dbname in db_list:
        execute(conn, 'drop', admin_passwd, dbname)
    id = execute(conn,'create',admin_passwd, dbname, True, lang)
    wait(id,url)
    return True

def login(url, dbname, user, pwd):
    conn = xmlrpclib.ServerProxy(url + '/xmlrpc/common')
    uid = execute(conn,'login',dbname, user, pwd)
    return uid

def install_module(url='', uid=1, pwd='admin', dbname='', module=''):
    obj_conn = xmlrpclib.ServerProxy(url + '/xmlrpc/object')
    wizard_conn = xmlrpclib.ServerProxy(url + '/xmlrpc/wizard')
    module_ids = execute(obj_conn, 'execute', dbname, uid, pwd, 'ir.module.module',
                        'search', [('name','in',[module,'base_module_quality'])])
    for action in ('button_install','button_upgrade'):
        execute(obj_conn, 'execute', dbname, uid, pwd, 'ir.module.module', action, module_ids)
        wiz_id = execute(wizard_conn, 'create', dbname, uid, pwd, 'module.upgrade.simple')
        state = 'init'
        datas = {}
        while state!='end':
            res = execute(wizard_conn, 'execute', dbname, uid, pwd, wiz_id, datas, state, {})
            if state == 'init':
                state = 'start'
            elif state == 'start':
                state = 'end'
    return True

def check_quality(url, user, pwd, dbname, module, quality_logs):
    uid = login(url, dbname, user, pwd)
    quality_logs += 'quality-logs'
    if uid:
        conn = xmlrpclib.ServerProxy(url + '/xmlrpc/object')
        final = {}
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
    else:
        print 'Login Failed...'
    return True

def install_translation(url, uid, pwd, dbname, po_files):
    conn = xmlrpclib.ServerProxy(url + '/xmlrpc/wizard')
    wiz_id = execute(conn,'create', dbname, uid, pwd, 'module.lang.import')
    for file in po_files:
        lang,ext = os.path.splitext(file.split('/')[-1])
        if ext == '.po':
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
                    trans_obj = open(file)
                    datas['form'].update({
                        'name': lang,
                        'code': lang,
                        'data' : base64.encodestring(trans_obj.read())
                    })
                    trans_obj.close()
                elif res['type']=='action':
                    state = res['state']

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

def wait(id, url=''):
    progress=0.0
    sock2 = xmlrpclib.ServerProxy(url+'/xmlrpc/db')
    while not progress==1.0:
        progress,users = execute(sock2,'get_progress',admin_passwd, id)
    return True

def store_logs(module, step, msg='' , want_html_log = False):
    logfile = open('test_logs/logs.txt','r')
    mod_log = open('test_logs/%s/%s.txt'%(module, step),'w')

    mod_log.write(logfile.read() + '\n' + msg)
    mod_log.close()
    logfile.close()

    logfile = open('test_logs/logs.txt','w')
    logfile.write('')
    logfile.close()
    if want_html_log:
        store_html_logs(module)
    return True

def store_html_logs(module):
    html = '''<html><body><a name="TOP"></a>'''
    html +="<h1> Module: %s </h1>"%(module)
    html += "<div id='tabs'>"
    html += "<ul>"
    detail_html = ''
    path = os.path.realpath('test_logs') + os.sep + module
    for log in os.listdir(path):
        log_fp = open(path + os.sep + log, 'r')
        step_name, ext = os.path.splitext(log)
        data = ''
        for line in log_fp.readlines():
            data += line + '<br>'
        html += "<li><a href=\"#%s\">%s</a></li>"%(step_name, step_name)
        detail_html += '''<div id=\"%s\"><h3>%s</h3>%s</div>'''%(step_name, step_name, data)
        log_fp.close()
    html += "</ul>"
    html += "%s"%(detail_html)
    html += "</div></body></html>"

    html_fp = open(path + os.sep + module +'.html','wb')
    html_fp.write(to_decode(html))
    html_fp.close()
    return True

def openerp_test(url, rootpath = '', addons='', user='admin', pwd='admin', quality_log='', port=8069, netport=8070):
    modules = os.listdir(addons)
    for module in modules:
        print "Testing Module: ", module
        if module == '.bzr':
            continue
        dbname = module
        try:
            os.mkdir('test_logs' + os.sep + module)
        except OSError:
            os.remove('test_logs' + os.sep + module)
            os.mkdir('test_logs' + os.sep + module)
        # 1: Create Database also drop the database if it exists !:
        try:
            create_db(url, dbname, user, pwd)
            store_logs(module, 'createDB')
        except xmlrpclib.Fault, e:
            print e.faultString
            store_logs(module, 'createDB', want_html_log=True)
            continue
        except Exception, e:
            print e
            store_logs(module, 'createDB', want_html_log=True)
            continue

        uid = login(url, dbname, user, pwd)
        # 2: Install the module
        try:
            install_module(url, uid, pwd, dbname, module)
            store_logs(module, 'Install_module', )
        except xmlrpclib.Fault, e:
            print e.faultString
            store_logs(module, 'Install_module', want_html_log=True)
            continue
        except Exception, e:
            print e
            store_logs(module, 'Install_module', want_html_log=True)
            continue

        # 3: Check Quality of the module
        try:
            check_quality(url, user, pwd, dbname, module, quality_log)
        except xmlrpclib.Fault, e:
            print e.faultString
            store_logs(module, 'Check_quality', want_html_log=True)
            continue
        except Exception, e:
            print e
            store_logs(module, 'Check_quality', want_html_log=True)
            continue

        #4:Install Translations for the module
        try:
            if os.path.isdir(addons+'/'+module+'/'+'i18n'):
                po_files = os.listdir(addons+'/'+module+'/'+'i18n')
                po_file_paths = []
                for po_file in po_files:
                    if module == 'base':
                        po_link = '%saddons/%s/i18n/%s'%(rootpath, module, po_file)
                    else:
                        po_link = '%s/%s/i18n/%s'%(addons, module, po_file)
                    po_file_paths.append(po_link)
                install_translation(url, uid, pwd, dbname, po_file_paths)
                store_logs(module, 'Install_translation')
            else:
                msg = "Translations Not Available for %s! "%(module)
                store_logs(module, 'Install_translation', msg)
        except xmlrpclib.Fault, e:
            print e.faultString
            store_logs(module, 'Install_translation', want_html_log=True)
            continue
        except Exception, e:
            print e
            store_logs(module, 'Install_translation', want_html_log=True)
            continue
        store_html_logs(module)
    sys.exit(0)
    return True

usage = """%prog command [options]

Basic Command:
    This command will do the following tests on the modules:
    openerp-test:
               1: Start Server
               2: Create new database
               3: Drop database if it exists
               4: Install module from addons one by one.
               5: Install translation file for each module.
               6: Calculate quality and dump quality result into quality_log.pck using pickle
"""
parser = optparse.OptionParser(usage)
parser.add_option("--addons-path", dest="addons_path", help="specify the addons path")
parser.add_option("--root-path", dest="root_path", help="specify the root path")
parser.add_option("--quality-logs", dest="quality_logs", help="specify the path of quality logs files which has to stores")
parser.add_option("-p", "--port", dest="port", help="specify the TCP port", type="int")
parser.add_option("--net_port", dest="netport",help="specify the TCP port for netrpc")
parser.add_option("--login", dest="login", help="specify the User Login")
parser.add_option("--password", dest="pwd", help="specify the User Password")

(opt, args) = parser.parse_args()

if len(args) != 1:
    parser.error("incorrect number of arguments")
command = args[0]
if not command == 'openerp-test':
    parser.error("incorrect command")

options = {
    'addons-path' : opt.addons_path or 'addons',
    'quality-logs' : opt.quality_logs or '',
    'root-path' : opt.root_path or '',
    'port' : opt.port or 8069,
    'netport':opt.netport or 8070,
    'login' : opt.login or 'admin',
    'pwd' : opt.pwd or '',
}

url = 'http://localhost:' + str(options['port'])

server_thread = threading.Thread(target=start_server,
                args=(options['root-path'], options['port'],options['netport'], options['addons-path']))

clear_log_dir('test_logs')
os.mkdir('test_logs')
server_thread.start()

openerp_test(url, options['root-path'], options['addons-path'],
             options['login'], options['pwd'], options['quality-logs'], options['port'],options['netport'])
clean()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
