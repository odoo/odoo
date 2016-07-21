# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp import api
import interface
import print_xml
import print_fnc
import custom
import render
import int_to_text

import report_sxw

import printscreen

def render_report(cr, uid, ids, name, data, context=None):
    """
    Helper to call ``ir.actions.report.xml.render_report()``.
    """
    env = api.Environment(cr, uid, context or {})
    return env['ir.actions.report.xml'].render_report(ids, name, data)
