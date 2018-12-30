# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# TODO:
#   Error treatment: exception, request, ... -> send request to user_id

import time
from openerp.osv import fields,osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class subscription_document(osv.osv):
    _name = "subscription.document"
    _description = "Subscription Document"
    _columns = {
        'name': fields.char('Name', required=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the subscription document without removing it."),
        'model': fields.many2one('ir.model', 'Object', required=True),
        'field_ids': fields.one2many('subscription.document.fields', 'document_id', 'Fields', copy=True)
    }
    _defaults = {
        'active' : lambda *a: True,
    }

class subscription_document_fields(osv.osv):
    _name = "subscription.document.fields"
    _description = "Subscription Document Fields"
    _rec_name = 'field'
    _columns = {
        'field': fields.many2one('ir.model.fields', 'Field', domain="[('model_id', '=', parent.model)]", required=True),
        'value': fields.selection([('false','False'),('date','Current Date')], 'Default Value', size=40, help="Default value is considered for field when new document is generated."),
        'document_id': fields.many2one('subscription.document', 'Subscription Document', ondelete='cascade'),
    }
    _defaults = {}

def _get_document_types(self, cr, uid, context=None):
    cr.execute('select m.model, s.name from subscription_document s, ir_model m WHERE s.model = m.id order by s.name')
    return cr.fetchall()

class subscription_subscription(osv.osv):
    _name = "subscription.subscription"
    _description = "Subscription"
    _columns = {
        'name': fields.char('Name', required=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the subscription without removing it."),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'notes': fields.text('Internal Notes'),
        'user_id': fields.many2one('res.users', 'User', required=True),
        'interval_number': fields.integer('Interval Qty'),
        'interval_type': fields.selection([('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')], 'Interval Unit'),
        'exec_init': fields.integer('Number of documents'),
        'date_init': fields.datetime('First Date'),
        'state': fields.selection([('draft','Draft'),('running','Running'),('done','Done')], 'Status', copy=False),
        'doc_source': fields.reference('Source Document', required=True, selection=_get_document_types, size=128, help="User can choose the source document on which he wants to create documents"),
        'doc_lines': fields.one2many('subscription.subscription.history', 'subscription_id', 'Documents created', readonly=True),
        'cron_id': fields.many2one('ir.cron', 'Cron Job', help="Scheduler which runs on subscription", states={'running':[('readonly',True)], 'done':[('readonly',True)]}),
        'note': fields.text('Notes', help="Description or Summary of Subscription"),
    }
    _defaults = {
        'date_init': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': lambda obj,cr,uid,context: uid,
        'active': lambda *a: True,
        'interval_number': lambda *a: 1,
        'interval_type': lambda *a: 'months',
        'doc_source': lambda *a: False,
        'state': lambda *a: 'draft'
    }

    def _auto_end(self, cr, context=None):    
        super(subscription_subscription, self)._auto_end(cr, context=context)
        # drop the FK from subscription to ir.cron, as it would cause deadlocks
        # during cron job execution. When model_copy() tries to write() on the subscription,
        # it has to wait for an ExclusiveLock on the cron job record, but the latter 
        # is locked by the cron system for the duration of the job!
        # FIXME: the subscription module should be reviewed to simplify the scheduling process
        #        and to use a unique cron job for all subscriptions, so that it never needs to
        #        be updated during its execution. 
        cr.execute("ALTER TABLE %s DROP CONSTRAINT %s" % (self._table, '%s_cron_id_fkey' % self._table))

    def set_process(self, cr, uid, ids, context=None):
        for row in self.read(cr, uid, ids, context=context):
            mapping = {'name':'name','interval_number':'interval_number','interval_type':'interval_type','exec_init':'numbercall','date_init':'nextcall'}
            res = {'model':'subscription.subscription', 'args': repr([[row['id']]]), 'function':'model_copy', 'priority':6, 'user_id':row['user_id'] and row['user_id'][0]}
            for key,value in mapping.items():
                res[value] = row[key]
            id = self.pool.get('ir.cron').create(cr, uid, res)
            self.write(cr, uid, [row['id']], {'cron_id':id, 'state':'running'})
        return True

    def model_copy(self, cr, uid, ids, context=None):
        for row in self.read(cr, uid, ids, context=context):
            if not row.get('cron_id',False):
                continue
            cron_ids = [row['cron_id'][0]]
            remaining = self.pool.get('ir.cron').read(cr, uid, cron_ids, ['numbercall'])[0]['numbercall']
            try:
                (model_name, id) = row['doc_source'].split(',')
                id = int(id)
                model = self.pool[model_name]
            except:
                raise UserError(_('Please provide another source document.\nThis one does not exist!'))

            default = {'state':'draft'}
            doc_obj = self.pool.get('subscription.document')
            document_ids = doc_obj.search(cr, uid, [('model.model','=',model_name)])
            doc = doc_obj.browse(cr, uid, document_ids)[0]
            for f in doc.field_ids:
                if f.value=='date':
                    value = time.strftime('%Y-%m-%d')
                else:
                    value = False
                default[f.field.name] = value

            state = 'running'

            # if there was only one remaining document to generate
            # the subscription is over and we mark it as being done
            if remaining == 1:
                state = 'done'
            id = self.pool[model_name].copy(cr, uid, id, default, context)
            self.pool.get('subscription.subscription.history').create(cr, uid, {'subscription_id': row['id'], 'date':time.strftime('%Y-%m-%d %H:%M:%S'), 'document_id': model_name+','+str(id)})
            self.write(cr, uid, [row['id']], {'state':state})
        return True

    def unlink(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context or {}):
            if record.state=="running":
                raise UserError(_('You cannot delete an active subscription!'))
        return super(subscription_subscription, self).unlink(cr, uid, ids, context)

    def set_done(self, cr, uid, ids, context=None):
        res = self.read(cr,uid, ids, ['cron_id'])
        ids2 = [x['cron_id'][0] for x in res if x['cron_id']]
        if ids2:
            self.pool.get('ir.cron').write(cr, uid, ids2, {'active':False})
        self.write(cr, uid, ids, {'state':'done'})
        return True

    def set_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft'})
        return True

class subscription_subscription_history(osv.osv):
    _name = "subscription.subscription.history"
    _description = "Subscription history"
    _rec_name = 'date'
    _columns = {
        'date': fields.datetime('Date'),
        'subscription_id': fields.many2one('subscription.subscription', 'Subscription', ondelete='cascade'),
        'document_id': fields.reference('Source Document', required=True, selection=_get_document_types, size=128),
    }
