# -*- coding: utf-8 -*-
import logging
import time

from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _serve_page(cls):
        response = super(IrHttp, cls)._serve_page()
        if response and getattr(response, 'status_code', 0) == 200 and request.env.user._is_public():
            visitor_sudo = request.env['website.visitor']._get_visitor_from_request()
            # We are avoiding to create a reveal_view if a lead is already
            # created from another module, e.g. website_form
            if not (visitor_sudo and visitor_sudo.lead_ids):
                country_code = 'geoip' in request.session and request.session['geoip'].get('country_code')
                state_code = 'geoip' in request.session and request.session['geoip'].get('region')
                if country_code:
                    try:
                        url = request.httprequest.url
                        ip_address = request.httprequest.remote_addr
                        website_id = request.website.id
                        rules_excluded = (request.httprequest.cookies.get('rule_ids') or '').split(',')
                        before = time.time()
                        new_rules_excluded = request.env['crm.reveal.view'].sudo()._create_reveal_view(website_id, url, ip_address, country_code, state_code, rules_excluded)
                        # even when we match, no view may have been created if this is a duplicate
                        _logger.info('Reveal process time: [%s], match rule: [%s?], country code: [%s], ip: [%s]',
                                     time.time() - before, new_rules_excluded == rules_excluded, country_code,
                                     ip_address)
                        if new_rules_excluded:
                            response.set_cookie('rule_ids', ','.join(new_rules_excluded))
                    except Exception:
                        # just in case - we never want to crash a page view
                        _logger.exception("Failed to process reveal rules")
        return response
