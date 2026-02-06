# Part of GPCB. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

API_PREFIX = '/api/v1'


class GpcbApiReport(http.Controller):

    # ------------------------------------------------------------------
    # GET /api/v1/reports/dashboard — Dashboard summary
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/reports/dashboard',
        type='http', auth='bearer', methods=['GET'],
        csrf=False, save_session=False, readonly=True,
    )
    def dashboard(self, **kw):
        """Return a summary dashboard with key financial metrics.

        Designed for the iOS reporting app (Phase 9).
        """
        company = request.env.company

        # Totals for current period
        period_start = kw.get('date_from', '')
        period_end = kw.get('date_to', '')

        Move = request.env['account.move']

        # Revenue (posted customer invoices)
        inv_domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'),
            ('company_id', '=', company.id),
        ]
        if period_start:
            inv_domain.append(('invoice_date', '>=', period_start))
        if period_end:
            inv_domain.append(('invoice_date', '<=', period_end))

        invoices = Move.search(inv_domain)
        total_revenue = sum(invoices.mapped('amount_untaxed'))
        total_iva_collected = sum(invoices.mapped('amount_tax'))

        # Expenses (posted vendor bills)
        bill_domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice'),
            ('company_id', '=', company.id),
        ]
        if period_start:
            bill_domain.append(('invoice_date', '>=', period_start))
        if period_end:
            bill_domain.append(('invoice_date', '<=', period_end))

        bills = Move.search(bill_domain)
        total_expenses = sum(bills.mapped('amount_untaxed'))
        total_iva_paid = sum(bills.mapped('amount_tax'))

        # DIAN status
        dian_domain = [
            ('state', '=', 'posted'),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('company_id', '=', company.id),
        ]
        if period_start:
            dian_domain.append(('invoice_date', '>=', period_start))

        all_edi_invoices = Move.search(dian_domain)
        dian_stats = {
            'total': len(all_edi_invoices),
            'validated': len(all_edi_invoices.filtered(
                lambda m: getattr(m, 'l10n_co_edi_state', '') == 'validated'
            )),
            'pending': len(all_edi_invoices.filtered(
                lambda m: getattr(m, 'l10n_co_edi_state', '') == 'pending'
            )),
            'rejected': len(all_edi_invoices.filtered(
                lambda m: getattr(m, 'l10n_co_edi_state', '') == 'rejected'
            )),
        }

        # Outstanding receivables / payables
        receivable = sum(invoices.mapped('amount_residual'))
        payable = sum(bills.mapped('amount_residual'))

        return request.make_json_response({
            'status': 'success',
            'data': {
                'company': company.name,
                'currency': company.currency_id.name,
                'period': {'from': period_start, 'to': period_end},
                'revenue': total_revenue,
                'expenses': total_expenses,
                'net_income': total_revenue - total_expenses,
                'iva_collected': total_iva_collected,
                'iva_paid': total_iva_paid,
                'iva_payable': total_iva_collected - total_iva_paid,
                'receivable': receivable,
                'payable': payable,
                'dian': dian_stats,
            },
        })

    # ------------------------------------------------------------------
    # GET /api/v1/reports/dian-status — DIAN submission status
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/reports/dian-status',
        type='http', auth='bearer', methods=['GET'],
        csrf=False, save_session=False, readonly=True,
    )
    def dian_status(self, **kw):
        """Return DIAN submission status for recent invoices."""
        limit = min(int(kw.get('limit', 50)), 200)
        offset = int(kw.get('offset', 0))

        domain = [
            ('state', '=', 'posted'),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('company_id', '=', request.env.company.id),
        ]
        if kw.get('dian_state'):
            domain.append(('l10n_co_edi_state', '=', kw['dian_state']))

        invoices = request.env['account.move'].search(
            domain, limit=limit, offset=offset, order='invoice_date desc',
        )
        total = request.env['account.move'].search_count(domain)

        items = []
        for inv in invoices:
            items.append({
                'id': inv.id,
                'name': inv.name,
                'partner_name': inv.partner_id.name,
                'invoice_date': str(inv.invoice_date or ''),
                'amount_total': inv.amount_total,
                'dian_state': getattr(inv, 'l10n_co_edi_state', '') or '',
                'cufe': getattr(inv, 'l10n_co_edi_cufe_cude', '') or '',
            })

        return request.make_json_response({
            'status': 'success',
            'data': {
                'items': items,
                'total': total,
                'limit': limit,
                'offset': offset,
            },
        })
