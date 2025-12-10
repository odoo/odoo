# -*- coding: utf-8 -*-
# Part of SMART eCommerce Extension. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class EcommerceAnalytics(models.Model):
    """Main analytics dashboard model with computed KPIs"""
    _name = 'ecommerce.analytics'
    _description = 'E-commerce Analytics Dashboard'
    _auto = False  # This is a SQL view
    _order = 'date desc'

    date = fields.Date(string='Date', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    
    # Sales metrics
    total_orders = fields.Integer(string='Total Orders', readonly=True)
    confirmed_orders = fields.Integer(string='Confirmed Orders', readonly=True)
    cancelled_orders = fields.Integer(string='Cancelled Orders', readonly=True)
    
    total_revenue = fields.Monetary(string='Total Revenue', readonly=True, currency_field='currency_id')
    avg_order_value = fields.Monetary(string='Avg Order Value', readonly=True, currency_field='currency_id')
    total_tax = fields.Monetary(string='Total Tax', readonly=True, currency_field='currency_id')
    
    # Product metrics
    products_sold = fields.Integer(string='Products Sold', readonly=True)
    unique_products = fields.Integer(string='Unique Products', readonly=True)
    
    # Customer metrics
    unique_customers = fields.Integer(string='Unique Customers', readonly=True)
    new_customers = fields.Integer(string='New Customers', readonly=True)
    
    # Delivery metrics
    orders_with_delivery = fields.Integer(string='Orders with Delivery', readonly=True)
    total_delivery_revenue = fields.Monetary(string='Delivery Revenue', readonly=True, currency_field='currency_id')
    
    def init(self):
        """Create or replace the SQL view for analytics"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () AS id,
                    date_trunc('day', so.date_order)::date AS date,
                    so.company_id,
                    so.currency_id,
                    COUNT(DISTINCT so.id) AS total_orders,
                    COUNT(DISTINCT CASE WHEN so.state IN ('sale', 'done') THEN so.id END) AS confirmed_orders,
                    COUNT(DISTINCT CASE WHEN so.state = 'cancel' THEN so.id END) AS cancelled_orders,
                    COALESCE(SUM(CASE WHEN so.state IN ('sale', 'done') THEN so.amount_total ELSE 0 END), 0) AS total_revenue,
                    COALESCE(AVG(CASE WHEN so.state IN ('sale', 'done') THEN so.amount_total END), 0) AS avg_order_value,
                    COALESCE(SUM(CASE WHEN so.state IN ('sale', 'done') THEN so.amount_tax ELSE 0 END), 0) AS total_tax,
                    COALESCE(SUM(sol.product_uom_qty), 0)::integer AS products_sold,
                    COUNT(DISTINCT sol.product_id) AS unique_products,
                    COUNT(DISTINCT so.partner_id) AS unique_customers,
                    COUNT(DISTINCT CASE 
                        WHEN so.partner_id NOT IN (
                            SELECT DISTINCT partner_id FROM sale_order 
                            WHERE date_order < date_trunc('day', so.date_order)
                            AND state IN ('sale', 'done')
                        ) THEN so.partner_id 
                    END) AS new_customers,
                    COUNT(DISTINCT CASE WHEN so.delivery_zone_id IS NOT NULL THEN so.id END) AS orders_with_delivery,
                    COALESCE(SUM(CASE WHEN so.delivery_zone_id IS NOT NULL THEN so.computed_delivery_price ELSE 0 END), 0) AS total_delivery_revenue
                FROM sale_order so
                LEFT JOIN sale_order_line sol ON sol.order_id = so.id
                WHERE so.website_id IS NOT NULL
                    AND so.date_order IS NOT NULL
                GROUP BY 
                    date_trunc('day', so.date_order)::date,
                    so.company_id,
                    so.currency_id
            )
        """ % self._table)


