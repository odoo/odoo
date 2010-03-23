# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import netsvc
import sql_db
from osv import osv,fields 

class wiz_auc_lots_buyer_map(osv.osv_memory):
    _name = 'auction.lots.buyer_map'
    _description = 'Map Buyer'
    
    _columns = {
        'ach_login': fields.char('Buyer Username', size=64, required=True),
        'ach_uid': fields.many2one('res.partner','Buyer', required=True),
    }

    def default_get(self, cr, uid, fields, context):
        """ 
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values 
         @param context: A standard dictionary 
         @return: A dictionary which of fields with values. 
        """
        ids = context and context.get('active_ids',False) or False
        assert ids, _('Active IDs not Found')
        res = super(wiz_auc_lots_buyer_map,self).default_get(cr, uid, fields, context)
        cr.execute('select id from auction_lots where (ach_uid is null and ach_login is not null)  ')
        v_ids = [x[0] for x in cr.fetchall()]
        for rec in self.pool.get('auction.lots').browse(cr, uid, v_ids, context):
            if (not rec.ach_uid or not rec.ach_login):
                res.update(self._start(cr, uid, ids, context))
                return res
        res.update(self._start(cr, uid, ids, context))
        return res
    
    def _start(self, cr, uid, ids, context):
        """ 
         Returns login if already there in the selected record.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of ids 
         @param context: A standard dictionary 
         @return: login field from current record. 
        """
        lots_obj = self.pool.get('auction.lots')
        for rec in lots_obj.browse(cr, uid, ids, context):
            if (len(ids)==1) and (not rec.ach_uid and not rec.ach_login):
                raise osv.except_osv('Error', 'No buyer is set for this lot.')
            if not rec.ach_uid and rec.ach_login:
                return {'ach_login': rec.ach_login}
        return {}
    
    def buyer_map_set(self, cr, uid, ids, context):
        """ 
         To map the buyer and login name.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of ids 
         @param context: A standard dictionary 
         @return: 
        """
        rec_ids = context and context.get('active_ids',False) or False
        assert rec_ids, _('Active IDs not Found')
        datas = self.read(cr, uid, ids[0],['ach_login','ach_uid'])
        lots_obj = self.pool.get('auction.lots')
        recs = lots_obj.browse(cr, uid, rec_ids, context)
        for rec in recs:
            if rec.ach_login==datas['ach_login']:
                lots_obj.write(cr, uid, [rec.id], {'ach_uid': datas['ach_uid']}, context=context)
                cr.commit()
        return {}
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', 
                        context=None, toolbar=False, submenu=False):
        """ 
         Changes the view dynamically
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary 
         @return: New arch of view.
        """
        record_ids = context and context.get('active_ids', False) or False
        res = super(wiz_auc_lots_buyer_map, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        lots_obj = self.pool.get('auction.lots')
        if record_ids:
            for lots in lots_obj.browse(cr, uid, record_ids):
                if lots.ach_uid:
                    res['arch'] = """
                            <form title="Mapping Result">
                                <group col="2" colspan="2">
                                    <label string="All objects are assigned to buyers !"/>
                                    <newline/>
                                    <button icon='gtk-cancel' special="cancel"
                                        string="Done" />
                                </group>
                            </form>
                    """
        return res
    
wiz_auc_lots_buyer_map()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

