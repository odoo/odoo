# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api
from . import custom
from . import int_to_text
from . import interface
from . import print_fnc
from . import print_xml
from . import printscreen
from . import render
from . import report_sxw

def render_report(cr, uid, ids, name, data, context=None):
    """
    Helper to call ``ir.actions.report.xml.render_report()``.
    """
    env = api.Environment(cr, uid, context or {})
    return env['ir.actions.report.xml'].render_report(ids, name, data)
