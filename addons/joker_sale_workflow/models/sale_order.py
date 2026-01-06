# -*- coding: utf-8 -*-

import logging
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    workflow_id = fields.Many2one(
        'joker.sale.workflow',
        string='İş Akışı',
        tracking=True,
        help='Bu sipariş için kullanılacak otomatik iş akışı'
    )
    
    workflow_state = fields.Selection([
        ('pending', 'Beklemede'),
        ('processing', 'İşleniyor'),
        ('done', 'Tamamlandı'),
        ('error', 'Hata'),
    ], string='Otomasyon Durumu', default='pending', tracking=True)
    
    auto_workflow_log = fields.Text(string='Otomasyon Logu', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        
        for order in orders:
            # İş akışı atanmamışsa otomatik bul
            if not order.workflow_id:
                workflow = self.env['joker.sale.workflow'].get_workflow_for_order(order)
                if workflow:
                    order.workflow_id = workflow
            
            # Otomatik onay kontrolü
            if order.workflow_id and order.workflow_id.auto_confirm_order:
                order._schedule_auto_confirm()
        
        return orders

    def _schedule_auto_confirm(self):
        """Otomatik onay zamanla"""
        self.ensure_one()
        
        if not self.workflow_id:
            return
        
        workflow = self.workflow_id
        
        if workflow.use_delay and workflow.delay_minutes:
            # Gecikmeli çalıştır
            eta = fields.Datetime.now() + timedelta(minutes=workflow.delay_minutes)
            self.env['joker.queue.job'].create_job(
                name=f'Sipariş Otomatik Onay: {self.name}',
                model_name='sale.order',
                method_name='_auto_confirm_order',
                record_ids=[self.id],
                channel='default',
                eta=eta,
            )
            self._log_workflow(f"⏰ Otomatik onay {workflow.delay_minutes} dakika sonra çalışacak")
        else:
            # Hemen çalıştır (ama background'da)
            self.env['joker.queue.job'].create_job(
                name=f'Sipariş Otomatik Onay: {self.name}',
                model_name='sale.order',
                method_name='_auto_confirm_order',
                record_ids=[self.id],
                channel='default',
                priority=20,  # Yüksek öncelik
            )
            self._log_workflow("🔄 Otomatik onay kuyruğa alındı")

    def _auto_confirm_order(self):
        """Siparişi otomatik onayla"""
        for order in self:
            if order.state != 'draft':
                order._log_workflow(f"⚠️ Sipariş zaten onaylanmış (durum: {order.state})")
                continue
            
            try:
                order.workflow_state = 'processing'
                order.action_confirm()
                order._log_workflow("✅ Sipariş otomatik olarak onaylandı")
                
                # Fatura oluşturma kontrolü
                if order.workflow_id and order.workflow_id.auto_create_invoice:
                    order._schedule_auto_invoice()
                    
            except Exception as e:
                order.workflow_state = 'error'
                order._log_workflow(f"❌ Onay hatası: {str(e)}")
                _logger.error(f"Sipariş onay hatası {order.name}: {str(e)}")

    def _schedule_auto_invoice(self):
        """Otomatik fatura oluşturmayı zamanla"""
        self.ensure_one()
        
        self.env['joker.queue.job'].create_job(
            name=f'Fatura Otomatik Oluştur: {self.name}',
            model_name='sale.order',
            method_name='_auto_create_invoice',
            record_ids=[self.id],
            channel='default',
            priority=15,
        )
        self._log_workflow("🔄 Fatura oluşturma kuyruğa alındı")

    def _auto_create_invoice(self):
        """Otomatik fatura oluştur"""
        for order in self:
            if order.state != 'sale':
                order._log_workflow(f"⚠️ Sipariş onaylı değil (durum: {order.state})")
                continue
            
            if order.invoice_status != 'to invoice':
                order._log_workflow(f"⚠️ Faturalanacak bir şey yok (durum: {order.invoice_status})")
                continue
            
            try:
                # Fatura oluştur
                invoice = order._create_invoices()
                order._log_workflow(f"✅ Fatura oluşturuldu: {invoice.name or invoice.id}")
                
                # Fatura onaylama kontrolü
                if order.workflow_id and order.workflow_id.auto_validate_invoice:
                    for inv in invoice:
                        inv._schedule_auto_validate()
                        
            except Exception as e:
                order.workflow_state = 'error'
                order._log_workflow(f"❌ Fatura oluşturma hatası: {str(e)}")
                _logger.error(f"Fatura oluşturma hatası {order.name}: {str(e)}")

    def _log_workflow(self, message):
        """İş akışı loguna mesaj ekle"""
        self.ensure_one()
        timestamp = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}\n"
        
        if self.auto_workflow_log:
            self.auto_workflow_log = self.auto_workflow_log + log_line
        else:
            self.auto_workflow_log = log_line

    def action_run_workflow(self):
        """İş akışını manuel başlat"""
        for order in self:
            if not order.workflow_id:
                raise UserError(_("Bu sipariş için iş akışı tanımlanmamış!"))
            
            order._log_workflow("▶️ İş akışı manuel olarak başlatıldı")
            
            if order.state == 'draft' and order.workflow_id.auto_confirm_order:
                order._auto_confirm_order()
            elif order.state == 'sale' and order.workflow_id.auto_create_invoice:
                order._auto_create_invoice()
            else:
                order._log_workflow("ℹ️ Yapılacak otomatik işlem yok")

    def action_clear_workflow_log(self):
        """İş akışı logunu temizle"""
        self.auto_workflow_log = False


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _schedule_auto_validate(self):
        """Otomatik fatura onayını zamanla"""
        self.ensure_one()
        
        self.env['joker.queue.job'].create_job(
            name=f'Fatura Otomatik Onayla: {self.name or self.id}',
            model_name='account.move',
            method_name='_auto_validate_invoice',
            record_ids=[self.id],
            channel='default',
            priority=10,
        )

    def _auto_validate_invoice(self):
        """Faturayı otomatik onayla"""
        for invoice in self:
            if invoice.state != 'draft':
                continue
            
            try:
                invoice.action_post()
                _logger.info(f"✅ Fatura otomatik onaylandı: {invoice.name}")
                
                # E-posta gönderme kontrolü
                sale_orders = invoice.line_ids.mapped('sale_line_ids.order_id')
                for order in sale_orders:
                    if order.workflow_id and order.workflow_id.auto_send_invoice_email:
                        invoice._schedule_send_email()
                        order._log_workflow(f"✅ Fatura onaylandı: {invoice.name}")
                        break
                        
            except Exception as e:
                _logger.error(f"Fatura onay hatası {invoice.name}: {str(e)}")

    def _schedule_send_email(self):
        """E-posta gönderimini zamanla"""
        self.ensure_one()
        
        self.env['joker.queue.job'].create_job(
            name=f'Fatura E-posta: {self.name}',
            model_name='account.move',
            method_name='_auto_send_invoice_email',
            record_ids=[self.id],
            channel='email',
            priority=5,
        )

    def _auto_send_invoice_email(self):
        """Fatura e-postası gönder"""
        for invoice in self:
            try:
                template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
                if template:
                    invoice.with_context(mark_invoice_as_sent=True).message_post_with_source(
                        template,
                        email_layout_xmlid='mail.mail_notification_light',
                        subtype_xmlid='mail.mt_comment',
                    )
                    _logger.info(f"✅ Fatura e-postası gönderildi: {invoice.name}")
            except Exception as e:
                _logger.error(f"E-posta gönderme hatası {invoice.name}: {str(e)}")
