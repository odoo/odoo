##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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

from osv import osv, fields
import time

def _links_get(self, cr, uid, context={}):
    obj = self.pool.get('res.request.link')
    ids = obj.search(cr, uid, [])
    res = obj.read(cr, uid, ids, ['object', 'name'], context)
    return [(r['object'], r['name']) for r in res]

class res_request(osv.osv):
    _name = 'res.request'

    def request_send(self, cr, uid, ids, *args):
        for id in ids:
            cr.execute('update res_request set state=%s,date_sent=%s where id=%d', ('waiting', time.strftime('%Y-%m-%d %H:%M:%S'), id))
            cr.execute('select act_from,act_to,body,date_sent from res_request where id=%d', (id,))
            values = cr.dictfetchone()
            if values['body'] and (len(values['body']) > 128):
                values['name'] = values['body'][:125] + '...'
            else:
                values['name'] = values['body'] or '/'
            values['req_id'] = id
            self.pool.get('res.request.history').create(cr, uid, values)
        return True

    def request_reply(self, cr, uid, ids, *args):
        for id in ids:
            cr.execute("update res_request set state='active', act_from=%d, act_to=act_from, trigger_date=NULL, body='' where id=%d", (uid,id))
        return True

    def request_close(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'closed', 'active':False})
        return True

    def request_get(self, cr, uid):
        cr.execute('select id from res_request where act_to=%d and (trigger_date<=%s or trigger_date is null) and active=True', (uid,time.strftime('%Y-%m-%d')))
        ids = map(lambda x:x[0], cr.fetchall())
        cr.execute('select id from res_request where act_from=%d and (act_to<>%d) and (trigger_date<=%s or trigger_date is null) and active=True', (uid,uid,time.strftime('%Y-%m-%d')))
        ids2 = map(lambda x:x[0], cr.fetchall())
        return (ids, ids2)

    _columns = {
        'create_date': fields.datetime('Created date', readonly=True),
        'name': fields.char('Subject', states={'waiting':[('readonly',True)],'active':[('readonly',True)],'closed':[('readonly',True)]}, required=True, size=128),
        'active': fields.boolean('Active'),
        'priority': fields.selection([('0','Low'),('1','Normal'),('2','High')], 'Priority', states={'waiting':[('readonly',True)],'closed':[('readonly',True)]}, required=True),
        'act_from': fields.many2one('res.users', 'From', required=True, readonly=True, states={'closed':[('readonly',True)]}),
        'act_to': fields.many2one('res.users', 'To', required=True, states={'waiting':[('readonly',True)],'closed':[('readonly',True)]}),
        'body': fields.text('Request', states={'waiting':[('readonly',True)],'closed':[('readonly',True)]}),
        'date_sent': fields.datetime('Date', readonly=True),
        'trigger_date': fields.datetime('Trigger Date', states={'waiting':[('readonly',True)],'closed':[('readonly',True)]}),
        'ref_partner_id':fields.many2one('res.partner', 'Partner Ref.', states={'closed':[('readonly',True)]}),
        'ref_doc1':fields.reference('Document Ref 1', selection=_links_get, size=128, states={'closed':[('readonly',True)]}),
        'ref_doc2':fields.reference('Document Ref 2', selection=_links_get, size=128, states={'closed':[('readonly',True)]}),
        'state': fields.selection([('draft','draft'),('waiting','waiting'),('active','active'),('closed','closed')], 'State', required=True, readonly=True),
        'history': fields.one2many('res.request.history','req_id', 'History')
    }
    _defaults = {
        'act_from': lambda obj,cr,uid,context={}: uid,
        'state': lambda obj,cr,uid,context={}: 'draft',
        'active': lambda obj,cr,uid,context={}: True,
        'priority': lambda obj,cr,uid,context={}: '1',
    }
    _order = 'priority desc, trigger_date, create_date desc'
    _table = 'res_request'
res_request()

class res_request_link(osv.osv):
    _name = 'res.request.link'
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'object': fields.char('Object', size=64, required=True),
        'priority': fields.integer('Priority'),
    }
    _defaults = {
        'priority': lambda *a: 5,
    }
    _order = 'priority'
res_request_link()

class res_request_history(osv.osv):
    _name = 'res.request.history'
    _columns = {
        'name': fields.char('Summary', size=128, states={'active':[('readonly',True)],'waiting':[('readonly',True)]}, required=True),
        'req_id': fields.many2one('res.request', 'Request', required=True, ondelete='cascade', select=True),
        'act_from': fields.many2one('res.users', 'From', required=True, readonly=True),
        'act_to': fields.many2one('res.users', 'To', required=True, states={'waiting':[('readonly',True)]}),
        'body': fields.text('Body', states={'waiting':[('readonly',True)]}),
        'date_sent': fields.datetime('Date sent', states={'waiting':[('readonly',True)]}, required=True)
    }
    _defaults = {
        'name': lambda *a: 'NoName',
        'act_from': lambda obj,cr,uid,context={}: uid,
        'act_to': lambda obj,cr,uid,context={}: uid,
        'date_sent': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'), 
    }
res_request_history()

