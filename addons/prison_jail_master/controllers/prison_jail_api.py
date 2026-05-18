# Part of TNPD Prison Management System.
# License: LGPL-3

"""
Prison Jail Hierarchy REST API
==============================

Public (no auth) endpoints for building cascading jail dropdowns in
mobile / web clients before a transfer request is submitted.

Endpoint overview
-----------------
GET  /api/jails/central                     → all active central jails
GET  /api/jails/district?central_id=<id>   → district jails under a central jail
GET  /api/jails/sub?district_id=<id>       → sub jails under a district jail
GET  /api/jails/<id>                        → single jail detail

Pagination
----------
All list endpoints accept ``page`` (default 1) and ``limit`` (default 50,
max 200) query parameters.

All responses are JSON objects:
    { "success": true, "data": [...], "total_count": N, "page": P, "limit": L }
"""

import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_MAX_LIMIT = 200


class PrisonJailApiController(http.Controller):

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _json_response(self, data, status=200):
        return request.make_response(
            json.dumps(data, default=str),
            headers=[('Content-Type', 'application/json')],
            status=status,
        )

    def _ok(self, data, total_count, page, limit):
        return self._json_response({
            'success': True,
            'total_count': total_count,
            'page': page,
            'limit': limit,
            'data': data,
        })

    def _err(self, message, status=400):
        return self._json_response(
            {'success': False, 'message': message}, status=status
        )

    def _parse_pagination(self, kwargs):
        """Parse and clamp page / limit from query params."""
        try:
            page = max(1, int(kwargs.get('page', 1)))
            limit = max(1, min(_MAX_LIMIT, int(kwargs.get('limit', 50))))
        except (TypeError, ValueError) as exc:
            raise ValueError(f'Invalid pagination parameter: {exc}') from exc
        return page, limit

    def _format_jail(self, rec):
        return {
            'id': rec.id,
            'name': rec.name,
            'code': rec.code or '',
            'jail_type': rec.jail_type,
            'parent_id': rec.parent_id.id if rec.parent_id else None,
            'parent_name': rec.parent_id.name if rec.parent_id else '',
            'central_jail_id': rec.central_jail_id.id if rec.central_jail_id else None,
            'central_jail_name': rec.central_jail_id.name if rec.central_jail_id else '',
            'district': rec.district or '',
            'state': rec.state_id.name if rec.state_id else '',
            'external_ref': rec.external_ref or '',
            'child_count': rec.child_count,
        }

    def _fetch_list(self, domain, kwargs):
        """Execute paginated search and return formatted payload."""
        page, limit = self._parse_pagination(kwargs)
        offset = (page - 1) * limit
        Jail = request.env['prison.jail'].sudo()
        total = Jail.search_count(domain)
        records = Jail.search(domain, offset=offset, limit=limit, order='sequence, name')
        return [self._format_jail(r) for r in records], total, page, limit

    # ── API 1: Central Jails ─────────────────────────────────────────────────

    @http.route(
        '/api/jails/central',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def get_central_jails(self, **kwargs):
        """
        Return all active Central Jails.

        Query params: page, limit
        Response: { success, total_count, page, limit, data: [jail, ...] }
        """
        try:
            domain = [('jail_type', '=', 'central_jail'), ('active', '=', True)]
            data, total, page, limit = self._fetch_list(domain, kwargs)
            return self._ok(data, total, page, limit)
        except ValueError as exc:
            return self._err(str(exc))
        except Exception as exc:
            _logger.exception('GET /api/jails/central failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ── API 2: District Jails by Central Jail ────────────────────────────────

    @http.route(
        '/api/jails/district',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def get_district_jails(self, **kwargs):
        """
        Return District Jails that belong to a given Central Jail.

        Query params: central_id (required), page, limit

        Example:
            GET /api/jails/district?central_id=3
        """
        try:
            central_id = kwargs.get('central_id')
            if not central_id:
                return self._err('Missing required query parameter: central_id')
            try:
                central_id = int(central_id)
            except ValueError:
                return self._err('central_id must be an integer')

            central = request.env['prison.jail'].sudo().browse(central_id)
            if not central.exists() or central.jail_type != 'central_jail':
                return self._err(
                    f'No active Central Jail found with id={central_id}', status=404
                )

            domain = [
                ('jail_type', '=', 'district_jail'),
                ('parent_id', '=', central_id),
                ('active', '=', True),
            ]
            data, total, page, limit = self._fetch_list(domain, kwargs)
            return self._ok(data, total, page, limit)

        except ValueError as exc:
            return self._err(str(exc))
        except Exception as exc:
            _logger.exception('GET /api/jails/district failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ── API 3: Sub Jails by District Jail ────────────────────────────────────

    @http.route(
        '/api/jails/sub',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def get_sub_jails(self, **kwargs):
        """
        Return Sub Jails that belong to a given District Jail.

        Query params: district_id (required), page, limit

        Example:
            GET /api/jails/sub?district_id=7
        """
        try:
            district_id = kwargs.get('district_id')
            if not district_id:
                return self._err('Missing required query parameter: district_id')
            try:
                district_id = int(district_id)
            except ValueError:
                return self._err('district_id must be an integer')

            district = request.env['prison.jail'].sudo().browse(district_id)
            if not district.exists() or district.jail_type != 'district_jail':
                return self._err(
                    f'No active District Jail found with id={district_id}', status=404
                )

            domain = [
                ('jail_type', '=', 'sub_jail'),
                ('parent_id', '=', district_id),
                ('active', '=', True),
            ]
            data, total, page, limit = self._fetch_list(domain, kwargs)
            return self._ok(data, total, page, limit)

        except ValueError as exc:
            return self._err(str(exc))
        except Exception as exc:
            _logger.exception('GET /api/jails/sub failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ── API 4: Single Jail Detail ────────────────────────────────────────────

    @http.route(
        '/api/jails/<int:jail_id>',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def get_jail_detail(self, jail_id, **_kwargs):
        """
        Return full detail for a single prison.jail record.

        Example:
            GET /api/jails/12
        """
        try:
            jail = request.env['prison.jail'].sudo().browse(jail_id)
            if not jail.exists() or not jail.active:
                return self._err(f'Jail with id={jail_id} not found', status=404)

            payload = self._format_jail(jail)

            # Include children summary for central / district jails
            if jail.jail_type != 'sub_jail':
                children = request.env['prison.jail'].sudo().search([
                    ('parent_id', '=', jail.id),
                    ('active', '=', True),
                ], order='sequence, name')
                payload['children'] = [
                    {'id': c.id, 'name': c.name, 'code': c.code or '',
                     'jail_type': c.jail_type}
                    for c in children
                ]

            return self._json_response({'success': True, 'data': payload})

        except Exception as exc:
            _logger.exception('GET /api/jails/%s failed: %s', jail_id, exc)
            return self._err('Internal server error', status=500)

    # ── API 5: Full Hierarchy (for seeding client-side caches) ───────────────

    @http.route(
        '/api/jails/hierarchy',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def get_full_hierarchy(self, **_kwargs):
        """
        Return the complete three-tier hierarchy as a nested structure.
        Intended for client-side caching; not paginated.

        Response shape:
        {
            "success": true,
            "data": [
                {
                    "id": 1, "name": "Central Prison, Chennai", ...
                    "district_jails": [
                        {
                            "id": 10, "name": "Chennai District Jail", ...
                            "sub_jails": [{"id": 20, "name": "S.J. Saidapet"}, ...]
                        }, ...
                    ]
                }, ...
            ]
        }
        """
        try:
            Jail = request.env['prison.jail'].sudo()

            central_jails = Jail.search(
                [('jail_type', '=', 'central_jail'), ('active', '=', True)],
                order='sequence, name',
            )

            result = []
            for cp in central_jails:
                cp_data = self._format_jail(cp)
                cp_data['district_jails'] = []

                district_jails = Jail.search(
                    [('parent_id', '=', cp.id), ('jail_type', '=', 'district_jail'),
                     ('active', '=', True)],
                    order='sequence, name',
                )
                for dj in district_jails:
                    dj_data = self._format_jail(dj)
                    sub_jails = Jail.search(
                        [('parent_id', '=', dj.id), ('jail_type', '=', 'sub_jail'),
                         ('active', '=', True)],
                        order='sequence, name',
                    )
                    dj_data['sub_jails'] = [self._format_jail(sj) for sj in sub_jails]
                    cp_data['district_jails'].append(dj_data)

                result.append(cp_data)

            return self._json_response({'success': True, 'data': result})

        except Exception as exc:
            _logger.exception('GET /api/jails/hierarchy failed: %s', exc)
            return self._err('Internal server error', status=500)
