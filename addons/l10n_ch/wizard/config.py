# -*- encoding: utf-8 -*-
#  config.py
#
#  Created by Nicolas Bessi on 12.02.09.
#  Copyright (c) 2010 CamptoCamp. All rights reserved.
#

# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#
#  Created by Nicolas Bessi on 12.02.09.
#  Copyright (c) 2010 CamptoCamp. All rights reserved.
#
from osv import fields, osv


class TaxTemplate(osv.osv):
    """Creat account.journal.todo class in order 
        to add configuration wizzard"""

    _name = "account.tax.template.todo"
    
    def _get_tax(self, cursor, uid, ctx):
        """will find the standardtaxes"""
        if not self.__dict__.has_key('_inner_steps') :
            self._inner_steps = 0
        ids = self.pool.get('account.tax.template').search( cursor, uid, [])
        if self._inner_steps == 'done' :
            return False
        return ids[self._inner_steps]
        

    def _get_collected(self, cursor, uid, ctx):
        """will find the tax tempaltes for collected"""
        if not self.__dict__.has_key('_inner_steps') :
            self._inner_steps = 0
        if self._inner_steps == 'done' :
            return False
        ids = self.pool.get('account.tax.template').search(cursor, uid, [])
        resid = self.pool.get('account.tax.template').browse(
            cursor,
            uid,
            ids[self._inner_steps]
        ).account_collected_id.id
        
        return resid
        
    def _get_paid(self, cursor, uid, ctx):
        """will find the payment tax"""
        if not self.__dict__.has_key('_inner_steps') :
            self._inner_steps = 0
        if self._inner_steps == 'done' :
            return False
        ids = self.pool.get('account.tax.template').search(cursor, uid, [])
        resid = self.pool.get('account.tax.template').browse(
            cursor,
            uid,
            ids[self._inner_steps]
        ).account_paid_id.id
        
        return resid
    
        
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
    
    def on_change_collected(self, cursor, uid, wizid, tax, account) :
        if account :
            self.pool.get('account.tax.template').write(
                                            cursor,
                                            uid, 
                                            tax,
                                            vals={
                                                'account_collected_id': account,
                                            }
                                        )
    
        
        
        return {}
        
    def on_change_paid(self, cursor, uid, wizid, tax, account) :
        if account :
            self.pool.get('account.tax.template').write(
                                            cursor,
                                            uid, 
                                            tax,
                                            vals={
                                                'account_paid_id': account,
                                            }
                                    )
        return {}



    def action_cancel(self, cursor, uid, ids, context=None):
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
        }
    
    def action_new(self, cursor, uid, ids, context=None):
        jids = self.pool.get('account.tax.template').search(cursor, uid, [])
        if self._inner_steps < len(jids)-1 :
            self._inner_steps += 1
        else :
            self._inner_steps = 'done'
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'account.tax.template.todo',
                'view_id':self.pool.get('ir.ui.view').search(
                        cursor,
                        uid,
                        [('name','=','view_account_journal_form_todo')]
                    ),
                'type': 'ir.actions.act_window',
                'target':'new',
               }
        

TaxTemplate()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
