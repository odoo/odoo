# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

import sys
import netsvc
import osv as base
import pooler


class EnvCall(object):

    def __init__(self,wf_service,d_arg):
        self.wf_service=wf_service
        self.d_arg=d_arg

    def __call__(self,*args):
        arg=self.d_arg+args
        return self.wf_service.execute_cr(*arg)


class Env(dict):

    def __init__(self, wf_service, cr, uid, model, ids):
        self.wf_service = wf_service
        self.cr = cr
        self.uid = uid
        self.model = model
        self.ids = ids
        self.obj = pooler.get_pool(cr.dbname).get(model)
        self.columns = self.obj._columns.keys() + self.obj._inherit_fields.keys()

    def __getitem__(self, key):
        if (key in self.columns) or (key in dir(self.obj)):
            res = self.obj.browse(self.cr, self.uid, self.ids[0])
            return res[key]
            #res=self.wf_service.execute_cr(self.cr, self.uid, self.model, 'read',\
            #       self.ids, [key])[0][key]
            #super(Env, self).__setitem__(key, res)
            #return res
        #elif key in dir(self.obj):
        #   return EnvCall(self.wf_service, (self.cr, self.uid, self.model, key,\
        #           self.ids))
        else:
            return super(Env, self).__getitem__(key)

def _eval_expr(cr, ident, workitem, action):
    ret=False
    assert action, 'You used a NULL action in a workflow, use dummy node instead.'
    for line in action.split('\n'):
        line = line.strip()
        uid=ident[0]
        model=ident[1]
        ids=[ident[2]]
        if line =='True':
            ret=True
        elif line =='False':
            ret=False
        else:
            wf_service = netsvc.LocalService("object_proxy")
            env = Env(wf_service, cr, uid, model, ids)
            ret = eval(line, env)
    return ret

def execute_action(cr, ident, workitem, activity):
    wf_service = netsvc.LocalService("object_proxy")
    obj = pooler.get_pool(cr.dbname).get('ir.actions.server')
    ctx = {'active_id':ident[2], 'active_ids':[ident[2]]}
    result = obj.run(cr, ident[0], [activity['action_id']], ctx)
    return result

def execute(cr, ident, workitem, activity):
    return _eval_expr(cr, ident, workitem, activity['action'])

def check(cr, workitem, ident, transition, signal):
    ok = True
    if transition['signal']:
        ok = (signal==transition['signal'])

    uid = ident[0]
    if transition['role_id'] and uid != 1:
        serv = netsvc.LocalService('object_proxy')
        user_roles = serv.execute_cr(cr, uid, 'res.users', 'read', [uid], ['roles_id'])[0]['roles_id']
        ok = ok and serv.execute_cr(cr, uid, 'res.roles', 'check', user_roles, transition['role_id'])
    ok = ok and _eval_expr(cr, ident, workitem, transition['condition'])
    return ok


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