class DailySalesReport(models.Model):
    """Daily sales report model"""
    _name = 'daily.sales.report'
    _description = 'Daily Sales Report'
    _auto = False
    _order = 'date desc'

    date = fields.Date(string='Date', readonly=True)
    day_of_week = fields.Char(string='Day', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    
    # Order counts
    total_orders = fields.Integer(string='Total Orders', readonly=True)
    confirmed_orders = fields.Integer(string='Confirmed', readonly=True)
    draft_orders = fields.Integer(string='Draft', readonly=True)
    cancelled_orders = fields.Integer(string='Cancelled', readonly=True)
    
    # Revenue
    gross_revenue = fields.Monetary(string='Gross Revenue', readonly=True, currency_field='currency_id')
    net_revenue = fields.Monetary(string='Net Revenue', readonly=True, currency_field='currency_id')
    total_tax = fields.Monetary(string='Total Tax', readonly=True, currency_field='currency_id')
    total_discount = fields.Monetary(string='Total Discount', readonly=True, currency_field='currency_id')
    delivery_revenue = fields.Monetary(string='Delivery Revenue', readonly=True, currency_field='currency_id')
    
    # Averages
    avg_order_value = fields.Monetary(string='AOV', readonly=True, currency_field='currency_id')
    avg_items_per_order = fields.Float(string='Items/Order', readonly=True, digits=(12, 2))
    
    # Customers
    unique_customers = fields.Integer(string='Customers', readonly=True)
    repeat_customers = fields.Integer(string='Repeat', readonly=True)
    
    # Comparison
    revenue_growth_pct = fields.Float(string='Growth %', readonly=True, digits=(12, 2))
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH daily_data AS (
                    SELECT
                        date_trunc('day', so.date_order)::date AS date,
                        to_char(so.date_order, 'Day') AS day_of_week,
                        so.company_id,
                        so.currency_id,
                        COUNT(DISTINCT so.id) AS total_orders,
                        COUNT(DISTINCT CASE WHEN so.state IN ('sale', 'done') THEN so.id END) AS confirmed_orders,
                        COUNT(DISTINCT CASE WHEN so.state = 'draft' THEN so.id END) AS draft_orders,
                        COUNT(DISTINCT CASE WHEN so.state = 'cancel' THEN so.id END) AS cancelled_orders,
                        COALESCE(SUM(CASE WHEN so.state IN ('sale', 'done') THEN so.amount_total ELSE 0 END), 0) AS gross_revenue,
                        COALESCE(SUM(CASE WHEN so.state IN ('sale', 'done') THEN so.amount_untaxed ELSE 0 END), 0) AS net_revenue,
                        COALESCE(SUM(CASE WHEN so.state IN ('sale', 'done') THEN so.amount_tax ELSE 0 END), 0) AS total_tax,
                        0.0 AS total_discount,
                        COALESCE(SUM(CASE WHEN so.state IN ('sale', 'done') THEN so.computed_delivery_price ELSE 0 END), 0) AS delivery_revenue,
                        COALESCE(AVG(CASE WHEN so.state IN ('sale', 'done') THEN so.amount_total END), 0) AS avg_order_value,
                        COALESCE(AVG(order_items.item_count), 0) AS avg_items_per_order,
                        COUNT(DISTINCT so.partner_id) AS unique_customers,
                        0 AS repeat_customers
                    FROM sale_order so
                    LEFT JOIN (
                        SELECT order_id, SUM(product_uom_qty) AS item_count
                        FROM sale_order_line
                        WHERE product_id IS NOT NULL
                        GROUP BY order_id
                    ) order_items ON order_items.order_id = so.id
                    WHERE so.website_id IS NOT NULL
                        AND so.date_order IS NOT NULL
                    GROUP BY 
                        date_trunc('day', so.date_order)::date,
                        to_char(so.date_order, 'Day'),
                        so.company_id,
                        so.currency_id
                ),
                with_growth AS (
                    SELECT
                        d.*,
                        LAG(d.gross_revenue) OVER (
                            PARTITION BY d.company_id 
                            ORDER BY d.date
                        ) AS prev_day_revenue
                    FROM daily_data d
                )
                SELECT
                    row_number() OVER () AS id,
                    date,
                    day_of_week,
                    company_id,
                    currency_id,
                    total_orders,
                    confirmed_orders,
                    draft_orders,
                    cancelled_orders,
                    gross_revenue,
                    net_revenue,
                    total_tax,
                    total_discount,
                    delivery_revenue,
                    avg_order_value,
                    avg_items_per_order,
                    unique_customers,
                    repeat_customers,
                    CASE 
                        WHEN prev_day_revenue > 0 THEN 
                            ROUND(((gross_revenue - prev_day_revenue) / prev_day_revenue * 100)::numeric, 2)
                        ELSE 0 
                    END AS revenue_growth_pct
                FROM with_growth
            )
        """ % self._table)


class TopSellingProduct(models.Model):
    """Top selling products report"""
    _name = 'top.selling.product'
    _description = 'Top Selling Products'
    _auto = False
    _order = 'total_quantity desc, total_revenue desc'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    category_id = fields.Many2one('product.category', string='Category', readonly=True)
    brand = fields.Char(string='Brand', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    
    total_quantity = fields.Float(string='Qty Sold', readonly=True)
    total_revenue = fields.Monetary(string='Revenue', readonly=True, currency_field='currency_id')
    total_orders = fields.Integer(string='Orders', readonly=True)
    avg_price = fields.Monetary(string='Avg Price', readonly=True, currency_field='currency_id')
    
    # Performance indicators
    revenue_share_pct = fields.Float(string='Revenue %', readonly=True, digits=(12, 2))
    
    # Time-based
    first_sale_date = fields.Date(string='First Sale', readonly=True)
    last_sale_date = fields.Date(string='Last Sale', readonly=True)
    days_since_launch = fields.Integer(string='Days Active', readonly=True)
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH product_stats AS (
                    SELECT
                        sol.product_id,
                        pp.product_tmpl_id,
                        pt.name AS product_name,
                        pt.categ_id AS category_id,
                        pt.brand,
                        so.company_id,
                        so.currency_id,
                        SUM(sol.product_uom_qty) AS total_quantity,
                        SUM(sol.price_subtotal) AS total_revenue,
                        COUNT(DISTINCT so.id) AS total_orders,
                        AVG(sol.price_unit) AS avg_price,
                        MIN(so.date_order)::date AS first_sale_date,
                        MAX(so.date_order)::date AS last_sale_date,
                        EXTRACT(DAY FROM (NOW() - MIN(so.date_order))) AS days_since_launch
                    FROM sale_order_line sol
                    JOIN sale_order so ON so.id = sol.order_id
                    JOIN product_product pp ON pp.id = sol.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    WHERE so.state IN ('sale', 'done')
                        AND so.website_id IS NOT NULL
                        AND sol.product_id IS NOT NULL
                    GROUP BY 
                        sol.product_id,
                        pp.product_tmpl_id,
                        pt.name,
                        pt.categ_id,
                        pt.brand,
                        so.company_id,
                        so.currency_id
                ),
                total_revenue AS (
                    SELECT 
                        company_id,
                        currency_id,
                        SUM(total_revenue) AS grand_total
                    FROM product_stats
                    GROUP BY company_id, currency_id
                )
                SELECT
                    row_number() OVER () AS id,
                    ps.product_id,
                    ps.product_tmpl_id,
                    ps.product_name,
                    ps.category_id,
                    ps.brand,
                    ps.company_id,
                    ps.currency_id,
                    ps.total_quantity,
                    ps.total_revenue,
                    ps.total_orders,
                    ps.avg_price,
                    ROUND((ps.total_revenue / NULLIF(tr.grand_total, 0) * 100)::numeric, 2) AS revenue_share_pct,
                    ps.first_sale_date,
                    ps.last_sale_date,
                    ps.days_since_launch::integer
                FROM product_stats ps
                LEFT JOIN total_revenue tr ON tr.company_id = ps.company_id AND tr.currency_id = ps.currency_id
            )
        """ % self._table)


