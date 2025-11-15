from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class IntegrationOAuthController(http.Controller):
    
    @http.route('/onedesk/integration/oauth/callback', type='http', auth='user', website=True)
    def oauth_callback(self, **kwargs):
        """Callback OAuth"""
        code = kwargs.get('code')
        state = kwargs.get('state')
        error = kwargs.get('error')
        
        if error:
            _logger.error(f"❌ OAuth error: {error}")
            return request.render('onedesk_core.oauth_error', {
                'error': error,
                'error_description': kwargs.get('error_description', 'Erreur inconnue'),
            })
        
        if not code or not state:
            return request.render('onedesk_core.oauth_error', {
                'error': 'invalid_request',
                'error_description': 'Code ou state manquant',
            })
        
        try:
            # Trouve l'intégration
            integration = request.env['onedesk.integration'].sudo().search([
                ('oauth_state', '=', state),
                ('state', '=', 'connecting'),
            ], limit=1)
            
            if not integration:
                return request.render('onedesk_core.oauth_error', {
                    'error': 'invalid_state',
                    'error_description': 'État OAuth invalide ou expiré',
                })
            
            # Traite le callback
            integration.handle_oauth_callback(code, state)
            
            return request.render('onedesk_core.oauth_success', {
                'integration': integration,
            })
            
        except Exception as e:
            _logger.error(f"❌ Callback error: {e}", exc_info=True)
            return request.render('onedesk_core.oauth_error', {
                'error': 'processing_error',
                'error_description': str(e),
            })

