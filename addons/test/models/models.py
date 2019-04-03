# -*- coding: utf-8 -*-

from odoo import models, fields, api

class test(models.Model):
    _name = 'test.test'

    name = fields.Char()
    source = fields.Selection([('out_invoice', 'Set to Invoice'),('in_invoice','Set to Bill'),('other','Set to Others'),('no','Do Not Change'), ('use_source2', 'Use Source 2')], 'Source', default='other')
    # source2 = fields.Selection([('out_invoice', 'Set to Invoice'),('in_invoice','Set to Bill'),('other','Set to Others'),('no','Do Not Change')], 'Source 2', default='other')
    dest = fields.Selection([('out_invoice', 'Invoice'),('in_invoice','Bill'),('other','Others')], 'Destination', compute='_get_dest', store=True, readonly=False)
    # dest2 = fields.Selection([('out_invoice', 'Invoice'),('in_invoice','Bill'),('other','Others')], 'Destination2', compute='_get_dest', store=True, readonly=False, default='in_invoice')
    line_ids = fields.One2many('test.line', 'test_id', 'Lines')
    user_id = fields.Many2one('res.users', 'User', default=lambda x: x.env.user.id)
    company_id = fields.Many2one('res.company', 'Company', compute='_get_company', store=True)

    @api.depends('user_id')
    def _get_company(self):
        for record in self:
            record.company_id = 1

    @api.depends('source')
    def _get_dest(self):
        for record in self:
            record.dest = record.source

    #         if val == 'use_source2':
    #             val = record.source2
    #         if val != 'no':
    #             record.dest = val
    #         if record.source2 != 'no':
    #             record.dest2 = record.source2

class test(models.Model):
    _name = 'test.line'
    name = fields.Char()
    company_id = fields.Many2one('res.company', 'Company', store=True, compute="_get_company")
    test_id = fields.Many2one('test.test', 'Test', required=True)

    @api.depends('test_id.company_id')
    def _get_company(self):
        for record in self:
            record.company_id = record.test_id.company_id

