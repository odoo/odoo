# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProductProduct(models.Model):
    """
    Product model extension for BizimHesap
    """
    _inherit = 'product.product'

    bizimhesap_binding_ids = fields.One2many(
        'bizimhesap.product.binding',
        'odoo_id',
        string='BizimHesap Eşleşmeleri',
    )
    
    # store=False - Odoo 19'da combination_indices constraint ile çakışmayı önler
    bizimhesap_synced = fields.Boolean(
        compute='_compute_bizimhesap_synced',
        string='BizimHesap Senkronize',
        store=False,  # CRITICAL: store=True constraint violation'a neden oluyor
    )
    
    @api.depends('bizimhesap_binding_ids')
    def _compute_bizimhesap_synced(self):
        for record in self:
            record.bizimhesap_synced = bool(record.bizimhesap_binding_ids)
    
    def action_sync_to_bizimhesap(self):
        """Manuel olarak BizimHesap'a gönder"""
        self.ensure_one()
        
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
            backend.export_product(self)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Başarılı'),
                    'message': _('Ürün BizimHesap\'a gönderildi!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
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


class ProductTemplate(models.Model):
    """
    Product Template extension
    """
    _inherit = 'product.template'
    
    bizimhesap_synced = fields.Boolean(
        compute='_compute_bizimhesap_synced',
        string='BizimHesap Senkronize',
    )
    
    def _compute_bizimhesap_synced(self):
        for record in self:
            record.bizimhesap_synced = any(
                p.bizimhesap_synced for p in record.product_variant_ids
            )
