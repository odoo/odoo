# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api



class PackBenchConfiguration(models.Model):
    _name = 'pack.bench.configuration'
    _description = 'Pack Bench Configuration.'
    _inherit = 'mail.thread'

    name = fields.Char(string='Bench', tracking=True)
    pack_bench_id = fields.Integer(string='Pack Bench ID', tracking=True)
    printer_ip = fields.Char(string='Printer IP', tracking=True)
    printer_name = fields.Char(string='Printer Name', tracking=True)
    tenant_code_id = fields.Many2one(
        'tenant.code.configuration',
        string='Tenant Code',
        store=True
    )
    site_code_id = fields.Many2one('site.code.configuration', string='Site Code', store=True)

