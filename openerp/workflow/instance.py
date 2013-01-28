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
import workitem

def create(cr, ident, wkf_id):
    (uid,res_type,res_id) = ident
    cr.execute('insert into wkf_instance (res_type,res_id,uid,wkf_id) values (%s,%s,%s,%s) RETURNING id', (res_type,res_id,uid,wkf_id))
    id_new = cr.fetchone()[0]
    cr.execute('select * from wkf_activity where flow_start=True and wkf_id=%s', (wkf_id,))
    res = cr.dictfetchall()
    stack = []
    workitem.create(cr, res, id_new, ident, stack=stack)
    update(cr, id_new, ident)
    return id_new

def delete(cr, ident):
    (uid,res_type,res_id) = ident
    cr.execute('delete from wkf_instance where res_id=%s and res_type=%s', (res_id,res_type))

def validate(cr, inst_id, ident, signal, force_running=False):
    cr.execute("select * from wkf_workitem where inst_id=%s", (inst_id,))
    stack = []
    for witem in cr.dictfetchall():
        stack = []
        workitem.process(cr, witem, ident, signal, force_running, stack=stack)
        # An action is returned
    _update_end(cr, inst_id, ident)
    return stack and stack[0] or False

def update(cr, inst_id, ident):
    cr.execute("select * from wkf_workitem where inst_id=%s", (inst_id,))
    for witem in cr.dictfetchall():
        stack = []
        workitem.process(cr, witem, ident, stack=stack)
    return _update_end(cr, inst_id, ident)

def _update_end(cr, inst_id, ident):
    cr.execute('select wkf_id from wkf_instance where id=%s', (inst_id,))
    wkf_id = cr.fetchone()[0]
    cr.execute('select state,flow_stop from wkf_workitem w left join wkf_activity a on (a.id=w.act_id) where w.inst_id=%s', (inst_id,))
    ok=True
    for r in cr.fetchall():
        if (r[0]<>'complete') or not r[1]:
            ok=False
            break
    if ok:
        cr.execute('select distinct a.name from wkf_activity a left join wkf_workitem w on (a.id=w.act_id) where w.inst_id=%s', (inst_id,))
        act_names = cr.fetchall()
        cr.execute("update wkf_instance set state='complete' where id=%s", (inst_id,))
        cr.execute("update wkf_workitem set state='complete' where subflow_id=%s", (inst_id,))
        cr.execute("select i.id,w.osv,i.res_id from wkf_instance i left join wkf w on (i.wkf_id=w.id) where i.id IN (select inst_id from wkf_workitem where subflow_id=%s)", (inst_id,))
        for i in cr.fetchall():
            for act_name in act_names:
                validate(cr, i[0], (ident[0],i[1],i[2]), 'subflow.'+act_name[0])
    return ok


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

