# -*- encoding: utf-8 -*-
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
import time
from lxml import etree

from openerp.osv import fields, osv

class asset_modify(osv.osv_memory):
    _name = 'asset.modify'
    _description = 'Modify Asset'

    def _get_asset_method_time(self, cr, uid, ids, field_name, arg, context=None):
        if ids and len(ids) == 1 and context.get('active_id'):
            asset = self.pool['account.asset.asset'].browse(cr, uid, context.get('active_id'), context=context)
            return {ids[0]: asset.method_time}
        else:
            return dict.fromkeys(ids, False)

    _columns = {
        'name': fields.char('Reason', required=True),
        'method_number': fields.integer('Number of Depreciations', required=True),
        'method_period': fields.integer('Period Length'),
        'method_end': fields.date('Ending date'),
        'note': fields.text('Notes'),
        'asset_method_time': fields.function(_get_asset_method_time, type='char', string='Asset Method Time', readonly=True),
    }

    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values 
        @param context: A standard dictionary 
        @return: A dictionary which of fields with values. 
        """ 
        if not context:
            context = {}
        asset_obj = self.pool.get('account.asset.asset')
        res = super(asset_modify, self).default_get(cr, uid, fields, context=context)
        asset_id = context.get('active_id', False)
        asset = asset_obj.browse(cr, uid, asset_id, context=context)
        if 'name' in fields:
            res.update({'name': asset.name})
        if 'method_number' in fields and asset.method_time == 'number':
            res.update({'method_number': asset.method_number})
        if 'method_period' in fields:
            res.update({'method_period': asset.method_period})
        if 'method_end' in fields and asset.method_time == 'end':
            res.update({'method_end': asset.method_end})
        if context.get('active_id'):
            res['asset_method_time'] = self._get_asset_method_time(cr, uid, [0], 'asset_method_time', [], context=context)[0]
        return res
    
    def modify(self, cr, uid, ids, context=None):
        """ Modifies the duration of asset for calculating depreciation
        and maintains the history of old values.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of Ids 
        @param context: A standard dictionary 
        @return: Close the wizard. 
        """ 
        if not context:
            context = {}
        asset_obj = self.pool.get('account.asset.asset')
        history_obj = self.pool.get('account.asset.history')
        asset_id = context.get('active_id', False)
        asset = asset_obj.browse(cr, uid, asset_id, context=context)
        data = self.browse(cr, uid, ids[0], context=context)
        history_vals = {
            'asset_id': asset_id,
            'name': data.name,
            'method_time': asset.method_time,
            'method_number': asset.method_number,
            'method_period': asset.method_period,
            'method_end': asset.method_end,
            'user_id': uid,
            'date': time.strftime('%Y-%m-%d'),
            'note': data.note,
        }
        history_obj.create(cr, uid, history_vals, context=context)
        asset_vals = {
            'method_number': data.method_number,
            'method_period': data.method_period,
            'method_end': data.method_end,
        }
        asset_obj.write(cr, uid, [asset_id], asset_vals, context=context)
        asset_obj.compute_depreciation_board(cr, uid, [asset_id], context=context)
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
