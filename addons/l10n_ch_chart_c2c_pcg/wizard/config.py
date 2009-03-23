#!/usr/bin/env python2.3
#
#  config.py
#
#  Created by Nicolas Bessi on 12.02.09.
#  Copyright (c) 2009 CamptoCamp. All rights reserved.
#
from osv import fields, osv


class Tax_template(osv.osv):
    """Creat account.journal.todo class in order 
        to add configuration wizzard"""

    _name ="account.tax.template.todo"
    
    
    
    def _get_tax(self, cr, uid, ctx):
        if not self.__dict__.has_key('_inner_steps') :
            self._inner_steps = 0
        ids = self.pool.get('account.tax.template').search(cr,uid,[])
        if self._inner_steps == 'done' :
            return False
        return ids[self._inner_steps]
        

    def _get_collected(self, cr, uid, ctx):
        if not self.__dict__.has_key('_inner_steps') :
            self._inner_steps = 0
        if self._inner_steps == 'done' :
            return False
        ids = self.pool.get('account.tax.template').search(cr,uid,[])
        id = self.pool.get('account.tax.template').browse(
            cr,
            uid,
            ids[self._inner_steps]
        ).account_collected_id.id
        
        return id
        
    def _get_paid(self, cr, uid, ctx):
        if not self.__dict__.has_key('_inner_steps') :
            self._inner_steps = 0
        if self._inner_steps == 'done' :
            return False
        ids = self.pool.get('account.tax.template').search(cr,uid,[])
        id = self.pool.get('account.tax.template').browse(
            cr,
            uid,
            ids[self._inner_steps]
        ).account_paid_id.id
        
        return id
    
        
    _columns={
        'name': fields.many2one(
            'account.tax.template',
            'Tax to set',
             readonly=True,
             help="The tax template you are currently editing"
        ),
        'account_collected_id':fields.many2one(
                                                'account.account.template', 
                                                'Invoice Tax Account',
                                                help="You can set \
                                                here the invoice tax account"
                                              ),
        'account_paid_id':fields.many2one(
                                            'account.account.template', 
                                            'Refund Tax Account',
                                            help="You can set \
                                            here the refund tax account"
                                          ),

    }

    _defaults = {
        'name': _get_tax,
        'account_collected_id':_get_collected,
        'account_paid_id':_get_paid,
        }
    
    def on_change_collected(self, cr, uid, id, tax, account) :
        if account :
            self.pool.get('account.tax.template').write(
                                                    cr,
                                                    uid, 
                                                    tax,
                                                    vals={
                                                        'account_collected_id': account,
                                                    }
                                                    )
        
        
        
        return {}
        
    def on_change_paid(self, cr, uid, id, tax, account) :
        if account :
            self.pool.get('account.tax.template').write(
                                                    cr,
                                                    uid, 
                                                    tax,
                                                    vals={
                                                        'account_paid_id': account,
                                                    }
                                            )
        return {}



    def action_cancel(self,cr,uid,ids,context=None):
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
        }
    
    def action_new(self,cr,uid,ids,context={}):
        jids = self.pool.get('account.tax.template').search(cr, uid, [])
        if self._inner_steps < len(jids)-1 :
            self._inner_steps += 1
        else :
            self._inner_steps = 'done'
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'account.tax.template.todo',
                'view_id':self.pool.get('ir.ui.view').search(
                        cr,
                        uid,
                        [('name','=','view_account_journal_form_todo')]
                    ),
                'type': 'ir.actions.act_window',
                'target':'new',
               }
        

Tax_template()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
