# -*- coding: utf-8 -*-

from odoo import models, fields, api

class test(models.Model):
    _name = 'test.test'

    name = fields.Char()
    source = fields.Selection([('out_invoice', 'Set to Invoice'),('in_invoice','Set to Bill'),('other','Set to Others'),('no','Do Not Change'), ('use_source2', 'Use Source 2')], 'Source', default='other')
    dest = fields.Selection([('out_invoice', 'Invoice'),('in_invoice','Bill'),('other','Others')], 'Destination', compute='_get_dest', store=True, readonly=False)
    user_id = fields.Many2one('res.users', 'User', default=lambda x: x.env.user.id)
    company_id = fields.Many2one('res.company', 'Company', compute='_get_company', store=True)

    @api.depends('user_id')
    def _get_company(self):
        for record in self:
            print('Main Set CompanyWrite')
            record.company_id = 1

    @api.depends('source')
    def _get_dest(self):
        for record in self:
            record.dest = record.source

    def testme(self):
        rec = self.new()
        print(rec.create_uid, rec.user_id, rec.company_id)
        return True

