# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """
    Account Move (Invoice) extension for BizimHesap
    """
    _inherit = 'account.move'

    bizimhesap_binding_ids = fields.One2many(
        'bizimhesap.invoice.binding',
        'odoo_id',
        string='BizimHesap Eşleşmeleri',
    )
    
    bizimhesap_synced = fields.Boolean(
        compute='_compute_bizimhesap_synced',
        string='BizimHesap Senkronize',
        store=True,
    )
    
    bizimhesap_guid = fields.Char(
        string='BizimHesap GUID',
        readonly=True,
        copy=False,
        help='BizimHesap tarafından atanan benzersiz ID',
    )
    
    bizimhesap_url = fields.Char(
        string='BizimHesap URL',
        readonly=True,
        copy=False,
        help='BizimHesap\'taki fatura linki',
    )
    
    bizimhesap_sent_date = fields.Datetime(
        string='BizimHesap Gönderim Tarihi',
        readonly=True,
        copy=False,
    )
    
    @api.depends('bizimhesap_binding_ids')
    def _compute_bizimhesap_synced(self):
        for record in self:
            record.bizimhesap_synced = bool(record.bizimhesap_binding_ids)
    
    def action_sync_to_bizimhesap(self):
        """Manuel olarak BizimHesap'a gönder"""
        self.ensure_one()
        
        if self.move_type not in ('out_invoice', 'in_invoice', 'out_refund', 'in_refund'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Uyarı'),
                    'message': _('Sadece faturalar senkronize edilebilir!'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        if self.state != 'posted':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Uyarı'),
                    'message': _('Sadece onaylanmış faturalar gönderilebilir!'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        backend = self.env['bizimhesap.backend'].search([
            ('state', '=', 'connected'),
            ('active', '=', True),
        ], limit=1)
        
        if not backend:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Hata'),
                    'message': _('Aktif BizimHesap bağlantısı bulunamadı!'),
                    'type': 'danger',
                    'sticky': False,
                }
            }
        
        try:
            result = backend.export_invoice(self)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Başarılı'),
                    'message': _('Fatura BizimHesap\'a gönderildi!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"BizimHesap fatura gönderim hatası: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Hata'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_open_bizimhesap(self):
        """BizimHesap'ta faturayı aç"""
        self.ensure_one()
        if self.bizimhesap_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.bizimhesap_url,
                'target': 'new',
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Uyarı'),
                'message': _('Bu fatura henüz BizimHesap\'a gönderilmemiş!'),
                'type': 'warning',
                'sticky': False,
            }
        }
