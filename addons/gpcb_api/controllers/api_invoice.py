# Part of GPCB. See LICENSE file for full copyright and licensing details.

import json
import logging
import time

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)

API_PREFIX = '/api/v1'


class GpcbApiInvoice(http.Controller):

    # ------------------------------------------------------------------
    # POST /api/v1/invoices — Create a draft invoice
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/invoices',
        type='http', auth='bearer', methods=['POST'],
        csrf=False, save_session=False,
    )
    def create_invoice(self, **kw):
        """Create a draft invoice from JSON payload.

        Expected body::

            {
              "partner": {"nit": "900123456", "name": "..."},
              "journal_code": "VET01",
              "lines": [
                {"product_code": "LAB-01", "quantity": 1, "unit_price": 85000}
              ],
              "narration": "...",
              "payment_method": "cash"
            }
        """
        start = time.time()
        try:
            data = request.get_json_data()
            if not data:
                return request.make_json_response(
                    {'status': 'error', 'message': 'Request body is required'},
                    status=400,
                )

            # Resolve partner
            partner = self._resolve_partner(data.get('partner', {}))
            if not partner:
                return request.make_json_response(
                    {'status': 'error', 'message': 'Partner not found or invalid'},
                    status=400,
                )

            # Resolve journal
            journal = self._resolve_journal(data.get('journal_code'))
            if not journal:
                return request.make_json_response(
                    {'status': 'error', 'message': 'Journal not found'},
                    status=400,
                )

            # Build invoice lines
            lines_data = data.get('lines', [])
            if not lines_data:
                return request.make_json_response(
                    {'status': 'error', 'message': 'At least one invoice line is required'},
                    status=400,
                )

            invoice_lines = []
            for idx, line in enumerate(lines_data):
                il = self._build_invoice_line(line, idx)
                if isinstance(il, dict) and il.get('status') == 'error':
                    return request.make_json_response(il, status=400)
                invoice_lines.append(il)

            # Create the invoice
            invoice_vals = {
                'move_type': data.get('move_type', 'out_invoice'),
                'partner_id': partner.id,
                'journal_id': journal.id,
                'narration': data.get('narration', ''),
                'invoice_line_ids': invoice_lines,
            }
            invoice = request.env['account.move'].create(invoice_vals)

            result = self._serialize_invoice(invoice)
            self._log(f'{API_PREFIX}/invoices', 'POST', data, result, 201, start)
            return request.make_json_response(
                {'status': 'success', 'data': result}, status=201,
            )

        except (AccessError, UserError, ValidationError) as e:
            _logger.warning('Invoice creation error: %s', e)
            self._log(f'{API_PREFIX}/invoices', 'POST', None, None, 400, start, error=e)
            return request.make_json_response(
                {'status': 'error', 'message': str(e)}, status=400,
            )
        except Exception as e:
            _logger.exception('Invoice creation failed')
            self._log(f'{API_PREFIX}/invoices', 'POST', None, None, 500, start, error=e)
            return request.make_json_response(
                {'status': 'error', 'message': 'Internal server error'}, status=500,
            )

    # ------------------------------------------------------------------
    # GET /api/v1/invoices/:id — Retrieve invoice with DIAN status
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/invoices/<int:invoice_id>',
        type='http', auth='bearer', methods=['GET'],
        csrf=False, save_session=False, readonly=True,
    )
    def get_invoice(self, invoice_id, **kw):
        """Retrieve a single invoice with its DIAN status."""
        try:
            invoice = request.env['account.move'].browse(invoice_id).exists()
            if not invoice:
                return request.make_json_response(
                    {'status': 'error', 'message': 'Invoice not found'}, status=404,
                )
            result = self._serialize_invoice(invoice)
            return request.make_json_response({'status': 'success', 'data': result})
        except AccessError:
            return request.make_json_response(
                {'status': 'error', 'message': 'Access denied'}, status=403,
            )

    # ------------------------------------------------------------------
    # GET /api/v1/invoices — List invoices (paginated)
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/invoices',
        type='http', auth='bearer', methods=['GET'],
        csrf=False, save_session=False, readonly=True,
    )
    def list_invoices(self, **kw):
        """List invoices with pagination and optional filters."""
        limit = min(int(kw.get('limit', 40)), 200)
        offset = int(kw.get('offset', 0))
        move_type = kw.get('type', 'out_invoice')

        domain = [('move_type', '=', move_type)]
        if kw.get('state'):
            domain.append(('state', '=', kw['state']))
        if kw.get('partner_id'):
            domain.append(('partner_id', '=', int(kw['partner_id'])))
        if kw.get('date_from'):
            domain.append(('invoice_date', '>=', kw['date_from']))
        if kw.get('date_to'):
            domain.append(('invoice_date', '<=', kw['date_to']))

        invoices = request.env['account.move'].search(
            domain, limit=limit, offset=offset, order='id desc',
        )
        total = request.env['account.move'].search_count(domain)

        result = {
            'items': [self._serialize_invoice_summary(inv) for inv in invoices],
            'total': total,
            'limit': limit,
            'offset': offset,
        }
        return request.make_json_response({'status': 'success', 'data': result})

    # ------------------------------------------------------------------
    # POST /api/v1/invoices/:id/confirm — Confirm and trigger DIAN
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/invoices/<int:invoice_id>/confirm',
        type='http', auth='bearer', methods=['POST'],
        csrf=False, save_session=False,
    )
    def confirm_invoice(self, invoice_id, **kw):
        """Confirm an invoice and trigger DIAN submission."""
        start = time.time()
        try:
            invoice = request.env['account.move'].browse(invoice_id).exists()
            if not invoice:
                return request.make_json_response(
                    {'status': 'error', 'message': 'Invoice not found'}, status=404,
                )
            if invoice.state != 'draft':
                return request.make_json_response(
                    {'status': 'error', 'message': 'Only draft invoices can be confirmed'},
                    status=400,
                )
            invoice.action_post()
            result = self._serialize_invoice(invoice)
            self._log(f'{API_PREFIX}/invoices/{invoice_id}/confirm', 'POST', None, result, 200, start)
            return request.make_json_response({'status': 'success', 'data': result})
        except (UserError, ValidationError) as e:
            self._log(f'{API_PREFIX}/invoices/{invoice_id}/confirm', 'POST', None, None, 400, start, error=e)
            return request.make_json_response(
                {'status': 'error', 'message': str(e)}, status=400,
            )

    # ------------------------------------------------------------------
    # POST /api/v1/invoices/:id/cancel — Request cancellation
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/invoices/<int:invoice_id>/cancel',
        type='http', auth='bearer', methods=['POST'],
        csrf=False, save_session=False,
    )
    def cancel_invoice(self, invoice_id, **kw):
        """Cancel an invoice (creates credit note for posted invoices)."""
        start = time.time()
        try:
            invoice = request.env['account.move'].browse(invoice_id).exists()
            if not invoice:
                return request.make_json_response(
                    {'status': 'error', 'message': 'Invoice not found'}, status=404,
                )
            if invoice.state == 'draft':
                invoice.button_cancel()
            elif invoice.state == 'posted':
                # For posted invoices, create a credit note
                credit_note_wizard = request.env['account.move.reversal'].with_context(
                    active_model='account.move', active_ids=invoice.ids,
                ).create({'reason': 'API cancellation request'})
                action = credit_note_wizard.refund_moves()
                credit_note = request.env['account.move'].browse(action.get('res_id'))
                result = self._serialize_invoice(credit_note)
                self._log(f'{API_PREFIX}/invoices/{invoice_id}/cancel', 'POST', None, result, 200, start)
                return request.make_json_response({
                    'status': 'success',
                    'message': 'Credit note created',
                    'data': result,
                })
            else:
                return request.make_json_response(
                    {'status': 'error', 'message': f'Cannot cancel invoice in {invoice.state} state'},
                    status=400,
                )
            result = self._serialize_invoice(invoice)
            self._log(f'{API_PREFIX}/invoices/{invoice_id}/cancel', 'POST', None, result, 200, start)
            return request.make_json_response({'status': 'success', 'data': result})
        except (UserError, ValidationError) as e:
            return request.make_json_response(
                {'status': 'error', 'message': str(e)}, status=400,
            )

    # ------------------------------------------------------------------
    # GET /api/v1/invoices/:id/pdf — Download PDF
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/invoices/<int:invoice_id>/pdf',
        type='http', auth='bearer', methods=['GET'],
        csrf=False, save_session=False, readonly=True,
    )
    def get_invoice_pdf(self, invoice_id, **kw):
        """Download the graphic representation (PDF) of an invoice."""
        invoice = request.env['account.move'].browse(invoice_id).exists()
        if not invoice:
            return request.make_json_response(
                {'status': 'error', 'message': 'Invoice not found'}, status=404,
            )
        report = request.env['ir.actions.report']._get_report_from_name(
            'account.report_invoice_with_payments'
        )
        if not report:
            report = request.env['ir.actions.report']._get_report_from_name(
                'account.report_invoice'
            )
        pdf_content, _content_type = report._render_qweb_pdf(
            'account.report_invoice_with_payments', [invoice.id],
        )
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'attachment; filename="{invoice.name}.pdf"'),
        ]
        return request.make_response(pdf_content, headers)

    # ------------------------------------------------------------------
    # GET /api/v1/invoices/:id/xml — Download signed UBL XML
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/invoices/<int:invoice_id>/xml',
        type='http', auth='bearer', methods=['GET'],
        csrf=False, save_session=False, readonly=True,
    )
    def get_invoice_xml(self, invoice_id, **kw):
        """Download the signed UBL 2.1 XML for an invoice."""
        import base64

        invoice = request.env['account.move'].browse(invoice_id).exists()
        if not invoice:
            return request.make_json_response(
                {'status': 'error', 'message': 'Invoice not found'}, status=404,
            )
        if not invoice.l10n_co_edi_xml_file:
            return request.make_json_response(
                {'status': 'error', 'message': 'No XML file available'}, status=404,
            )
        xml_content = base64.b64decode(invoice.l10n_co_edi_xml_file)
        filename = invoice.l10n_co_edi_xml_filename or f'{invoice.name}.xml'
        headers = [
            ('Content-Type', 'application/xml'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
        ]
        return request.make_response(xml_content, headers)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _resolve_partner(self, partner_data):
        """Find or create a partner from the API payload."""
        if not partner_data:
            return None

        Partner = request.env['res.partner']
        nit = partner_data.get('nit', '').replace('-', '').strip()

        if nit:
            partner = Partner.search([('vat', '=like', f'{nit}%')], limit=1)
            if partner:
                return partner

        if partner_data.get('id'):
            return Partner.browse(int(partner_data['id'])).exists()

        # Create new partner if name provided
        if partner_data.get('name') and nit:
            vals = {
                'name': partner_data['name'],
                'vat': nit,
                'is_company': partner_data.get('is_company', True),
            }
            if partner_data.get('email'):
                vals['email'] = partner_data['email']
            if partner_data.get('phone'):
                vals['phone'] = partner_data['phone']
            return Partner.create(vals)

        return None

    def _resolve_journal(self, journal_code):
        """Find a journal by code."""
        if not journal_code:
            return request.env['account.journal'].search(
                [('type', '=', 'sale')], limit=1,
            )
        return request.env['account.journal'].search(
            [('code', '=', journal_code)], limit=1,
        )

    def _build_invoice_line(self, line_data, idx):
        """Build an invoice line command tuple from API data."""
        vals = {
            'name': line_data.get('description', ''),
            'quantity': line_data.get('quantity', 1),
            'price_unit': line_data.get('unit_price', 0),
        }
        # Resolve product
        product_code = line_data.get('product_code')
        if product_code:
            product = request.env['product.product'].search(
                [('default_code', '=', product_code)], limit=1,
            )
            if product:
                vals['product_id'] = product.id
                if not vals['name']:
                    vals['name'] = product.display_name

        # Resolve taxes
        tax_ids = line_data.get('tax_ids', [])
        if tax_ids:
            taxes = request.env['account.tax'].search(
                [('id', 'in', [int(t) if str(t).isdigit() else 0 for t in tax_ids])],
            )
            if taxes:
                vals['tax_ids'] = [(6, 0, taxes.ids)]

        # Vet/Lab domain fields (stored as custom fields if they exist)
        for vet_field in ('animal_id', 'animal_species', 'animal_name'):
            if line_data.get(vet_field):
                field_name = f'x_vet_{vet_field}'
                if field_name in request.env['account.move.line']._fields:
                    vals[field_name] = line_data[vet_field]

        return (0, 0, vals)

    def _serialize_invoice(self, invoice):
        """Serialize an invoice to a JSON-safe dict."""
        return {
            'id': invoice.id,
            'name': invoice.name,
            'state': invoice.state,
            'move_type': invoice.move_type,
            'partner_id': invoice.partner_id.id,
            'partner_name': invoice.partner_id.name,
            'partner_vat': invoice.partner_id.vat or '',
            'invoice_date': str(invoice.invoice_date or ''),
            'invoice_date_due': str(invoice.invoice_date_due or ''),
            'amount_untaxed': invoice.amount_untaxed,
            'amount_tax': invoice.amount_tax,
            'amount_total': invoice.amount_total,
            'amount_residual': invoice.amount_residual,
            'currency': invoice.currency_id.name,
            'journal_code': invoice.journal_id.code,
            'dian_state': getattr(invoice, 'l10n_co_edi_state', '') or '',
            'cufe': getattr(invoice, 'l10n_co_edi_cufe_cude', '') or '',
            'has_xml': bool(getattr(invoice, 'l10n_co_edi_xml_file', False)),
            'lines': [
                {
                    'id': line.id,
                    'product_code': line.product_id.default_code or '',
                    'description': line.name or '',
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                    'price_total': line.price_total,
                    'tax_ids': line.tax_ids.ids,
                }
                for line in invoice.invoice_line_ids
            ],
        }

    def _serialize_invoice_summary(self, invoice):
        """Lightweight invoice serialization for list views."""
        return {
            'id': invoice.id,
            'name': invoice.name,
            'state': invoice.state,
            'partner_name': invoice.partner_id.name,
            'invoice_date': str(invoice.invoice_date or ''),
            'amount_total': invoice.amount_total,
            'amount_residual': invoice.amount_residual,
            'currency': invoice.currency_id.name,
            'dian_state': getattr(invoice, 'l10n_co_edi_state', '') or '',
        }

    def _log(self, endpoint, method, req_data, resp_data, status, start, error=None):
        """Log an API call."""
        try:
            duration = (time.time() - start) * 1000
            request.env['gpcb.api.log'].sudo().create({
                'endpoint': endpoint,
                'method': method,
                'user_id': request.env.uid,
                'request_body': json.dumps(req_data, default=str)[:10000] if req_data else '',
                'response_body': json.dumps(resp_data, default=str)[:10000] if resp_data else '',
                'status_code': status,
                'duration_ms': duration,
                'ip_address': request.httprequest.remote_addr or '',
                'error_message': str(error)[:5000] if error else '',
            })
        except Exception:
            _logger.warning('Failed to log API call', exc_info=True)
