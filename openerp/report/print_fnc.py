# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

functions = {
    'today': lambda x: time.strftime('%d/%m/%Y', time.localtime()).decode('latin1')
}

#
# TODO: call an object internal function too
#
def print_fnc(fnc, arg):
    if fnc in functions:
        return functions[fnc](arg)
    return ''
