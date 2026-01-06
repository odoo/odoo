# -*- coding: utf-8 -*-

import json
import logging
import traceback
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class JokerQueueJob(models.Model):
    """
    Background Job Queue - Async işlemler için
    """
    _name = 'joker.queue.job'
    _description = 'Joker Queue Job'
    _inherit = ['mail.thread']
    _order = 'priority desc, create_date asc'

    name = fields.Char(string='İş Adı', required=True, tracking=True)
    uuid = fields.Char(string='UUID', readonly=True, index=True, copy=False)
    
    channel_id = fields.Many2one(
        'joker.queue.channel',
        string='Kanal',
        default=lambda self: self.env.ref('joker_queue.channel_default', raise_if_not_found=False),
        tracking=True
    )
    
    state = fields.Selection([
        ('pending', 'Beklemede'),
        ('enqueued', 'Kuyruğa Alındı'),
        ('started', 'Başladı'),
        ('done', 'Tamamlandı'),
        ('failed', 'Başarısız'),
        ('cancelled', 'İptal'),
    ], string='Durum', default='pending', tracking=True, index=True)
    
    priority = fields.Integer(string='Öncelik', default=10)
    
    # İş tanımı
    model_name = fields.Char(string='Model', required=True, index=True)
    method_name = fields.Char(string='Metod', required=True)
    record_ids = fields.Text(string='Kayıt ID\'leri')  # JSON array
    args = fields.Text(string='Argümanlar')  # JSON
    kwargs = fields.Text(string='Keyword Argümanları')  # JSON
    
    # Zamanlama
    eta = fields.Datetime(string='Planlanan Zaman', default=fields.Datetime.now)
    date_started = fields.Datetime(string='Başlangıç Zamanı', readonly=True)
    date_done = fields.Datetime(string='Bitiş Zamanı', readonly=True)
    
    # Sonuç
    result = fields.Text(string='Sonuç')
    exc_info = fields.Text(string='Hata Detayı')
    
    # Retry
    max_retries = fields.Integer(string='Maksimum Deneme', default=3)
    retry_count = fields.Integer(string='Deneme Sayısı', default=0)
    retry_delay = fields.Integer(string='Yeniden Deneme Gecikmesi (sn)', default=60)
    
    # İstatistikler
    exec_time = fields.Float(string='Çalışma Süresi (sn)', digits=(10, 3))
    
    user_id = fields.Many2one('res.users', string='Oluşturan', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Şirket', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        import uuid
        for vals in vals_list:
            if not vals.get('uuid'):
                vals['uuid'] = str(uuid.uuid4())
        return super().create(vals_list)

    @api.model
    def create_job(self, name, model_name, method_name, record_ids=None, 
                   args=None, kwargs=None, channel=None, priority=10, 
                   eta=None, max_retries=3, run_now=False):
        """
        Yeni bir background job oluştur
        
        :param name: İş adı
        :param model_name: Hedef model (örn: 'sale.order')
        :param method_name: Çağrılacak metod
        :param record_ids: Kayıt ID listesi (opsiyonel)
        :param args: Pozisyonel argümanlar
        :param kwargs: Keyword argümanları
        :param channel: Kanal (opsiyonel)
        :param priority: Öncelik (yüksek = önce çalışır)
        :param eta: Planlanan çalışma zamanı
        :param max_retries: Maksimum deneme sayısı
        :param run_now: Hemen çalıştır
        :return: Oluşturulan job kaydı
        """
        channel_id = False
        if channel:
            channel_rec = self.env['joker.queue.channel'].search([('name', '=', channel)], limit=1)
            if channel_rec:
                channel_id = channel_rec.id
        
        job = self.create({
            'name': name,
            'model_name': model_name,
            'method_name': method_name,
            'record_ids': json.dumps(record_ids) if record_ids else None,
            'args': json.dumps(args) if args else None,
            'kwargs': json.dumps(kwargs) if kwargs else None,
            'channel_id': channel_id,
            'priority': priority,
            'eta': eta or fields.Datetime.now(),
            'max_retries': max_retries,
            'state': 'enqueued',
        })
        
        if run_now:
            job.action_run()
        
        return job

    def action_run(self):
        """Job'ı çalıştır"""
        for job in self:
            if job.state not in ('pending', 'enqueued', 'failed'):
                continue
            
            job.state = 'started'
            job.date_started = fields.Datetime.now()
            self.env.cr.commit()
            
            start_time = datetime.now()
            
            try:
                # Model ve metodu al
                model = self.env[job.model_name]
                method = getattr(model, job.method_name, None)
                
                if not method:
                    raise UserError(_(f"Metod bulunamadı: {job.model_name}.{job.method_name}"))
                
                # Kayıtları al
                records = model
                if job.record_ids:
                    record_ids = json.loads(job.record_ids)
                    records = model.browse(record_ids)
                
                # Argümanları hazırla
                args = json.loads(job.args) if job.args else []
                kwargs = json.loads(job.kwargs) if job.kwargs else {}
                
                # Metodu çalıştır
                if records:
                    result = method(records, *args, **kwargs)
                else:
                    result = method(*args, **kwargs)
                
                # Başarılı
                end_time = datetime.now()
                job.write({
                    'state': 'done',
                    'date_done': fields.Datetime.now(),
                    'result': json.dumps(result, default=str) if result else None,
                    'exec_time': (end_time - start_time).total_seconds(),
                })
                
                _logger.info(f"✅ Job tamamlandı: {job.name} ({job.uuid})")
                
            except Exception as e:
                end_time = datetime.now()
                job.retry_count += 1
                
                if job.retry_count < job.max_retries:
                    # Yeniden dene
                    job.write({
                        'state': 'enqueued',
                        'eta': fields.Datetime.now() + timedelta(seconds=job.retry_delay * job.retry_count),
                        'exc_info': traceback.format_exc(),
                    })
                    _logger.warning(f"⚠️ Job yeniden denecek ({job.retry_count}/{job.max_retries}): {job.name}")
                else:
                    # Başarısız
                    job.write({
                        'state': 'failed',
                        'date_done': fields.Datetime.now(),
                        'exc_info': traceback.format_exc(),
                        'exec_time': (end_time - start_time).total_seconds(),
                    })
                    _logger.error(f"❌ Job başarısız: {job.name} - {str(e)}")
            
            self.env.cr.commit()

    def action_cancel(self):
        """Job'ı iptal et"""
        for job in self.filtered(lambda j: j.state in ('pending', 'enqueued')):
            job.state = 'cancelled'
            _logger.info(f"🚫 Job iptal edildi: {job.name}")

    def action_retry(self):
        """Job'ı yeniden dene"""
        for job in self.filtered(lambda j: j.state == 'failed'):
            job.write({
                'state': 'enqueued',
                'retry_count': 0,
                'eta': fields.Datetime.now(),
                'exc_info': None,
            })
            _logger.info(f"🔄 Job yeniden kuyruğa alındı: {job.name}")

    def action_set_pending(self):
        """Job'ı beklemede durumuna al"""
        for job in self.filtered(lambda j: j.state == 'cancelled'):
            job.state = 'pending'

    @api.model
    def _cron_process_queue(self, channel_name=None):
        """
        Cron: Kuyruktaki işleri işle
        Her 1 dakikada bir çalışır
        """
        domain = [
            ('state', '=', 'enqueued'),
            ('eta', '<=', fields.Datetime.now()),
        ]
        
        if channel_name:
            channel = self.env['joker.queue.channel'].search([('name', '=', channel_name)], limit=1)
            if channel:
                domain.append(('channel_id', '=', channel.id))
        
        # Öncelik sırasına göre al
        jobs = self.search(domain, order='priority desc, create_date asc', limit=10)
        
        for job in jobs:
            try:
                job.action_run()
            except Exception as e:
                _logger.error(f"Job çalıştırma hatası: {str(e)}")
                continue
        
        return True

    @api.model
    def cleanup_old_jobs(self, days=30):
        """Eski tamamlanmış işleri temizle"""
        cutoff = fields.Datetime.now() - timedelta(days=days)
        old_jobs = self.search([
            ('state', 'in', ('done', 'cancelled')),
            ('date_done', '<', cutoff),
        ])
        count = len(old_jobs)
        old_jobs.unlink()
        _logger.info(f"🧹 {count} eski job temizlendi")
        return count
