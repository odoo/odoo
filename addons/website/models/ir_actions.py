# -*- coding: utf-8 -*-

from openerp.addons.web.http import request
from openerp.osv import fields, osv


class actions_server(osv.Model):
    """ Add website option in server actions. """
    _name = 'ir.actions.server'
    _inherit = ['ir.actions.server']

    _columns = {
        'website_published': fields.boolean(
            'Available on the Website',
            help='A code server action can be executed from the website, using a dedicated'
                 'controller. The address is <base>/website/action/<id_or_xml_id>.'
                 'Set this field as True to allow users to run this action. If it'
                 'set to is False the action cannot be run through the website.'),
    }

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
