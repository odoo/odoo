# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo import http
from odoo.http import request


class OnboardingController(http.Controller):
    @http.route('/onboarding/<string:route_name>', auth='user', type='json')
    def get_onboarding_data(self, route_name=None, context=None):
        if not request.env.user.has_group('base.group_system'):
            return {}

        if context:
            request.update_context(**context)
        onboarding = request.env['onboarding.onboarding'].search([('route_name', '=', route_name)])
        if onboarding:
            try:
                progress = onboarding._search_or_create_progress()
            except IntegrityError:  # Another worker created the record at the same time
                return {'code': 503}  # Temporarily unavailable - Invites client to try again

            if not progress.is_onboarding_closed:
                # JS implementation of the onboarding panel expects this data structure
                return {
                    'html': request.env['ir.qweb']._render(
                        'onboarding.onboarding_panel', onboarding._prepare_rendering_values())
                }

        return {}