class TopSeller(models.Model):
    """Top sellers (partners/customers) report"""
    _name = 'top.seller'
    _description = 'Top Sellers/Customers'
    _auto = False
    _order = 'total_spent desc'

    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    partner_name = fields.Char(string='Customer Name', readonly=True)
    partner_email = fields.Char(string='Email', readonly=True)
    partner_city = fields.Char(string='City', readonly=True)
    partner_country_id = fields.Many2one('res.country', string='Country', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    
    # Order metrics
    total_orders = fields.Integer(string='Total Orders', readonly=True)
    confirmed_orders = fields.Integer(string='Confirmed', readonly=True)
    
    # Financial metrics
    total_spent = fields.Monetary(string='Total Spent', readonly=True, currency_field='currency_id')
    avg_order_value = fields.Monetary(string='Avg Order', readonly=True, currency_field='currency_id')
    total_products = fields.Integer(string='Products Bought', readonly=True)
    
    # Engagement
    first_order_date = fields.Date(string='First Order', readonly=True)
    last_order_date = fields.Date(string='Last Order', readonly=True)
    days_as_customer = fields.Integer(string='Days as Customer', readonly=True)
    avg_days_between_orders = fields.Float(string='Avg Days Between Orders', readonly=True, digits=(12, 1))
    
    # Segmentation
    customer_tier = fields.Selection([
        ('vip', 'VIP'),
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('bronze', 'Bronze'),
        ('new', 'New'),
    ], string='Tier', readonly=True)
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH customer_stats AS (
                    SELECT
                        so.partner_id,
                        rp.name AS partner_name,
                        rp.email AS partner_email,
                        rp.city AS partner_city,
                        rp.country_id AS partner_country_id,
                        so.company_id,
                        so.currency_id,
                        COUNT(DISTINCT so.id) AS total_orders,
                        COUNT(DISTINCT CASE WHEN so.state IN ('sale', 'done') THEN so.id END) AS confirmed_orders,
                        COALESCE(SUM(CASE WHEN so.state IN ('sale', 'done') THEN so.amount_total ELSE 0 END), 0) AS total_spent,
                        COALESCE(AVG(CASE WHEN so.state IN ('sale', 'done') THEN so.amount_total END), 0) AS avg_order_value,
                        COALESCE(SUM(sol.product_uom_qty), 0)::integer AS total_products,
                        MIN(so.date_order)::date AS first_order_date,
                        MAX(so.date_order)::date AS last_order_date,
                        EXTRACT(DAY FROM (MAX(so.date_order) - MIN(so.date_order))) AS days_as_customer,
                        CASE 
                            WHEN COUNT(DISTINCT so.id) > 1 THEN
                                EXTRACT(DAY FROM (MAX(so.date_order) - MIN(so.date_order))) / (COUNT(DISTINCT so.id) - 1)
                            ELSE 0
                        END AS avg_days_between_orders
                    FROM sale_order so
                    JOIN res_partner rp ON rp.id = so.partner_id
                    LEFT JOIN sale_order_line sol ON sol.order_id = so.id
                    WHERE so.website_id IS NOT NULL
                        AND so.date_order IS NOT NULL
                    GROUP BY 
                        so.partner_id,
                        rp.name,
                        rp.email,
                        rp.city,
                        rp.country_id,
                        so.company_id,
                        so.currency_id
                )
                SELECT
                    row_number() OVER () AS id,
                    partner_id,
                    partner_name,
                    partner_email,
                    partner_city,
                    partner_country_id,
                    company_id,
                    currency_id,
                    total_orders,
                    confirmed_orders,
                    total_spent,
                    avg_order_value,
                    total_products,
                    first_order_date,
                    last_order_date,
                    days_as_customer::integer,
                    avg_days_between_orders,
                    CASE 
                        WHEN total_spent >= 10000 THEN 'vip'
                        WHEN total_spent >= 5000 THEN 'gold'
                        WHEN total_spent >= 1000 THEN 'silver'
                        WHEN confirmed_orders >= 2 THEN 'bronze'
                        ELSE 'new'
                    END AS customer_tier
                FROM customer_stats
            )
        """ % self._table)


class CartAbandonment(models.Model):
    """Cart abandonment tracking and analytics"""
    _name = 'cart.abandonment'
    _description = 'Cart Abandonment Analytics'
    _order = 'create_date desc'
    
    name = fields.Char(string='Reference', default=lambda self: _('New'), copy=False, readonly=True)
    
    # Link to order/cart
    order_id = fields.Many2one('sale.order', string='Cart', readonly=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Customer', related='order_id.partner_id', store=True)
    company_id = fields.Many2one('res.company', string='Company', related='order_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='order_id.currency_id', store=True)
    
    # Cart details
    cart_value = fields.Monetary(string='Cart Value', currency_field='currency_id')
    item_count = fields.Integer(string='Items in Cart')
    product_ids = fields.Many2many('product.product', string='Products', readonly=True)
    
    # Abandonment details
    abandoned_at = fields.Datetime(string='Abandoned At')
    hours_since_creation = fields.Float(string='Hours Since Creation', compute='_compute_age')
    days_since_creation = fields.Integer(string='Days Since Creation', compute='_compute_age')
    
    # Status
    state = fields.Selection([
        ('abandoned', 'Abandoned'),
        ('recovered', 'Recovered'),
        ('expired', 'Expired'),
        ('notified', 'Notified'),
    ], string='Status', default='abandoned')
    
    # Recovery tracking
    recovery_email_sent = fields.Boolean(string='Recovery Email Sent', default=False)
    recovery_email_date = fields.Datetime(string='Email Sent Date')
    recovered_order_id = fields.Many2one('sale.order', string='Recovered Order')
    recovered_at = fields.Datetime(string='Recovered At')
    
    # Abandonment reason (if captured)
    abandonment_stage = fields.Selection([
        ('cart', 'Cart Page'),
        ('checkout', 'Checkout'),
        ('payment', 'Payment'),
        ('delivery', 'Delivery Selection'),
    ], string='Abandonment Stage')
    
    @api.depends('order_id.create_date')
    def _compute_age(self):
        now = fields.Datetime.now()
        for record in self:
            if record.order_id.create_date:
                delta = now - record.order_id.create_date
                record.hours_since_creation = delta.total_seconds() / 3600
                record.days_since_creation = delta.days
            else:
                record.hours_since_creation = 0
                record.days_since_creation = 0
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('cart.abandonment') or _('New')
        return super().create(vals)
    
    def action_send_recovery_email(self):
        """Send cart recovery email"""
        self.ensure_one()
        if not self.partner_id.email:
            raise UserError(_('Customer has no email address.'))
        
        template = self.env.ref('smart_ecommerce_extension.cart_recovery_email_template', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        
        self.write({
            'recovery_email_sent': True,
            'recovery_email_date': fields.Datetime.now(),
            'state': 'notified',
        })
        return True
    
    def action_mark_recovered(self):
        """Mark cart as recovered"""
        self.write({
            'state': 'recovered',
            'recovered_at': fields.Datetime.now(),
        })
    
    @api.model
    def _cron_detect_abandoned_carts(self, hours_threshold=24):
        """Cron job to detect abandoned carts"""
        threshold_date = fields.Datetime.now() - timedelta(hours=hours_threshold)
        
        # Find draft orders that haven't been modified recently
        abandoned_orders = self.env['sale.order'].sudo().search([
            ('state', '=', 'draft'),
            ('website_id', '!=', False),
            ('order_line', '!=', False),
            ('write_date', '<', threshold_date),
        ])
        
        # Exclude orders already tracked
        tracked_order_ids = self.sudo().search([
            ('state', 'not in', ['recovered', 'expired'])
        ]).mapped('order_id.id')
        
        new_abandoned = abandoned_orders.filtered(lambda o: o.id not in tracked_order_ids)
        
        created_count = 0
        for order in new_abandoned:
            self.sudo().create({
                'order_id': order.id,
                'cart_value': order.amount_total,
                'item_count': len(order.order_line),
                'product_ids': [(6, 0, order.order_line.mapped('product_id.id'))],
                'abandoned_at': fields.Datetime.now(),
                'abandonment_stage': 'cart',
            })
            created_count += 1
        
        _logger.info(f'Cart abandonment detection: found {created_count} new abandoned carts')
        return created_count
    
    @api.model
    def _cron_send_recovery_emails(self, hours_after_abandonment=4, limit=50):
        """Cron job to send recovery emails for abandoned carts"""
        threshold = fields.Datetime.now() - timedelta(hours=hours_after_abandonment)
        
        abandoned_carts = self.sudo().search([
            ('state', '=', 'abandoned'),
            ('recovery_email_sent', '=', False),
            ('abandoned_at', '<', threshold),
            ('partner_id.email', '!=', False),
        ], limit=limit)
        
        sent_count = 0
        for cart in abandoned_carts:
            try:
                cart.action_send_recovery_email()
                sent_count += 1
            except Exception as e:
                _logger.error(f'Failed to send recovery email for cart {cart.name}: {e}')
        
        _logger.info(f'Cart recovery emails: sent {sent_count} emails')
        return sent_count


class CartAbandonmentReport(models.Model):
    """Cart abandonment analytics report"""
    _name = 'cart.abandonment.report'
    _description = 'Cart Abandonment Report'
    _auto = False
    _order = 'date desc'

    date = fields.Date(string='Date', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    
    # Cart metrics
    total_carts = fields.Integer(string='Total Carts', readonly=True)
    abandoned_carts = fields.Integer(string='Abandoned', readonly=True)
    recovered_carts = fields.Integer(string='Recovered', readonly=True)
    converted_carts = fields.Integer(string='Converted', readonly=True)
    
    # Value metrics
    total_abandoned_value = fields.Monetary(string='Abandoned Value', readonly=True, currency_field='currency_id')
    recovered_value = fields.Monetary(string='Recovered Value', readonly=True, currency_field='currency_id')
    avg_abandoned_value = fields.Monetary(string='Avg Abandoned Value', readonly=True, currency_field='currency_id')
    
    # Rates
    abandonment_rate = fields.Float(string='Abandonment Rate %', readonly=True, digits=(12, 2))
    recovery_rate = fields.Float(string='Recovery Rate %', readonly=True, digits=(12, 2))
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH orders_with_lines AS (
                    SELECT DISTINCT so.id
                    FROM sale_order so
                    JOIN sale_order_line sol ON sol.order_id = so.id
                    WHERE so.website_id IS NOT NULL
                ),
                daily_carts AS (
                    SELECT
                        date_trunc('day', so.create_date)::date AS date,
                        so.company_id,
                        so.currency_id,
                        COUNT(DISTINCT so.id) AS total_carts,
                        COUNT(DISTINCT CASE WHEN so.state = 'draft' THEN so.id END) AS abandoned_carts,
                        COUNT(DISTINCT CASE WHEN so.state IN ('sale', 'done') THEN so.id END) AS converted_carts,
                        COALESCE(SUM(CASE WHEN so.state = 'draft' THEN so.amount_total ELSE 0 END), 0) AS total_abandoned_value,
                        COALESCE(AVG(CASE WHEN so.state = 'draft' THEN so.amount_total END), 0) AS avg_abandoned_value
                    FROM sale_order so
                    WHERE so.website_id IS NOT NULL
                        AND so.create_date IS NOT NULL
                        AND so.id IN (SELECT id FROM orders_with_lines)
                    GROUP BY 
                        date_trunc('day', so.create_date)::date,
                        so.company_id,
                        so.currency_id
                ),
                recovery_data AS (
                    SELECT
                        date_trunc('day', ca.recovered_at)::date AS date,
                        ca.company_id,
                        COUNT(*) AS recovered_carts,
                        SUM(ca.cart_value) AS recovered_value
                    FROM cart_abandonment ca
                    WHERE ca.state = 'recovered'
                        AND ca.recovered_at IS NOT NULL
                    GROUP BY 
                        date_trunc('day', ca.recovered_at)::date,
                        ca.company_id
                )
                SELECT
                    row_number() OVER () AS id,
                    dc.date,
                    dc.company_id,
                    dc.currency_id,
                    dc.total_carts,
                    dc.abandoned_carts,
                    COALESCE(rd.recovered_carts, 0)::integer AS recovered_carts,
                    dc.converted_carts,
                    dc.total_abandoned_value,
                    COALESCE(rd.recovered_value, 0) AS recovered_value,
                    dc.avg_abandoned_value,
                    CASE 
                        WHEN dc.total_carts > 0 THEN 
                            ROUND((dc.abandoned_carts::numeric / dc.total_carts * 100), 2)
                        ELSE 0 
                    END AS abandonment_rate,
                    CASE 
                        WHEN dc.abandoned_carts > 0 THEN 
                            ROUND((COALESCE(rd.recovered_carts, 0)::numeric / dc.abandoned_carts * 100), 2)
                        ELSE 0 
                    END AS recovery_rate
                FROM daily_carts dc
                LEFT JOIN recovery_data rd ON rd.date = dc.date AND rd.company_id = dc.company_id
            )
        """ % self._table)


