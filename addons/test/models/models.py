# -*- coding: utf-8 -*-

from odoo import models, fields, api

class test(models.Model):
    _name = 'test.test'

    name = fields.Char()
    description = fields.Text()

    source = fields.Selection([('out_invoice', 'Set to Invoice'),('in_invoice','Set to Bill'),('other','Set to Others'),('no','Do Not Change')], 'Source', default='other')
    dest = fields.Selection([('out_invoice', 'Invoice'),('in_invoice','Bill'),('other','Others')], 'Destination', compute='_get_dest', store=True, readonly=False, default='in_invoice')

    @api.depends('source')
    def _get_journal(self):
        if self.source != 'no':
            self.dest = self.source



