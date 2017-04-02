# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import urlparse

from odoo import api, fields, models
from odoo.http import request


class ServerAction(models.Model):
    """ Add website option in server actions. """

    _name = 'ir.actions.server'
    _inherit = 'ir.actions.server'

    xml_id = fields.Char('External ID', compute='_compute_xml_id', help="ID of the action if defined in a XML file")
    website_path = fields.Char('Website Path')
    website_url = fields.Char('Website Url', compute='_get_website_url', help='The full URL to access the server action through the website.')
    website_published = fields.Boolean('Available on the Website', copy=False,
                                       help='A code server action can be executed from the website, using a dedicated '
                                            'controller. The address is <base>/website/action/<website_path>. '
                                            'Set this field as True to allow users to run this action. If it '
                                            'is set to False the action cannot be run through the website.')

    def _compute_xml_id(self):
        res = self.get_external_id()
        for action in self:
            action.xml_id = res.get(action.id)

    def _compute_website_url(self, website_path, xml_id):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        link = website_path or xml_id or (self.id and '%d' % self.id) or ''
        if base_url and link:
            path = '%s/%s' % ('/website/action', link)
            return '%s' % urlparse.urljoin(base_url, path)
        return ''

    @api.depends('state', 'website_published', 'website_path', 'xml_id')
    def _get_website_url(self):
        for action in self:
            if action.state == 'code' and action.website_published:
                action.website_url = self._compute_website_url(action.website_path, action.xml_id)

    @api.model
    def _get_eval_context(self, action):
        """ Override to add the request object in eval_context. """
        eval_context = super(ServerAction, self)._get_eval_context(action)
        if action.state == 'code':
            eval_context['request'] = request
        return eval_context

    @api.model
    def run_action_code_multi(self, action, eval_context=None):
        """ Override to allow returning response the same way action is already
            returned by the basic server action behavior. Note that response has
            priority over action, avoid using both.
        """
        res = super(ServerAction, self).run_action_code_multi(action, eval_context)
        return eval_context.get('response', res)
