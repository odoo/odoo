# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.addons.web.http import request
from openerp.tools.misc import unquote as unquote


class ir_rule(osv.osv):
    _inherit = 'ir.rule'

    def _eval_context_for_combinations(self):
        """Returns a dictionary to use as evaluation context for
           ir.rule domains, when the goal is to obtain python lists
           that are easier to parse and combine, but not to
           actually execute them."""
        res = super(ir_rule, self)._eval_context_for_combinations()
        res.update(session=unquote('session'))
        return res

    def _eval_context(self, cr, uid):
        """Returns a dictionary to use as evaluation context for
           ir.rule domains."""
        res = super(ir_rule, self)._eval_context(cr, uid)
        res.update(session=request and request.httprequest and request.httprequest.session)
        return res
