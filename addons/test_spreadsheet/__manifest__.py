# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Spreadsheet Test',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Spreadsheet Test, mainly to test the mixin behavior',
    'description': """This module contains tests related to spreadsheet.
    The modules exposes some mixin that are only implemented in other functional modules.
    When trying to test a global behavior of the mixin, it makes no sense to test it in
    each module implementing the mixin but rather test a dummy implementation of the later,
    hence the need for this test module.
    """,
    'depends': ['spreadsheet'],
    'license': 'LGPL-3',
    'data': ['security/ir.model.access.csv'],
}
