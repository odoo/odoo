# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

from odoo import api, fields, models, _


class BuilderJsOptions(models.Model):
    _name = 'formio.builder.js.options'
    _description = 'Formio Builder JavaScript Options'
    _order = 'name ASC'

    name = fields.Char(string="Name", required=True)
    value = fields.Text(string="Value (JSON)")
