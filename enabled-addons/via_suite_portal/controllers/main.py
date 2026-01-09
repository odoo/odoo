# -*- coding: utf-8 -*-
import json
import logging
import os
import werkzeug.urls
from odoo import http, api
from odoo.http import request
from odoo.addons.via_suite_base.controllers.main import ViaSuiteOAuthController

_logger = logging.getLogger(__name__)

class ViaSuitePortalDispatcher(ViaSuiteOAuthController):
    """
    Central Dispatcher for ViaSuite.
    
    This controller is active ONLY on the global domain and is responsible
    for redirecting users to their specific subdomains based on the 
    'tenant' claim in their Keycloak token.
    """

    @http.route('/auth_oauth/signin', type='http', auth='none', readonly=False)
    def signin(self, **kw):
        """
        Global Dispatcher Logic:
        If on root domain and tenant claim present -> Redirect to subdomain.
        Else -> Proceed with local login (Admin/Support).
        """
        # 1. Detect if we are on the Global Domain
        global_domain = os.getenv('VIA_SUITE_GLOBAL_DOMAIN', 'viafronteira.app')
        current_host = request.httprequest.host.split(':')[0]
        
        is_global_domain = current_host == global_domain
        
        if is_global_domain and kw.get('state'):
            try:
                # We need to peek into the token to find the tenant BEFORE local auth
                state = json.loads(kw.get('state'))
                provider_id = state.get('p')
                dbname = state.get('d')
                access_token = kw.get('access_token')
                
                if provider_id and access_token and dbname:
                    # In Odoo 19, ensure_db is critical for request.env to work
                    from odoo.addons.web.controllers.utils import ensure_db
                    ensure_db(db=dbname)
                    
                    # Use sudo to call validation since auth='none'
                    Users = request.env['res.users'].sudo()
                    validation = Users._auth_oauth_validate(provider_id, access_token)
                    tenant_code = validation.get('tenant')
                    
                    if tenant_code:
                        # Find the tenant record to check if it's active
                        tenant_record = request.env['via_suite.tenant'].sudo().search([
                            ('subdomain', '=', tenant_code)
                        ], limit=1)
                        
                        if tenant_record and not tenant_record.active:
                            _logger.warning("Global Dispatcher: Blocked access to inactive tenant '%s'", tenant_code)
                            # Redirect to a branded error page with a specific code
                            return request.redirect('/web/login?via_error=tenant_inactive', local=True)

                        # DISPATCH: Redirect to the tenant subdomain
                        tenant_url = f"https://{tenant_code}.{global_domain}/auth_oauth/signin"
                        _logger.info("Global Dispatcher: Redirecting user to tenant '%s' at %s", tenant_code, tenant_url)
                        
                        fragment = werkzeug.urls.url_encode(kw)
                        return request.redirect(f"{tenant_url}#{fragment}", local=False, keep_hash=True)
                        
            except Exception as e:
                _logger.error("Global Dispatcher failed to redirect: %s", str(e))
                # Fallback to standard signin logic below
        
        # 2. Fallback to standard ViaSuite login (handles Admins or local auth)
        return super(ViaSuitePortalDispatcher, self).signin(**kw)
