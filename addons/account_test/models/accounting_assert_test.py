# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

CODE_EXEC_DEFAULT = '''\
res = []
cr.execute("select id, code from account_journal")
for record in cr.dictfetchall():
    res.append(record['code'])
result = res
'''


class AccountingAssertTest(models.Model):
    _name = 'accounting.assert.test'
    _description = 'Accounting Assert Test'
    _order = "sequence"

    name = fields.Char(string='Test Name', required=True, translate=True)
    desc = fields.Text(string='Test Description', translate=True)
    code_exec = fields.Text(string='Python code', required=True, default=CODE_EXEC_DEFAULT)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
