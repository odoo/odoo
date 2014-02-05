# -*- coding: utf-8 -*-

from openerp.addons.web.http import request
from openerp.osv import fields, osv


class actions_server(osv.Model):
    """ Add website option in server actions. """
    _name = 'ir.actions.server'
    _inherit = ['ir.actions.server']

    # _columns = {
    #     'website': fields.boolean('Website Stuff'),
    # }

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
