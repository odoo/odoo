# -*- coding: utf-8 -*-
import openerp
from openerp.osv import fields
from openerp.osv.orm import Model

class test_uninstall_model(Model):
    _name = 'test_uninstall.model'

    _columns = {
        'name': fields.char('Name', size=64),
        'ref': fields.many2one('res.users', string='User'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Each name must be unique.')
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
