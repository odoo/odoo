# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import werkzeug

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class WebsiteRoute(models.Model):
    _rec_name = 'path'
    _name = 'website.route'
    _description = "All Website Route"
    _order = 'path'

    path = fields.Char('Route')

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        query = super()._name_search(name, domain, operator, limit, order)
        if not query:
            self._refresh()
            return super()._name_search(name, domain, operator, limit, order)
        return query

    def _refresh(self):
        _logger.debug("Refreshing website.route")
        ir_http = self.env['ir.http']
        tocreate = []
        paths = {rec.path: rec for rec in self.search([])}
        for url, endpoint in ir_http._generate_routing_rules(self.pool._init_modules, converters=ir_http._get_converters()):
            if 'GET' in (endpoint.routing.get('methods') or ['GET']):
                if paths.get(url):
                    paths.pop(url)
                else:
                    tocreate.append({'path': url})

        if tocreate:
            _logger.info("Add %d website.route" % len(tocreate))
            self.create(tocreate)

        if paths:
            find = self.search([('path', 'in', list(paths.keys()))])
            _logger.info("Delete %d website.route" % len(find))
            find.unlink()


class WebsiteRewrite(models.Model):
    _name = 'website.rewrite'
    _description = "Website rewrite"

    name = fields.Char('Name', required=True)
    website_id = fields.Many2one('website', string="Website", ondelete='cascade', index=True)
    active = fields.Boolean(default=True)
    url_from = fields.Char('URL from', index=True)
    route_id = fields.Many2one('website.route')
    url_to = fields.Char("URL to")
    redirect_type = fields.Selection([
        ('404', '404 Not Found'),
        ('301', '301 Moved permanently'),
        ('302', '302 Moved temporarily'),
        ('308', '308 Redirect / Rewrite'),
    ], string='Action', default="302",
        help='''Type of redirect/Rewrite:\n
        301 Moved permanently: The browser will keep in cache the new url.
        302 Moved temporarily: The browser will not keep in cache the new url and ask again the next time the new url.
        404 Not Found: If you want remove a specific page/controller (e.g. Ecommerce is installed, but you don't want /shop on a specific website)
        308 Redirect / Rewrite: If you want rename a controller with a new url. (Eg: /shop -> /garden - Both url will be accessible but /shop will automatically be redirected to /garden)
    ''')

    sequence = fields.Integer()

    @api.onchange('route_id')
    def _onchange_route_id(self):
        self.url_from = self.route_id.path
        self.url_to = self.route_id.path

    @api.constrains('url_to', 'url_from', 'redirect_type')
    def _check_url_to(self):
        for rewrite in self:
            if rewrite.redirect_type in ['301', '302', '308']:
                if not rewrite.url_to:
                    raise ValidationError(_('"URL to" can not be empty.'))
                if not rewrite.url_from:
                    raise ValidationError(_('"URL from" can not be empty.'))

            if rewrite.redirect_type == '308':
                if not rewrite.url_to.startswith('/'):
                    raise ValidationError(_('"URL to" must start with a leading slash.'))
                for param in re.findall('/<.*?>', rewrite.url_from):
                    if param not in rewrite.url_to:
                        raise ValidationError(_('"URL to" must contain parameter %s used in "URL from".', param))
                for param in re.findall('/<.*?>', rewrite.url_to):
                    if param not in rewrite.url_from:
                        raise ValidationError(_('"URL to" cannot contain parameter %s which is not used in "URL from".', param))

                if rewrite.url_to == '/':
                    raise ValidationError(_('"URL to" cannot be set to "/". To change the homepage content, use the "Homepage URL" field in the website settings or the page properties on any custom page.'))

                if any(
                    rule for rule in self.env['ir.http'].routing_map().iter_rules()
                    # Odoo routes are normally always defined without trailing
                    # slashes + strict_slashes=False, but there are exceptions.
                    if rule.rule.rstrip('/') == rewrite.url_to.rstrip('/')
                ):
                    raise ValidationError(_('"URL to" cannot be set to an existing page.'))

                try:
                    converters = self.env['ir.http']._get_converters()
                    routing_map = werkzeug.routing.Map(strict_slashes=False, converters=converters)
                    rule = werkzeug.routing.Rule(rewrite.url_to)
                    routing_map.add(rule)
                except ValueError as e:
                    raise ValidationError(_('"URL to" is invalid: %s', e)) from e

    @api.depends('redirect_type')
    def _compute_display_name(self):
        for rewrite in self:
            rewrite.display_name = f"{rewrite.redirect_type} - {rewrite.name}"

    @api.model_create_multi
    def create(self, vals_list):
        rewrites = super().create(vals_list)
        if set(rewrites.mapped('redirect_type')) & {'308', '404'}:
            self._invalidate_routing()
        return rewrites

    def write(self, vals):
        need_invalidate = set(self.mapped('redirect_type')) & {'308', '404'}
        res = super(WebsiteRewrite, self).write(vals)
        need_invalidate |= set(self.mapped('redirect_type')) & {'308', '404'}
        if need_invalidate:
            self._invalidate_routing()
        return res

    def unlink(self):
        need_invalidate = set(self.mapped('redirect_type')) & {'308', '404'}
        res = super(WebsiteRewrite, self).unlink()
        if need_invalidate:
            self._invalidate_routing()
        return res

    def _invalidate_routing(self):
        # Call clear_cache for routing on all workers to reload routing table.
        # Note that only 404 and 308 redirection alter the routing map:
        # - 404: remove entry from routing map
        # - 301/302: served as fallback later if path not found in routing map
        # - 308: add "alias" (`redirect_to`) in routing map
        self.env.registry.clear_cache('routing')

    def refresh_routes(self):
        self.env['website.route']._refresh()
