# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class PackageConfiguration(models.Model):
    _name = 'package.box.configuration'
    _description = 'Pack Bench Configuration.'
    _inherit = 'mail.thread'

    name = fields.Char(string='Package Name', tracking=True, required=True)
    box_barcode =fields.Char(string='Box Barcode')
    length = fields.Float('Length', tracking=True)
    width = fields.Float('Width', tracking=True)
    height = fields.Float('Height', tracking=True)
    tenant_code_id = fields.Many2one(
        'tenant.code.configuration',
        string='Tenant Code',
        store=True
    )
    site_code_id = fields.Many2one('site.code.configuration', string='Site Code', store=True)
