# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

def drop_view_if_exists(cr, viewname):
    cr.execute("DROP view IF EXISTS %s CASCADE" % (viewname,))
    cr.commit()

def escape_psql(to_escape):
    return to_escape.replace('\\', r'\\').replace('%', '\%').replace('_', '\_')
