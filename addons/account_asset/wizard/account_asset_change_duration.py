# -*- coding: utf-8 -*-
from lxml import etree

from openerp import api, fields, models
from openerp.osv.orm import setup_modifiers


class AssetModify(models.TransientModel):
    _name = 'asset.modify'
    _description = 'Modify Asset'

    name = fields.Char(string='Reason', required=True)
    method_number = fields.Integer(string='Number of Depreciations', required=True)
    method_period = fields.Integer(string='Period Length')
    method_end = fields.Date(string='Ending date')
    note = fields.Text(string='Notes')
    asset_method_time = fields.Char(compute='_get_asset_method_time', string='Asset Method Time', readonly=True)

    @api.one
    def _get_asset_method_time(self):
        if self.env.context.get('active_id'):
            asset = self.env['account.asset.asset'].browse(self.env.context.get('active_id'))
            self.asset_method_time = asset.method_time

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(AssetModify, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        asset_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        if active_model == 'account.asset.asset' and asset_id:
            asset = self.env['account.asset.asset'].browse(asset_id)
            doc = etree.XML(result['arch'])
            if asset.method_time == 'number' and doc.xpath("//field[@name='method_end']"):
                node = doc.xpath("//field[@name='method_end']")[0]
                node.set('invisible', '1')
                setup_modifiers(node, result['fields']['method_end'])
            elif asset.method_time == 'end' and doc.xpath("//field[@name='method_number']"):
                node = doc.xpath("//field[@name='method_number']")[0]
                node.set('invisible', '1')
                setup_modifiers(node, result['fields']['method_number'])
            result['arch'] = etree.tostring(doc)
        return result

    @api.model
    def default_get(self, fields):
        res = super(AssetModify, self).default_get(fields)
        asset_id = self.env.context.get('active_id')
        asset = self.env['account.asset.asset'].browse(asset_id)
        if 'name' in fields:
            res.update({'name': asset.name})
        if 'method_number' in fields and asset.method_time == 'number':
            res.update({'method_number': asset.method_number})
        if 'method_period' in fields:
            res.update({'method_period': asset.method_period})
        if 'method_end' in fields and asset.method_time == 'end':
            res.update({'method_end': asset.method_end})
        if self.env.context.get('active_id'):
            res['asset_method_time'] = self._get_asset_method_time()
        return res

    @api.multi
    def modify(self):
        """ Modifies the duration of asset for calculating depreciation
        and maintains the history of old values.
        """
        asset_id = self.env.context.get('active_id', False)
        asset = self.env['account.asset.asset'].browse(asset_id)
        history_vals = {
            'asset_id': asset_id,
            'name': self.name,
            'method_time': asset.method_time,
            'method_number': asset.method_number,
            'method_period': asset.method_period,
            'method_end': asset.method_end,
            'user_id': self.env.uid,
            'date': fields.Date.context_today(self),
            'note': self.note,
        }
        self.env['account.asset.history'].create(history_vals)
        asset_vals = {
            'method_number': self.method_number,
            'method_period': self.method_period,
            'method_end': self.method_end,
        }
        asset.write(asset_vals)
        asset.compute_depreciation_board()
        return {'type': 'ir.actions.act_window_close'}
