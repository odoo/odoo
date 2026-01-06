# -*- coding: utf-8 -*-

import json
from odoo import models, api


class JokerQueueMixin(models.AbstractModel):
    """
    Queue Mixin - Modellere background job yetenekleri ekler
    
    Kullanım:
    ---------
    class MyModel(models.Model):
        _inherit = ['joker.queue.mixin']
        
        def heavy_operation(self):
            # Bu işlemi background'da çalıştır
            self.with_delay().do_heavy_work()
        
        def do_heavy_work(self):
            # Uzun süren işlem
            pass
    """
    _name = 'joker.queue.mixin'
    _description = 'Joker Queue Mixin'

    def delay(self, method_name, *args, channel='default', priority=10, 
              eta=None, max_retries=3, **kwargs):
        """
        Metodu background job olarak çalıştır
        
        :param method_name: Çalıştırılacak metod adı
        :param args: Pozisyonel argümanlar
        :param channel: Kuyruk kanalı
        :param priority: Öncelik
        :param eta: Planlanan zaman
        :param max_retries: Maksimum deneme
        :param kwargs: Keyword argümanları
        :return: Oluşturulan job
        """
        record_ids = self.ids if self else None
        
        job = self.env['joker.queue.job'].create_job(
            name=f"{self._description or self._name}.{method_name}",
            model_name=self._name,
            method_name=method_name,
            record_ids=record_ids,
            args=list(args) if args else None,
            kwargs=kwargs if kwargs else None,
            channel=channel,
            priority=priority,
            eta=eta,
            max_retries=max_retries,
        )
        
        return job

    def run_in_background(self, method_name, *args, **kwargs):
        """
        Kısa yol: Metodu hemen background'da çalıştır
        """
        return self.delay(method_name, *args, run_now=False, **kwargs)

    @api.model
    def enqueue_batch(self, method_name, record_ids, batch_size=100, 
                      channel='batch', **kwargs):
        """
        Toplu işleri batch'lere bölerek kuyruğa ekle
        
        :param method_name: Çalıştırılacak metod
        :param record_ids: Tüm kayıt ID'leri
        :param batch_size: Batch boyutu
        :param channel: Kuyruk kanalı
        :param kwargs: Ek parametreler
        :return: Oluşturulan job'ların listesi
        """
        jobs = []
        
        for i in range(0, len(record_ids), batch_size):
            batch_ids = record_ids[i:i + batch_size]
            job = self.env['joker.queue.job'].create_job(
                name=f"{self._name}.{method_name} (Batch {i//batch_size + 1})",
                model_name=self._name,
                method_name=method_name,
                record_ids=batch_ids,
                channel=channel,
                priority=10 - (i // batch_size),  # İlk batch'ler önce
                **kwargs
            )
            jobs.append(job)
        
        return jobs
