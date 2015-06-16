# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import tools

def rounding(f, r):
	# TODO for trunk: log deprecation warning
	# _logger.warning("Deprecated rounding method, please use tools.float_round to round floats.")
	return tools.float_round(f, precision_rounding=r)

# TODO for trunk: add rounding method parameter to tools.float_round and use this method as hook
def ceiling(f, r):
    if not r:
        return f
    return tools.float_round(f, precision_rounding=r, rounding_method='UP')
