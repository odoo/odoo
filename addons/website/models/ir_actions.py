# -*- coding: utf-8 -*-

import urlparse

from openerp import api, fields, models
from openerp.http import request


class ActionsServer(models.Model):
    """ Add website option in server actions. """
    _name = 'ir.actions.server'
    _inherit = ['ir.actions.server']

    @api.multi
    def _compute_website_url(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        link = self.website_path or self.xml_id or (self.id and '%d' % self.id) or ''
        if base_url and link:
            path = '%s/%s' % ('/website/action', link)
            return '%s' % urlparse.urljoin(base_url, path)
        return ''

    @api.multi
    def _get_website_url(self):
        for action in self:
            if action.state == 'code' and action.website_published:
                action.website_url = action._compute_website_url()

    xml_id = fields.Char(compute=models.BaseModel.get_xml_id, string="External ID",
        help="ID of the action if defined in a XML file")
    website_path = fields.Char('Website Path')
    website_url = fields.Char(compute='_get_website_url', string='Website URL',
        help='The full URL to access the server action through the website.')
    website_published = fields.Boolean('Available on the Website', copy=False,
        help='A code server action can be executed from the website, using a dedicated'
             'controller. The address is <base>/website/action/<website_path>.'
             'Set this field as True to allow users to run this action. If it'
             'set to is False the action cannot be run through the website.')

    @api.onchange('website_path')
    def on_change_website_path(self):
        self.website_url = self._compute_website_url()

    @api.model
    def _get_eval_context(self, action):
        """ Override to add the request object in eval_context. """
        eval_context = super(ActionsServer, self)._get_eval_context(action)
        if action.state == 'code':
            eval_context['request'] = request
        return eval_context

    @api.model
    def run_action_code_multi(self, action, eval_context=None):
        """ Override to allow returning response the same way action is already
        returned by the basic server action behavior. Note that response has
        priority over action, avoid using both. """
        res = super(ActionsServer, self).run_action_code_multi(action, eval_context)
        if 'response' in eval_context:
            return eval_context['response']
        return res
