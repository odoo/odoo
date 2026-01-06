# -*- coding: utf-8 -*-

from odoo import models, fields, api


class BizimHesapSyncLog(models.Model):
    """
    BizimHesap Senkronizasyon Logları
    """
    _name = 'bizimhesap.sync.log'
    _description = 'BizimHesap Sync Log'
    _order = 'create_date desc'
    _rec_name = 'operation'

    backend_id = fields.Many2one(
        'bizimhesap.backend',
        string='Backend',
        required=True,
        ondelete='cascade',
    )
    
    operation = fields.Char(
        string='İşlem',
        required=True,
    )
    
    status = fields.Selection([
        ('success', 'Başarılı'),
        ('warning', 'Uyarı'),
        ('error', 'Hata'),
    ], string='Durum', default='success')
    
    status_code = fields.Integer(string='HTTP Kodu')
    
    message = fields.Text(string='Mesaj')
    error_message = fields.Text(string='Hata Mesajı')
    
    request_data = fields.Text(string='İstek Verisi')
    response_data = fields.Text(string='Yanıt Verisi')
    
    records_created = fields.Integer(string='Oluşturulan', default=0)
    records_updated = fields.Integer(string='Güncellenen', default=0)
    records_skipped = fields.Integer(string='Atlanan', default=0)
    records_failed = fields.Integer(string='Hatalı', default=0)
    
    duration = fields.Float(string='Süre (sn)')
    
    model = fields.Char(string='Model')
    record_id = fields.Integer(string='Kayıt ID')
    external_id = fields.Char(string='External ID')


class BizimHesapBinding(models.AbstractModel):
    """
    BizimHesap Binding Base Model
    """
    _name = 'bizimhesap.binding'
    _description = 'BizimHesap Binding'

    backend_id = fields.Many2one(
        'bizimhesap.backend',
        string='Backend',
        required=True,
        ondelete='cascade',
    )
    
    external_id = fields.Char(
        string='BizimHesap ID',
        required=True,
        index=True,
    )
    
    sync_date = fields.Datetime(
        string='Son Senkronizasyon',
    )
    
    sync_state = fields.Selection([
        ('new', 'Yeni'),
        ('synced', 'Senkronize'),
        ('modified', 'Değiştirilmiş'),
        ('error', 'Hata'),
    ], string='Sync Durumu', default='new')
    
    external_data = fields.Text(
        string='Ham Veri (JSON)',
    )
    
    _sql_constraints = [
        ('external_uniq', 'unique(backend_id, external_id)',
         'Bu External ID zaten bu backend için mevcut!'),
    ]
