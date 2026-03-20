# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrExports(models.Model):
    _name = 'ir.exports'
    _description = 'Exports'
    _order = 'name, id'

    name = fields.Char(string='Export Name')
    resource = fields.Char(index=True)
    export_fields = fields.One2many('ir.exports.line', 'export_id', string='Export ID', copy=True)


class IrExportsLine(models.Model):
    _name = 'ir.exports.line'
    _description = 'Exports Line'
    _order = 'id'

    name = fields.Char(string='Field Name')
    export_id = fields.Many2one('ir.exports', string='Export', index=True, ondelete='cascade')
