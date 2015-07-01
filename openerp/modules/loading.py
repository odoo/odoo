# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules (also called addons) management.

"""
import openerp

def _check_module_names(cr, module_names):
    return openerp.registry(cr.dbname)._check_module_names(cr, module_names)

def load_marked_modules(cr, graph, states, force, progressdict, report, loaded_modules, perform_checks):
    return openerp.registry(cr.dbname).load_marked_modules(
        cr, states, force=force, loaded_modules=loaded_modules,
        perform_checks=perform_checks)

def load_module_graph(cr, graph, status=None, perform_checks=True, skip_modules=None, report=None):
    return openerp.registry(cr.dbname).load_module_graph(
        cr, perform_checks=perform_checks, skip_modules=skip_modules)

def load_modules(db, force_demo=False, status=None, update_module=False):
    openerp.registry(db).load_modules(force_demo=force_demo, update_module=update_module)
