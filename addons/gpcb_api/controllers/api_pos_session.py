# Part of GPCB. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

API_PREFIX = '/api/v1'


class GpcbApiPosSession(http.Controller):

    # ------------------------------------------------------------------
    # POST /api/v1/pos/sessions/open — Open a new POS session
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/pos/sessions/open',
        type='http', auth='bearer', methods=['POST'],
        csrf=False, save_session=False,
    )
    def open_session(self, **kw):
        """Open a new POS session for the given config."""
        try:
            data = request.get_json_data() or {}
            config_id = data.get('config_id')
            if not config_id:
                return request.make_json_response(
                    {'status': 'error', 'message': 'config_id is required'}, status=400,
                )

            config = request.env['pos.config'].browse(int(config_id)).exists()
            if not config:
                return request.make_json_response(
                    {'status': 'error', 'message': 'POS config not found'}, status=404,
                )

            # Check for existing open session
            existing = request.env['pos.session'].search([
                ('config_id', '=', config.id),
                ('state', '!=', 'closed'),
            ], limit=1)
            if existing:
                return request.make_json_response({
                    'status': 'success',
                    'message': 'Session already open',
                    'data': self._serialize_session(existing),
                })

            session = request.env['pos.session'].create({
                'config_id': config.id,
                'user_id': request.env.uid,
            })
            session.action_pos_session_open()

            return request.make_json_response({
                'status': 'success',
                'data': self._serialize_session(session),
            }, status=201)

        except (UserError, ValidationError) as e:
            return request.make_json_response(
                {'status': 'error', 'message': str(e)}, status=400,
            )

    # ------------------------------------------------------------------
    # POST /api/v1/pos/sessions/:id/close — Close session
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/pos/sessions/<int:session_id>/close',
        type='http', auth='bearer', methods=['POST'],
        csrf=False, save_session=False,
    )
    def close_session(self, session_id, **kw):
        """Close a POS session with optional cash count."""
        try:
            session = request.env['pos.session'].browse(session_id).exists()
            if not session:
                return request.make_json_response(
                    {'status': 'error', 'message': 'Session not found'}, status=404,
                )
            if session.state == 'closed':
                return request.make_json_response(
                    {'status': 'error', 'message': 'Session is already closed'}, status=400,
                )

            session.action_pos_session_closing_control()

            return request.make_json_response({
                'status': 'success',
                'data': self._serialize_session(session),
            })
        except (UserError, ValidationError) as e:
            return request.make_json_response(
                {'status': 'error', 'message': str(e)}, status=400,
            )

    # ------------------------------------------------------------------
    # GET /api/v1/pos/sessions/:id/summary — Session totals
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/pos/sessions/<int:session_id>/summary',
        type='http', auth='bearer', methods=['GET'],
        csrf=False, save_session=False, readonly=True,
    )
    def session_summary(self, session_id, **kw):
        """Get session totals and reconciliation data."""
        session = request.env['pos.session'].browse(session_id).exists()
        if not session:
            return request.make_json_response(
                {'status': 'error', 'message': 'Session not found'}, status=404,
            )
        return request.make_json_response({
            'status': 'success',
            'data': self._serialize_session(session),
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _serialize_session(self, session):
        """Serialize a POS session to a JSON-safe dict."""
        result = {
            'id': session.id,
            'name': session.name,
            'config_id': session.config_id.id,
            'config_name': session.config_id.name,
            'state': session.state,
            'user_id': session.user_id.id,
            'user_name': session.user_id.name,
            'start_at': str(session.start_at or ''),
            'stop_at': str(session.stop_at or ''),
            'order_count': session.order_count,
            'total_payments_amount': session.total_payments_amount,
        }
        return result
