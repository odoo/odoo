# -*- coding: utf-8 -*-

import urlparse

from openerp.http import request
from openerp.osv import fields, osv


class actions_server(osv.Model):
    """ Add website option in server actions. """
    _name = 'ir.actions.server'
    _inherit = ['ir.actions.server']

    def _compute_website_url(self, cr, uid, id, website_path, xml_id, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url', context=context)
        link = website_path or xml_id or (id and '%d' % id) or ''
        if base_url and link:
            path = '%s/%s' % ('/website/action', link)
            return '%s' % urlparse.urljoin(base_url, path)
        return ''

    def _get_website_url(self, cr, uid, ids, name, args, context=None):
        res = dict.fromkeys(ids, False)
        for action in self.browse(cr, uid, ids, context=context):
            if action.state == 'code' and action.website_published:
                res[action.id] = self._compute_website_url(cr, uid, action.id, action.website_path, action.xml_id, context=context)
        return res

    _columns = {
        'xml_id': fields.function(
            osv.osv.get_xml_id, type='char', string="External ID",
            help="ID of the action if defined in a XML file"),
        'website_path': fields.char('Website Path'),
        'website_url': fields.function(
            _get_website_url, type='char', string='Website URL',
            help='The full URL to access the server action through the website.'),
        'website_published': fields.boolean(
            'Available on the Website', copy=False,
            help='A code server action can be executed from the website, using a dedicated'
                 'controller. The address is <base>/website/action/<website_path>.'
                 'Set this field as True to allow users to run this action. If it'
                 'set to is False the action cannot be run through the website.'),
    }

    def on_change_website_path(self, cr, uid, ids, website_path, xml_id, context=None):
        values = {
            'website_url': self._compute_website_url(cr, uid, ids[0], website_path, xml_id, context=context)
        }
        return {'value': values}

    def _get_eval_context(self, cr, uid, action, context=None):
        """ Override to add the request object in eval_context. """
        eval_context = super(actions_server, self)._get_eval_context(cr, uid, action, context=context)
        if action.state == 'code':
            eval_context['request'] = request
        return eval_context

    def run_action_code_multi(self, cr, uid, action, eval_context=None, context=None):
        """ Override to allow returning response the same way action is already
        returned by the basic server action behavior. Note that response has
        priority over action, avoid using both. """
        res = super(actions_server, self).run_action_code_multi(cr, uid, action, eval_context, context)
        if 'response' in eval_context:
            return eval_context['response']
        return res
