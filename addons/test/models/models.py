# -*- coding: utf-8 -*-

from odoo import models, fields, api

class test(models.Model):
    _name = 'test.test'

    name = fields.Char()
    description = fields.Text()

    source = fields.Selection([('out_invoice', 'Set to Invoice'),('in_invoice','Set to Bill'),('other','Set to Others'),('no','Do Not Change'), ('use_source2', 'Use Source 2')], 'Source', default='other')
    source2 = fields.Selection([('out_invoice', 'Set to Invoice'),('in_invoice','Set to Bill'),('other','Set to Others'),('no','Do Not Change')], 'Source 2', default='other')
    dest = fields.Selection([('out_invoice', 'Invoice'),('in_invoice','Bill'),('other','Others')], 'Destination', compute='_get_dest', store=True, readonly=False, default='in_invoice')
    dest2 = fields.Selection([('out_invoice', 'Invoice'),('in_invoice','Bill'),('other','Others')], 'Destination2', compute='_get_dest', store=True, readonly=False, default='in_invoice')

    @api.depends('source')
    def _get_dest(self):
        val = self.source
        if val == 'use_source2':
            val = self.source2
        if val != 'no':
            self.dest = val
        if self.source2 != 'no':
            self.dest2 = self.source2

