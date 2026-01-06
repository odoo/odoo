# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class JokerSaleWorkflow(models.Model):
    """
    Satış İş Akışı Tanımları
    """
    _name = 'joker.sale.workflow'
    _description = 'Joker Sale Workflow'
    _order = 'sequence, name'

    name = fields.Char(string='İş Akışı Adı', required=True)
    code = fields.Char(string='Kod', required=True, index=True)
    sequence = fields.Integer(string='Sıra', default=10)
    active = fields.Boolean(string='Aktif', default=True)
    
    # Otomatik İşlemler
    auto_confirm_order = fields.Boolean(
        string='Siparişi Otomatik Onayla',
        default=False,
        help='Sipariş oluşturulduğunda otomatik olarak onaylansın mı?'
    )
    auto_create_invoice = fields.Boolean(
        string='Fatura Otomatik Oluştur',
        default=False,
        help='Sipariş onaylandığında otomatik fatura oluşturulsun mu?'
    )
    auto_validate_invoice = fields.Boolean(
        string='Faturayı Otomatik Onayla',
        default=False,
        help='Fatura oluşturulduğunda otomatik olarak onaylansın mı?'
    )
    auto_send_invoice_email = fields.Boolean(
        string='Fatura E-postası Gönder',
        default=False,
        help='Fatura onaylandığında müşteriye e-posta gönderilsin mi?'
    )
    auto_mark_done = fields.Boolean(
        string='Siparişi Otomatik Tamamla',
        default=False,
        help='Fatura ödendikten sonra sipariş tamamlansın mı?'
    )
    
    # Koşullar
    min_amount = fields.Float(
        string='Minimum Tutar',
        default=0,
        help='Bu tutarın altındaki siparişler için otomatik işlem yapılmaz'
    )
    max_amount = fields.Float(
        string='Maksimum Tutar',
        default=0,
        help='Bu tutarın üstündeki siparişler için otomatik işlem yapılmaz (0 = sınırsız)'
    )
    
    # Filtreler
    partner_category_ids = fields.Many2many(
        'res.partner.category',
        string='Müşteri Etiketleri',
        help='Sadece bu etiketlere sahip müşteriler için geçerli'
    )
    product_category_ids = fields.Many2many(
        'product.category',
        string='Ürün Kategorileri',
        help='Sadece bu kategorilerdeki ürünler için geçerli'
    )
    payment_term_ids = fields.Many2many(
        'account.payment.term',
        string='Ödeme Koşulları',
        help='Sadece bu ödeme koşulları için geçerli'
    )
    
    # Zamanlama
    use_delay = fields.Boolean(
        string='Gecikme Kullan',
        default=False,
        help='İşlemleri belirli bir süre sonra çalıştır'
    )
    delay_minutes = fields.Integer(
        string='Gecikme (Dakika)',
        default=0,
        help='İşlem başlamadan önce beklenecek süre'
    )
    
    description = fields.Text(string='Açıklama')
    
    # İstatistikler
    order_count = fields.Integer(string='Sipariş Sayısı', compute='_compute_order_count')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'İş akışı kodu benzersiz olmalı!'),
    ]

    def _compute_order_count(self):
        for workflow in self:
            workflow.order_count = self.env['sale.order'].search_count([
                ('workflow_id', '=', workflow.id)
            ])

    def action_view_orders(self):
        """Bu iş akışını kullanan siparişleri görüntüle"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} Siparişleri',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('workflow_id', '=', self.id)],
            'context': {'default_workflow_id': self.id},
        }

    def check_conditions(self, order):
        """
        Sipariş için bu iş akışının koşullarını kontrol et
        
        :param order: sale.order kaydı
        :return: True eğer koşullar sağlanıyorsa
        """
        self.ensure_one()
        
        # Tutar kontrolü
        if self.min_amount and order.amount_total < self.min_amount:
            return False
        if self.max_amount and order.amount_total > self.max_amount:
            return False
        
        # Müşteri etiketi kontrolü
        if self.partner_category_ids:
            partner_categories = order.partner_id.category_id
            if not (partner_categories & self.partner_category_ids):
                return False
        
        # Ürün kategorisi kontrolü
        if self.product_category_ids:
            order_categories = order.order_line.mapped('product_id.categ_id')
            if not (order_categories & self.product_category_ids):
                return False
        
        # Ödeme koşulu kontrolü
        if self.payment_term_ids:
            if order.payment_term_id not in self.payment_term_ids:
                return False
        
        return True

    @api.model
    def get_workflow_for_order(self, order):
        """
        Sipariş için en uygun iş akışını bul
        
        :param order: sale.order kaydı
        :return: joker.sale.workflow kaydı veya False
        """
        # Önce müşterinin varsayılan iş akışını kontrol et
        if order.partner_id.sale_workflow_id:
            workflow = order.partner_id.sale_workflow_id
            if workflow.active and workflow.check_conditions(order):
                return workflow
        
        # Sonra tüm aktif iş akışlarını kontrol et
        workflows = self.search([('active', '=', True)], order='sequence')
        for workflow in workflows:
            if workflow.check_conditions(order):
                return workflow
        
        return False
