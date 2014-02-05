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
            help='A Code server action can be run using a dedicated controller. Set'
                 'this field as True to allow users to run this action. If it is False'
                 'the action cannot be run through the dedicated controller.'),
    }

    def _get_eval_context(self, cr, uid, action, context=None):
        eval_context = super(actions_server, self)._get_eval_context(cr, uid, action, context=context)
        if action.state == 'code':
            eval_context['request'] = request
        return eval_context

    def run_action_code_multi(self, cr, uid, action, eval_context=None, context=None):
        res = super(actions_server, self).run_action_code_multi(cr, uid, action, eval_context, context)
        if 'template' in eval_context:
            return eval_context['template']
        return res
