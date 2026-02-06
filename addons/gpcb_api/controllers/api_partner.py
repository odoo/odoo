# Part of GPCB. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)

API_PREFIX = '/api/v1'


class GpcbApiPartner(http.Controller):

    # ------------------------------------------------------------------
    # GET /api/v1/partners — Search partners
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/partners',
        type='http', auth='bearer', methods=['GET'],
        csrf=False, save_session=False, readonly=True,
    )
    def list_partners(self, **kw):
        """Search partners by NIT, name, or other criteria."""
        limit = min(int(kw.get('limit', 40)), 200)
        offset = int(kw.get('offset', 0))

        domain = []
        if kw.get('nit'):
            nit = kw['nit'].replace('-', '').strip()
            domain.append(('vat', '=like', f'{nit}%'))
        if kw.get('name'):
            domain.append(('name', 'ilike', kw['name']))
        if kw.get('is_company') is not None:
            domain.append(('is_company', '=', kw.get('is_company') in ('true', '1', 'True')))
        if kw.get('customer_rank'):
            domain.append(('customer_rank', '>', 0))
        if kw.get('supplier_rank'):
            domain.append(('supplier_rank', '>', 0))

        partners = request.env['res.partner'].search(
            domain, limit=limit, offset=offset, order='name',
        )
        total = request.env['res.partner'].search_count(domain)

        return request.make_json_response({
            'status': 'success',
            'data': {
                'items': [self._serialize_partner(p) for p in partners],
                'total': total,
                'limit': limit,
                'offset': offset,
            },
        })

    # ------------------------------------------------------------------
    # GET /api/v1/partners/:id — Retrieve partner
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/partners/<int:partner_id>',
        type='http', auth='bearer', methods=['GET'],
        csrf=False, save_session=False, readonly=True,
    )
    def get_partner(self, partner_id, **kw):
        """Retrieve a single partner with full details."""
        partner = request.env['res.partner'].browse(partner_id).exists()
        if not partner:
            return request.make_json_response(
                {'status': 'error', 'message': 'Partner not found'}, status=404,
            )
        return request.make_json_response({
            'status': 'success',
            'data': self._serialize_partner(partner),
        })

    # ------------------------------------------------------------------
    # POST /api/v1/partners — Create partner
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/partners',
        type='http', auth='bearer', methods=['POST'],
        csrf=False, save_session=False,
    )
    def create_partner(self, **kw):
        """Create a new partner with NIT validation."""
        try:
            data = request.get_json_data()
            if not data or not data.get('name'):
                return request.make_json_response(
                    {'status': 'error', 'message': 'Partner name is required'}, status=400,
                )

            vals = {
                'name': data['name'],
                'is_company': data.get('is_company', True),
            }

            nit = (data.get('nit') or '').replace('-', '').strip()
            if nit:
                # Check for duplicate NIT
                existing = request.env['res.partner'].search(
                    [('vat', '=like', f'{nit}%')], limit=1,
                )
                if existing:
                    return request.make_json_response({
                        'status': 'error',
                        'message': f'Partner with NIT {nit} already exists (ID: {existing.id})',
                    }, status=409)
                vals['vat'] = nit

            # Identification type
            id_type = data.get('identification_type', 'nit')
            id_type_record = request.env['l10n_latam.identification.type'].search(
                [('l10n_co_document_code', '=', id_type)], limit=1,
            )
            if id_type_record:
                vals['l10n_latam_identification_type_id'] = id_type_record.id

            # Optional fields
            for field in ('email', 'phone', 'mobile', 'street', 'city', 'zip'):
                if data.get(field):
                    vals[field] = data[field]

            if data.get('country_code'):
                country = request.env['res.country'].search(
                    [('code', '=', data['country_code'].upper())], limit=1,
                )
                if country:
                    vals['country_id'] = country.id

            if data.get('state_code') and vals.get('country_id'):
                state = request.env['res.country.state'].search([
                    ('code', '=', data['state_code']),
                    ('country_id', '=', vals['country_id']),
                ], limit=1)
                if state:
                    vals['state_id'] = state.id

            # Colombian fiscal classification
            if data.get('tax_regime'):
                vals['l10n_co_edi_tax_regime'] = data['tax_regime']
            if data.get('gran_contribuyente') is not None:
                vals['l10n_co_edi_gran_contribuyente'] = data['gran_contribuyente']

            partner = request.env['res.partner'].create(vals)
            return request.make_json_response({
                'status': 'success',
                'data': self._serialize_partner(partner),
            }, status=201)

        except (UserError, ValidationError) as e:
            return request.make_json_response(
                {'status': 'error', 'message': str(e)}, status=400,
            )

    # ------------------------------------------------------------------
    # PATCH /api/v1/partners/:id — Update partner
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/partners/<int:partner_id>',
        type='http', auth='bearer', methods=['PATCH'],
        csrf=False, save_session=False,
    )
    def update_partner(self, partner_id, **kw):
        """Update an existing partner."""
        try:
            partner = request.env['res.partner'].browse(partner_id).exists()
            if not partner:
                return request.make_json_response(
                    {'status': 'error', 'message': 'Partner not found'}, status=404,
                )

            data = request.get_json_data()
            if not data:
                return request.make_json_response(
                    {'status': 'error', 'message': 'Request body is required'}, status=400,
                )

            allowed_fields = {
                'name', 'email', 'phone', 'mobile', 'street', 'city', 'zip',
                'vat', 'is_company',
            }
            vals = {k: v for k, v in data.items() if k in allowed_fields}

            if data.get('tax_regime'):
                vals['l10n_co_edi_tax_regime'] = data['tax_regime']

            if vals:
                partner.write(vals)

            return request.make_json_response({
                'status': 'success',
                'data': self._serialize_partner(partner),
            })
        except (UserError, ValidationError) as e:
            return request.make_json_response(
                {'status': 'error', 'message': str(e)}, status=400,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _serialize_partner(self, partner):
        """Serialize a partner to a JSON-safe dict."""
        result = {
            'id': partner.id,
            'name': partner.name,
            'vat': partner.vat or '',
            'is_company': partner.is_company,
            'email': partner.email or '',
            'phone': partner.phone or '',
            'mobile': partner.mobile or '',
            'street': partner.street or '',
            'city': partner.city or '',
            'zip': partner.zip or '',
            'country_code': partner.country_id.code or '',
            'state_code': partner.state_id.code or '',
            'customer_rank': partner.customer_rank,
            'supplier_rank': partner.supplier_rank,
        }
        # Colombian fields (available if l10n_co_edi is installed)
        if hasattr(partner, 'l10n_co_edi_tax_regime'):
            result['tax_regime'] = partner.l10n_co_edi_tax_regime or ''
            result['gran_contribuyente'] = partner.l10n_co_edi_gran_contribuyente or False
            result['autorretenedor'] = partner.l10n_co_edi_autorretenedor or False
            result['fiscal_responsibilities'] = partner.l10n_co_edi_fiscal_responsibilities or ''
        if partner.l10n_latam_identification_type_id:
            result['identification_type'] = partner.l10n_latam_identification_type_id.l10n_co_document_code or ''
        return result
