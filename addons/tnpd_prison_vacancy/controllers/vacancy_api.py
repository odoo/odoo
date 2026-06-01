# Part of TNPD Prison Management System.
# License: LGPL-3

"""
Prison Vacancy REST API
=======================

Auth: all endpoints require a valid Odoo user session (auth='user').

Endpoints
---------
POST /api/transfer/check-availability
    Check whether a target prison has staff vacancy.
    Request : { "prison_id": <int> }
    Response: vacancy detail + vacancy_available flag

POST /api/vacancy/import
    Bulk-upsert vacancy records.
    Request : { "records": [ { "prison_id": <int>, "sanctioned_strength": <int>,
                                "occupied_count": <int>, "vacancy_count": <int> } ] }

POST /api/vacancy/update
    Update a single prison's vacancy figures.
    Request : { "prison_id": <int>, "sanctioned_strength"?: <int>,
                "occupied_count"?: <int>, "vacancy_count"?: <int> }
"""

import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class VacancyApiController(http.Controller):

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _json(self, data, status=200):
        return request.make_response(
            json.dumps(data, default=str),
            headers=[('Content-Type', 'application/json')],
            status=status,
        )

    def _ok(self, data):
        return self._json({'success': True, **data})

    def _err(self, message, status=400):
        return self._json({'success': False, 'message': message}, status=status)

    def _parse_body(self):
        try:
            body = request.httprequest.get_data(as_text=True)
            return json.loads(body) if body else {}
        except Exception:
            return None

    def _int(self, value, default=None):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    # ── POST /api/transfer/check-availability ─────────────────────────────────

    @http.route(
        '/api/transfer/check-availability',
        type='http',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def check_availability(self, **kwargs):
        body = self._parse_body()
        if body is None:
            return self._err('Invalid JSON body.')

        prison_id = self._int(body.get('prison_id'))
        if not prison_id:
            return self._err('prison_id is required and must be an integer.')

        vacancy = request.env['prison.vacancy'].sudo().search(
            [('prison_id', '=', prison_id), ('active', '=', True)],
            limit=1,
        )
        if not vacancy:
            return self._err(f'No vacancy record found for prison_id {prison_id}.', status=404)

        available = vacancy.is_vacancy_available()
        return self._ok({
            'vacancy_available': available,
            'prison_id': prison_id,
            'prison_name': vacancy.prison_name,
            'sanctioned_strength': vacancy.sanctioned_strength,
            'occupied_count': vacancy.occupied_count,
            'vacancy_count': vacancy.vacancy_count,
            'message': (
                'Vacancy available. Transfer can be processed.'
                if available else
                'No vacancy available in requested prison.'
            ),
        })

    # ── POST /api/vacancy/import ───────────────────────────────────────────────

    @http.route(
        '/api/vacancy/import',
        type='http',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def vacancy_import(self, **kwargs):
        body = self._parse_body()
        if body is None:
            return self._err('Invalid JSON body.')

        records = body.get('records')
        if not isinstance(records, list) or not records:
            return self._err('"records" must be a non-empty list.')

        Vacancy = request.env['prison.vacancy'].sudo()
        Jail = request.env['prison.jail'].sudo()

        created = updated = errors = 0
        error_details = []

        for i, rec in enumerate(records):
            prison_id = self._int(rec.get('prison_id'))
            if not prison_id:
                errors += 1
                error_details.append(f'Record {i}: missing or invalid prison_id.')
                continue

            jail = Jail.browse(prison_id)
            if not jail.exists():
                errors += 1
                error_details.append(f'Record {i}: prison_id {prison_id} not found in prison master.')
                continue

            vals = {
                'sanctioned_strength': self._int(rec.get('sanctioned_strength'), 0),
                'occupied_count': self._int(rec.get('occupied_count'), 0),
                'vacancy_count': self._int(rec.get('vacancy_count'), 0),
            }

            existing = Vacancy.search([('prison_id', '=', prison_id)], limit=1)
            if existing:
                existing.write(vals)
                updated += 1
            else:
                prison_type = rec.get('prison_type', 'sub_jail')
                valid_types = [k for k, _ in Vacancy._fields['prison_type'].selection]
                if prison_type not in valid_types:
                    prison_type = 'sub_jail'
                vals.update({
                    'prison_id': prison_id,
                    'prison_name': rec.get('prison_name') or jail.name,
                    'prison_type': prison_type,
                })
                Vacancy.create(vals)
                created += 1

        return self._ok({
            'created': created,
            'updated': updated,
            'errors': errors,
            'error_details': error_details,
            'message': f'Import complete: {created} created, {updated} updated, {errors} errors.',
        })

    # ── POST /api/vacancy/update ──────────────────────────────────────────────

    @http.route(
        '/api/vacancy/update',
        type='http',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def vacancy_update(self, **kwargs):
        body = self._parse_body()
        if body is None:
            return self._err('Invalid JSON body.')

        prison_id = self._int(body.get('prison_id'))
        if not prison_id:
            return self._err('prison_id is required and must be an integer.')

        Vacancy = request.env['prison.vacancy'].sudo()
        vacancy = Vacancy.search([('prison_id', '=', prison_id), ('active', '=', True)], limit=1)
        if not vacancy:
            return self._err(f'No active vacancy record found for prison_id {prison_id}.', status=404)

        vals = {}
        for field in ('sanctioned_strength', 'occupied_count', 'vacancy_count'):
            if field in body:
                v = self._int(body[field])
                if v is None or v < 0:
                    return self._err(f'{field} must be a non-negative integer.')
                vals[field] = v

        if not vals:
            return self._err('No updatable fields provided. Provide at least one of: '
                             'sanctioned_strength, occupied_count, vacancy_count.')

        vacancy.write(vals)
        return self._ok({
            'prison_id': prison_id,
            'prison_name': vacancy.prison_name,
            'sanctioned_strength': vacancy.sanctioned_strength,
            'occupied_count': vacancy.occupied_count,
            'vacancy_count': vacancy.vacancy_count,
            'message': 'Vacancy record updated successfully.',
        })
