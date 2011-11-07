#!/usr/bin/env python
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

#
# This script will automatically test all profiles, localisations and language
# packs You must start the OpenERP server and not have a test database. You
# may also have to change some data in the top of this file.
#

import xmlrpclib
import time
import base64

url = 'http://localhost:8069/xmlrpc'
profiles = [
    'profile_accounting',
    'profile_service',
    'profile_manufacturing'
]
l10n_charts = [
    'l10n_uk',
    False,
    'l10n_be',
    'l10n_fr'
]
dbname = 'test'
admin_passwd = 'admin'
lang = False          # List of langs of False for all


sock = xmlrpclib.ServerProxy(url+'/object')
sock2 = xmlrpclib.ServerProxy(url+'/db')
sock3 = xmlrpclib.ServerProxy(url+'/common')
sock4 = xmlrpclib.ServerProxy(url+'/wizard')
demos =  [True]

langs = lang or (map(lambda x: x[0], sock2.list_lang()) + ['en_US'])

def wait(id):
    progress=0.0
    while not progress==1.0:
        time.sleep(3)
        progress,users = sock2.get_progress(admin_passwd, id)
        time.sleep(3)
    return True

def wizard_run(wizname, fieldvalues=None, endstate='end'):
    if fieldvalues is None:
        fieldvalues = {}
    wiz_id = sock4.create(dbname, uid, 'admin', wizname)
    state = 'init'
    datas = {'form':{}}
    while state!=endstate:
        res = sock4.execute(dbname, uid, 'admin', wiz_id, datas, state, {})
        if 'datas' in res:
            datas['form'].update( res['datas'] )
        if res['type']=='form':
            for field in res['fields'].keys():
                datas['form'][field] = res['fields'][field].get('value', False)
            state = res['state'][-1][0]
            datas['form'].update(fieldvalues)
        elif res['type']=='state':
            state = res['state']
    return True

for demo in demos:
    for l10n in l10n_charts:
        print 'Testing localisation', l10n, '...'
        for prof in profiles:
            print '\tTesting profile', prof, '...'
            id = sock2.create(admin_passwd, dbname, demo, lang)
            wait(id)
            uid = sock3.login(dbname, 'admin','admin')

            idprof = sock.execute(dbname, uid, 'admin', 'ir.module.module', 'search', [('name','=',prof)])
            if l10n:
                idl10n = sock.execute(dbname, uid, 'admin', 'ir.module.module', 'search', [('name','=',l10n)])
            else:
                idl10n = [-1]
            wizard_run('base_setup.base_setup', {
                'profile': idprof[0],
                'charts': idl10n[0],
            }, 'menu')
            for lang in langs:
                print '\t\tTesting Language', lang, '...'
                wizard_run('module.lang.install', {'lang': lang})

            ok = False
            range = 4
            while (not ok) and range:
                try:
                    time.sleep(2)
                    id = sock2.drop(admin_passwd, dbname)
                    ok = True
                except:
                    range -= 1
            time.sleep(2)




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

