# -*- coding: utf-8 -*-

from odoo import models, fields, api


class JokerQueueChannel(models.Model):
    """
    Job Kanalları - İşleri gruplandırmak için
    """
    _name = 'joker.queue.channel'
    _description = 'Joker Queue Channel'
    _order = 'sequence, name'

    name = fields.Char(string='Kanal Adı', required=True, index=True)
    code = fields.Char(string='Kod', required=True, index=True)
    sequence = fields.Integer(string='Sıra', default=10)
    active = fields.Boolean(string='Aktif', default=True)
    
    max_concurrent = fields.Integer(
        string='Maksimum Eşzamanlı İş',
        default=1,
        help='Bu kanalda aynı anda çalışabilecek maksimum iş sayısı'
    )
    
    description = fields.Text(string='Açıklama')
    
    # İstatistikler
    job_ids = fields.One2many('joker.queue.job', 'channel_id', string='İşler')
    job_count = fields.Integer(string='Toplam İş', compute='_compute_job_stats')
    pending_count = fields.Integer(string='Bekleyen', compute='_compute_job_stats')
    running_count = fields.Integer(string='Çalışan', compute='_compute_job_stats')
    done_count = fields.Integer(string='Tamamlanan', compute='_compute_job_stats')
    failed_count = fields.Integer(string='Başarısız', compute='_compute_job_stats')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Kanal kodu benzersiz olmalı!'),
    ]

    @api.depends('job_ids', 'job_ids.state')
    def _compute_job_stats(self):
        for channel in self:
            jobs = channel.job_ids
            channel.job_count = len(jobs)
            channel.pending_count = len(jobs.filtered(lambda j: j.state in ('pending', 'enqueued')))
            channel.running_count = len(jobs.filtered(lambda j: j.state == 'started'))
            channel.done_count = len(jobs.filtered(lambda j: j.state == 'done'))
            channel.failed_count = len(jobs.filtered(lambda j: j.state == 'failed'))

    def action_view_jobs(self):
        """Kanaldaki işleri görüntüle"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} İşleri',
            'res_model': 'joker.queue.job',
            'view_mode': 'list,form',
            'domain': [('channel_id', '=', self.id)],
            'context': {'default_channel_id': self.id},
        }

    def action_run_pending(self):
        """Bekleyen işleri çalıştır"""
        self.ensure_one()
        self.env['joker.queue.job']._cron_process_queue(self.name)
