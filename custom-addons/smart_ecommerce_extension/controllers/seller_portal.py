# -*- coding: utf-8 -*-
# Part of SMART eCommerce Extension. See LICENSE file for full copyright and licensing details.

import logging
from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

_logger = logging.getLogger(__name__)


class SellerPortal(CustomerPortal):
    """Portal controller for Marketplace Sellers"""

    def _prepare_home_portal_values(self, counters):
        """Add seller counters to portal home"""
        values = super()._prepare_home_portal_values(counters)
        
        seller = self._get_current_seller()
        if seller:
            if 'seller_product_count' in counters:
                values['seller_product_count'] = seller.product_count
            if 'seller_order_count' in counters:
                values['seller_order_count'] = seller.order_count
        
        return values

    def _get_current_seller(self):
        """Get seller record for current user"""
        if not request.env.user._is_public():
            return request.env['marketplace.seller'].sudo().search([
                ('user_id', '=', request.env.user.id)
            ], limit=1)
        return False

    # ==========================================
    # SELLER DASHBOARD
    # ==========================================

    @http.route(['/my/seller', '/my/seller/dashboard'], type='http', auth='user', website=True)
    def seller_dashboard(self, **kw):
        """Seller dashboard with statistics"""
        seller = self._get_current_seller()
        
        if not seller:
            return request.redirect('/my/seller/register')
        
        if seller.state not in ('approved', 'pending'):
            return request.render('smart_ecommerce_extension.seller_not_approved', {
                'seller': seller,
            })
        
        dashboard_data = seller.get_portal_dashboard_data()
        
        # Get recent orders
        recent_orders = request.env['sale.order'].sudo().search([
            ('partner_id', '=', seller.partner_id.id),
        ], limit=5, order='date_order desc')
        
        values = {
            'page_name': 'seller_dashboard',
            'seller': seller,
            'dashboard': dashboard_data,
            'recent_orders': recent_orders,
        }
        
        return request.render('smart_ecommerce_extension.seller_dashboard', values)

    @http.route('/my/seller/register', type='http', auth='user', website=True)
    def seller_register(self, **kw):
        """Seller registration form"""
        seller = self._get_current_seller()
        
        if seller:
            return request.redirect('/my/seller/dashboard')
        
        countries = request.env['res.country'].sudo().search([])
        
        values = {
            'page_name': 'seller_register',
            'countries': countries,
            'error': kw.get('error'),
        }
        
        return request.render('smart_ecommerce_extension.seller_register', values)

    @http.route('/my/seller/register/submit', type='http', auth='user', website=True, methods=['POST'])
    def seller_register_submit(self, **kw):
        """Process seller registration"""
        try:
            # Validate required fields
            required = ['company_name', 'phone', 'city']
            for field in required:
                if not kw.get(field):
                    return request.redirect('/my/seller/register?error=missing_fields')
            
            # Check if user already has a seller account
            existing = request.env['marketplace.seller'].sudo().search([
                ('user_id', '=', request.env.user.id)
            ], limit=1)
            if existing:
                return request.redirect('/my/seller/dashboard')
            
            # Check company name uniqueness
            existing_company = request.env['marketplace.seller'].sudo().search([
                ('company_name', '=', kw.get('company_name'))
            ], limit=1)
            if existing_company:
                return request.redirect('/my/seller/register?error=company_exists')
            
            # Create seller
            vals = {
                'user_id': request.env.user.id,
                'company_name': kw.get('company_name'),
                'phone': kw.get('phone'),
                'city': kw.get('city'),
                'street': kw.get('street', ''),
                'tax_id': kw.get('tax_id', ''),
                'bank_name': kw.get('bank_name', ''),
                'bank_account': kw.get('bank_account', ''),
                'store_description': kw.get('store_description', ''),
                'state': 'draft',
            }
            
            if kw.get('country_id'):
                vals['country_id'] = int(kw['country_id'])
            
            seller = request.env['marketplace.seller'].sudo().create(vals)
            
            # Handle file uploads
            if kw.get('kyc_doc'):
                seller.sudo().write({
                    'kyc_doc': kw['kyc_doc'].read(),
                    'kyc_doc_filename': kw['kyc_doc'].filename,
                })
            
            if kw.get('store_logo'):
                seller.sudo().write({
                    'store_logo': kw['store_logo'].read(),
                })
            
            return request.redirect('/my/seller/dashboard?success=registered')
            
        except Exception as e:
            _logger.error(f"Seller registration error: {str(e)}", exc_info=True)
            return request.redirect('/my/seller/register?error=server_error')

    # ==========================================
    # SELLER ORDERS
    # ==========================================

    @http.route(['/my/seller/orders', '/my/seller/orders/page/<int:page>'], 
                type='http', auth='user', website=True)
    def seller_orders(self, page=1, sortby=None, filterby=None, **kw):
        """Seller orders list with pagination"""
        seller = self._get_current_seller()
        
        if not seller or seller.state != 'approved':
            return request.redirect('/my/seller/dashboard')
        
        SaleOrder = request.env['sale.order'].sudo()
        
        # Sorting
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'date_order desc'},
            'date_asc': {'label': _('Oldest'), 'order': 'date_order asc'},
            'name': {'label': _('Order #'), 'order': 'name'},
            'amount': {'label': _('Amount'), 'order': 'amount_total desc'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        # Filtering
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'draft': {'label': _('Quotation'), 'domain': [('state', '=', 'draft')]},
            'sale': {'label': _('Sales Order'), 'domain': [('state', '=', 'sale')]},
            'done': {'label': _('Done'), 'domain': [('state', '=', 'done')]},
            'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
        }
        if not filterby:
            filterby = 'all'
        domain = searchbar_filters[filterby]['domain']
        
        # Base domain
        domain += [('partner_id', '=', seller.partner_id.id)]
        
        # Pager
        order_count = SaleOrder.search_count(domain)
        pager = portal_pager(
            url='/my/seller/orders',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=order_count,
            page=page,
            step=20
        )
        
        orders = SaleOrder.search(
            domain,
            order=order,
            limit=20,
            offset=pager['offset']
        )
        
        values = {
            'page_name': 'seller_orders',
            'seller': seller,
            'orders': orders,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
        }
        
        return request.render('smart_ecommerce_extension.seller_orders', values)

    @http.route('/my/seller/orders/<int:order_id>', type='http', auth='user', website=True)
    def seller_order_detail(self, order_id, **kw):
        """View single order details"""
        seller = self._get_current_seller()
        
        if not seller or seller.state != 'approved':
            return request.redirect('/my/seller/dashboard')
        
        order = request.env['sale.order'].sudo().browse(order_id)
        
        if not order.exists() or order.partner_id.id != seller.partner_id.id:
            return request.redirect('/my/seller/orders')
        
        values = {
            'page_name': 'seller_order_detail',
            'seller': seller,
            'order': order,
        }
        
        return request.render('smart_ecommerce_extension.seller_order_detail', values)

    # ==========================================
    # SELLER PAYMENTS
    # ==========================================

    @http.route(['/my/seller/payments', '/my/seller/payments/page/<int:page>'],
                type='http', auth='user', website=True)
    def seller_payments(self, page=1, **kw):
        """Seller payments/earnings history"""
        seller = self._get_current_seller()
        
        if not seller or seller.state != 'approved':
            return request.redirect('/my/seller/dashboard')
        
        payment_data = seller.get_portal_payments(page=page)
        
        # Calculate totals
        total_earnings = seller.total_sales * (1 - seller.commission_rate / 100)
        total_commission = seller.total_sales * (seller.commission_rate / 100)
        
        pager = portal_pager(
            url='/my/seller/payments',
            total=len(payment_data['payments']) * 10,  # Approximate
            page=page,
            step=20
        )
        
        values = {
            'page_name': 'seller_payments',
            'seller': seller,
            'payments': payment_data['payments'],
            'pager': pager,
            'total_earnings': total_earnings,
            'total_commission': total_commission,
            'commission_rate': seller.commission_rate,
        }
        
        return request.render('smart_ecommerce_extension.seller_payments', values)

    # ==========================================
    # SELLER PROFILE
    # ==========================================

    @http.route('/my/seller/profile', type='http', auth='user', website=True)
    def seller_profile(self, **kw):
        """Seller profile edit"""
        seller = self._get_current_seller()
        
        if not seller:
            return request.redirect('/my/seller/register')
        
        countries = request.env['res.country'].sudo().search([])
        
        values = {
            'page_name': 'seller_profile',
            'seller': seller,
            'countries': countries,
            'success': kw.get('success'),
            'error': kw.get('error'),
        }
        
        return request.render('smart_ecommerce_extension.seller_profile', values)

    @http.route('/my/seller/profile/update', type='http', auth='user', website=True, methods=['POST'])
    def seller_profile_update(self, **kw):
        """Update seller profile"""
        seller = self._get_current_seller()
        
        if not seller:
            return request.redirect('/my/seller/register')
        
        try:
            vals = {}
            
            # Editable fields
            editable_fields = ['phone', 'street', 'city', 'tax_id', 'bank_name', 
                             'bank_account', 'store_description']
            for field in editable_fields:
                if kw.get(field) is not None:
                    vals[field] = kw.get(field)
            
            if kw.get('country_id'):
                vals['country_id'] = int(kw['country_id'])
            
            # Handle file uploads
            if kw.get('kyc_doc'):
                vals['kyc_doc'] = kw['kyc_doc'].read()
                vals['kyc_doc_filename'] = kw['kyc_doc'].filename
            
            if kw.get('store_logo'):
                vals['store_logo'] = kw['store_logo'].read()
            
            if kw.get('store_banner'):
                vals['store_banner'] = kw['store_banner'].read()
            
            if vals:
                seller.sudo().write(vals)
            
            return request.redirect('/my/seller/profile?success=updated')
            
        except Exception as e:
            _logger.error(f"Seller profile update error: {str(e)}", exc_info=True)
            return request.redirect('/my/seller/profile?error=server_error')

    @http.route('/my/seller/submit', type='http', auth='user', website=True, methods=['POST'])
    def seller_submit_approval(self, **kw):
        """Submit seller profile for approval"""
        seller = self._get_current_seller()
        
        if not seller or seller.state != 'draft':
            return request.redirect('/my/seller/dashboard')
        
        try:
            seller.sudo().action_submit_for_approval()
            return request.redirect('/my/seller/dashboard?success=submitted')
        except Exception as e:
            _logger.error(f"Seller submit error: {str(e)}", exc_info=True)
            return request.redirect('/my/seller/dashboard?error=' + str(e))

