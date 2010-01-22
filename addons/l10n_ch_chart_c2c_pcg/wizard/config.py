#!/usr/bin/env python
#
#  config.py
#
#  Created by Nicolas Bessi on 12.02.09.
#  Copyright (c) 2009 CamptoCamp. All rights reserved.
#
from osv import fields, osv

class Tax_template(osv.osv_memory):
    """Creat account.journal.todo class in order
        to add configuration wizzard"""
    _name ="account.tax.template.todo"
    _inherit = 'res.config'

    def _ensure_step(self):
        if getattr(self, '_inner_steps', None) is None:
            self._inner_steps = 0

    def _current_tax_template(self, cr, uid):
        ids = self.pool.get('account.tax.template').search(cr,uid,[])
        return self.pool.get('account.tax.template').browse(
            cr, uid, ids[self._inner_steps]
            )

    def _get_tax(self, cr, uid, ctx):
        self._ensure_step()
        return self.pool.get('account.tax.template')\
            .search(cr,uid,[])[self._inner_steps]

    def _get_collected(self, cr, uid, ctx):
        self._ensure_step()
        return self._current_tax_template(cr, uid).account_collected_id.id

    def _get_paid(self, cr, uid, ctx):
        self._ensure_step()
        return self._current_tax_template(cr, uid).account_paid_id.id

    _columns = {
        'name': fields.many2one(
            'account.tax.template',
            'Tax to set',
             readonly=True,
             help="The tax template you are currently editing"
        ),
        'account_collected_id':fields.many2one(
            'account.account.template',
            'Invoice Tax Account',
            help="You can set here the invoice tax account"
            ),
        'account_paid_id':fields.many2one(
            'account.account.template',
            'Refund Tax Account',
            help="You can set here the refund tax account"
            ),
        }

    _defaults = {
        'name': _get_tax,
        'account_collected_id': _get_collected,
        'account_paid_id': _get_paid,
        }

    def _on_change(self, cr, uid, id, tax, vals):
        if account:
            self.pool.get('account.tax.template').write(
                cr, uid, tax, vals=vals)
        return {}

    def on_change_collected(self, cr, uid, id, tax, account):
        return self._on_change(
            cr, uid, ids, tax, vals={'account_collected_id': account})

    def on_change_paid(self, cr, uid, id, tax, account):
        return self._on_change(
            cr, uid, ids, tax, vals={'account_paid_id': account})

    def execute(self,cr,uid,ids,context={}):
        jids = self.pool.get('account.tax.template').search(cr, uid, [])
        if self._inner_steps < len(jids)-1 :
            self._inner_steps += 1
            return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'account.tax.template.todo',
                'view_id':self.pool.get('ir.ui.view').search(
                    cr, uid, [('name','=','account.tax.template.todo')]),
                'type': 'ir.actions.act_window',
                'target':'new',
                }
Tax_template()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