class AnalyticsWizard(models.TransientModel):
    """Wizard for generating analytics reports"""
    _name = 'analytics.report.wizard'
    _description = 'Analytics Report Wizard'

    date_from = fields.Date(string='From Date', required=True, 
                           default=lambda self: fields.Date.today() - timedelta(days=30))
    date_to = fields.Date(string='To Date', required=True,
                         default=fields.Date.today)
    report_type = fields.Selection([
        ('daily_sales', 'Daily Sales Report'),
        ('top_products', 'Top Products'),
        ('top_customers', 'Top Customers'),
        ('cart_abandonment', 'Cart Abandonment'),
        ('full_dashboard', 'Full Dashboard'),
    ], string='Report Type', required=True, default='full_dashboard')
    
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    
    def action_generate_report(self):
        """Generate selected report"""
        self.ensure_one()
        
        action_map = {
            'daily_sales': 'smart_ecommerce_extension.action_daily_sales_report',
            'top_products': 'smart_ecommerce_extension.action_top_selling_products',
            'top_customers': 'smart_ecommerce_extension.action_top_sellers',
            'cart_abandonment': 'smart_ecommerce_extension.action_cart_abandonment_report',
            'full_dashboard': 'smart_ecommerce_extension.action_ecommerce_analytics',
        }
        
        action = self.env.ref(action_map[self.report_type]).read()[0]
        
        # Add date filters to domain
        action['domain'] = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        
        if self.company_id:
            action['domain'].append(('company_id', '=', self.company_id.id))
        
        action['context'] = {
            'default_date_from': self.date_from,
            'default_date_to': self.date_to,
        }
        
        return action

