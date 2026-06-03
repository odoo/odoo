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

import io
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

    # ── Auth helper (mirrors employee_api pattern) ────────────────────────────

    def _require_auth(self):
        uid = request.session.uid
        if not uid:
            return None, self._json_response(
                {'success': False, 'message': 'Authentication required'}, status=401
            )
        return uid, None

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

    # ── Special Women Prison detection ───────────────────────────────────────

    def _is_special_women(self, jail_or_name):
        """Detect Special Women Prisons by name convention."""
        name = jail_or_name if isinstance(jail_or_name, str) else jail_or_name.name
        return 'special' in name.lower()

    # ── Code auto-generation ──────────────────────────────────────────────────

    def _generate_jail_code(self, jail_type, special_women=False):
        if special_women:
            prefix = 'SW'
        else:
            prefix = {'central_jail': 'CP', 'district_jail': 'DJ', 'sub_jail': 'SJ'}.get(jail_type, 'XX')
        Jail = request.env['prison.jail'].sudo()
        existing = Jail.search([('code', 'like', f'{prefix}%'), ('active', 'in', [True, False])])
        nums = []
        for j in existing:
            try:
                nums.append(int(j.code[len(prefix):]))
            except (ValueError, TypeError):
                pass
        return f'{prefix}{max(nums, default=0) + 1:03d}'

    # ── Vacancy helper ────────────────────────────────────────────────────────

    def _vacancy_dict(self, vacancy_map, jail_id):
        v = vacancy_map.get(jail_id)
        if v:
            return {
                'sanctioned_strength': v.sanctioned_strength,
                'occupied_count': v.occupied_count,
                'vacancy_count': v.vacancy_count,
            }
        return {'sanctioned_strength': 0, 'occupied_count': 0, 'vacancy_count': 0}

    # ── API 6: Full Hierarchy WITH Vacancy ───────────────────────────────────

    @http.route(
        '/api/jails/hierarchy-with-vacancy',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def get_hierarchy_with_vacancy(self, **_kwargs):
        """
        Full 3-tier hierarchy with vacancy data merged in.

        Response:
        {
          "success": true,
          "stats": { "central_prisons": N, "district_jails": N, "sub_jails": N, "total": N },
          "data": [
            {
              id, name, code, jail_type, district, ...vacancy fields...,
              "district_jails": [
                { id, name, ..., vacancy fields,
                  "sub_jails": [ { id, name, ..., vacancy fields } ]
                }
              ],
              "direct_sub_jails": [ ... ]
            }
          ],
          "standalone_districts": [...]
        }
        """
        try:
            Jail = request.env['prison.jail'].sudo()
            Vacancy = request.env['prison.vacancy'].sudo()

            vacancy_map = {v.prison_id.id: v for v in Vacancy.search([('active', '=', True)])}

            all_central = Jail.search(
                [('jail_type', '=', 'central_jail'), ('active', '=', True)],
                order='sequence, name',
            )

            # Separate regular Central Prisons from Special Women Prisons by name
            central_prisons = []
            special_women = []

            for cp in all_central:
                cp_data = self._format_jail(cp)
                cp_data.update(self._vacancy_dict(vacancy_map, cp.id))
                cp_data['is_special_women'] = self._is_special_women(cp)

                if self._is_special_women(cp):
                    special_women.append(cp_data)
                else:
                    cp_data['district_jails'] = []
                    cp_data['direct_sub_jails'] = []

                    district_jails = Jail.search(
                        [('parent_id', '=', cp.id), ('jail_type', '=', 'district_jail'), ('active', '=', True)],
                        order='sequence, name',
                    )
                    for dj in district_jails:
                        dj_data = self._format_jail(dj)
                        dj_data.update(self._vacancy_dict(vacancy_map, dj.id))
                        sub_jails = Jail.search(
                            [('parent_id', '=', dj.id), ('jail_type', '=', 'sub_jail'), ('active', '=', True)],
                            order='sequence, name',
                        )
                        dj_data['sub_jails'] = []
                        for sj in sub_jails:
                            sj_data = self._format_jail(sj)
                            sj_data.update(self._vacancy_dict(vacancy_map, sj.id))
                            dj_data['sub_jails'].append(sj_data)
                        cp_data['district_jails'].append(dj_data)

                    direct_sj = Jail.search(
                        [('parent_id', '=', cp.id), ('jail_type', '=', 'sub_jail'), ('active', '=', True)],
                        order='sequence, name',
                    )
                    for sj in direct_sj:
                        sj_data = self._format_jail(sj)
                        sj_data.update(self._vacancy_dict(vacancy_map, sj.id))
                        cp_data['direct_sub_jails'].append(sj_data)

                    central_prisons.append(cp_data)

            standalone = Jail.search(
                [('jail_type', '=', 'district_jail'), ('parent_id', '=', False), ('active', '=', True)],
                order='sequence, name',
            )
            standalone_data = []
            for dj in standalone:
                dj_data = self._format_jail(dj)
                dj_data.update(self._vacancy_dict(vacancy_map, dj.id))
                sub_jails = Jail.search(
                    [('parent_id', '=', dj.id), ('jail_type', '=', 'sub_jail'), ('active', '=', True)],
                    order='sequence, name',
                )
                dj_data['sub_jails'] = []
                for sj in sub_jails:
                    sj_data = self._format_jail(sj)
                    sj_data.update(self._vacancy_dict(vacancy_map, sj.id))
                    dj_data['sub_jails'].append(sj_data)
                standalone_data.append(dj_data)

            total_district = Jail.search_count([('jail_type', '=', 'district_jail'), ('active', '=', True)])
            total_sub = Jail.search_count([('jail_type', '=', 'sub_jail'), ('active', '=', True)])

            return self._json_response({
                'success': True,
                'stats': {
                    'central_prisons': len(central_prisons),
                    'special_women_prisons': len(special_women),
                    'district_jails': total_district,
                    'sub_jails': total_sub,
                    'total': len(all_central) + total_district + total_sub,
                },
                'data': central_prisons,
                'special_women_prisons': special_women,
                'standalone_districts': standalone_data,
            })

        except Exception as exc:
            _logger.exception('GET /api/jails/hierarchy-with-vacancy failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ── API 7: Create Facility ────────────────────────────────────────────────

    @http.route(
        '/api/jails/create',
        auth='none',
        type='http',
        methods=['POST'],
        csrf=False,
    )
    def create_facility(self, **_kwargs):
        """
        Create a new prison/jail facility.

        Request body:
        {
          "jail_type": "central_jail" | "district_jail" | "sub_jail",
          "name": "...",
          "parent_id": <int> | null,
          "district": "...",
          "sanctioned_strength": <int>,
          "occupied_count": <int>,
          "sequence": <int>
        }

        Response: { success, data: { jail, vacancy } }
        """
        uid, err = self._require_auth()
        if err:
            return err

        body = self._parse_body()
        if body is None:
            return self._err('Invalid JSON body.')

        jail_type = body.get('jail_type', '').strip()
        # 'special_women_prison' is a UI-only type; stored as central_jail in prison.jail
        is_special_women_create = (jail_type == 'special_women_prison')
        if is_special_women_create:
            jail_type = 'central_jail'
        valid_types = ['central_jail', 'district_jail', 'sub_jail']
        if jail_type not in valid_types:
            return self._err('jail_type must be one of: central_jail, district_jail, sub_jail, special_women_prison')

        name = (body.get('name') or '').strip()
        if not name:
            return self._err('name is required.')

        parent_id = self._int(body.get('parent_id'))
        sanctioned = max(0, self._int(body.get('sanctioned_strength'), 0))
        occupied = max(0, self._int(body.get('occupied_count'), 0))
        if occupied > sanctioned:
            return self._err('Occupied count cannot exceed sanctioned strength.')

        Jail = request.env['prison.jail'].sudo()
        Vacancy = request.env['prison.vacancy'].sudo()

        # Special Women Prison: no parent, name must contain 'Special'
        if is_special_women_create and parent_id:
            return self._err('Special Women Prison cannot have a parent.')

        # Validate parent
        if jail_type == 'central_jail' and parent_id and not is_special_women_create:
            return self._err('Central Prison cannot have a parent.')
        if jail_type == 'district_jail' and parent_id:
            parent = Jail.browse(parent_id)
            if not parent.exists() or parent.jail_type != 'central_jail':
                return self._err('Parent of a District Jail must be a Central Prison.')
        if jail_type == 'sub_jail':
            if not parent_id:
                return self._err('Sub Jail requires a parent (Central Prison or District Jail).')
            parent = Jail.browse(parent_id)
            if not parent.exists() or parent.jail_type not in ('central_jail', 'district_jail'):
                return self._err('Parent of a Sub Jail must be a Central Prison or District Jail.')

        # Check duplicate name+type
        existing = Jail.search([('name', '=ilike', name), ('jail_type', '=', jail_type)], limit=1)
        if existing:
            return self._err(f'A {jail_type.replace("_", " ").title()} named "{name}" already exists.')

        # Auto-generate code
        code = self._generate_jail_code(jail_type, special_women=is_special_women_create)

        vals = {
            'name': name,
            'jail_type': jail_type,
            'code': code,
            'district': (body.get('district') or '').strip() or False,
            'sequence': self._int(body.get('sequence'), 10),
            'active': True,
        }
        if parent_id:
            vals['parent_id'] = parent_id

        new_jail = Jail.create(vals)

        # Map jail_type → prison.vacancy prison_type
        if is_special_women_create:
            vacancy_type = 'special_prison_women'
        else:
            type_map = {
                'central_jail': 'central_prison',
                'district_jail': 'district_jail',
                'sub_jail': 'sub_jail',
            }
            vacancy_type = type_map[jail_type]

        vacancy = Vacancy.create({
            'prison_id': new_jail.id,
            'prison_name': new_jail.name,
            'prison_type': vacancy_type,
            'sanctioned_strength': sanctioned,
            'occupied_count': occupied,
            'vacancy_count': max(0, sanctioned - occupied),
        })

        return self._json_response({
            'success': True,
            'message': f'Facility "{name}" created successfully.',
            'data': {
                **self._format_jail(new_jail),
                'sanctioned_strength': vacancy.sanctioned_strength,
                'occupied_count': vacancy.occupied_count,
                'vacancy_count': vacancy.vacancy_count,
            },
        }, status=201)

    # ── API 8: Export Hierarchy ───────────────────────────────────────────────

    @http.route(
        '/api/jails/export',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def export_hierarchy(self, **kwargs):
        """
        Export the full prison hierarchy as CSV.
        Optional query params mirror search/filter: q (search term), jail_type.
        """
        uid, err = self._require_auth()
        if err:
            return err

        try:
            Jail = request.env['prison.jail'].sudo()
            Vacancy = request.env['prison.vacancy'].sudo()

            vacancy_map = {v.prison_id.id: v for v in Vacancy.search([('active', '=', True)])}

            domain = [('active', '=', True)]
            q = (kwargs.get('q') or '').strip()
            jt = kwargs.get('jail_type', '').strip()
            if q:
                domain += ['|', ('name', 'ilike', q), ('code', 'ilike', q)]

            # Handle special_women_prison filter (name-based)
            filter_special = (jt == 'special_women_prison')
            if jt == 'central_jail':
                domain.append(('jail_type', '=', 'central_jail'))
            elif jt in ('district_jail', 'sub_jail'):
                domain.append(('jail_type', '=', jt))

            jails = Jail.search(domain, order='jail_type, sequence, name')

            # Apply special women filter post-query
            if filter_special:
                jails = jails.filtered(lambda j: self._is_special_women(j))
            elif jt == 'central_jail':
                jails = jails.filtered(lambda j: not self._is_special_women(j))

            output = io.StringIO()
            import csv as csv_mod
            writer = csv_mod.writer(output)
            writer.writerow([
                'Facility Code', 'Facility Name', 'Facility Type',
                'Parent Facility', 'District',
                'Sanctioned Strength', 'Filled Strength', 'Vacancy Count',
                'Status',
            ])

            for j in jails:
                if j.jail_type == 'central_jail':
                    type_label = 'Special Women Prison' if self._is_special_women(j) else 'Central Prison'
                elif j.jail_type == 'district_jail':
                    type_label = 'District Jail'
                else:
                    type_label = 'Sub Jail'
                v = vacancy_map.get(j.id)
                writer.writerow([
                    j.code or '',
                    j.name,
                    type_label,
                    j.parent_id.name if j.parent_id else '',
                    j.district or '',
                    v.sanctioned_strength if v else 0,
                    v.occupied_count if v else 0,
                    v.vacancy_count if v else 0,
                    'Active' if j.active else 'Inactive',
                ])

            csv_bytes = output.getvalue().encode('utf-8-sig')
            return request.make_response(
                csv_bytes,
                headers=[
                    ('Content-Type', 'text/csv; charset=utf-8'),
                    ('Content-Disposition', 'attachment; filename="prisons_hierarchy.csv"'),
                ],
            )

        except Exception as exc:
            _logger.exception('GET /api/jails/export failed: %s', exc)
            return self._err('Internal server error', status=500)
