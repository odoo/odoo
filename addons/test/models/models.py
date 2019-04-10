# -*- coding: utf-8 -*-

from odoo import models, fields, api

class test(models.Model):
    _name = 'test.test'
    _inherit = ['mail.thread']

    name = fields.Char()
    source = fields.Selection([('out_invoice', 'Set to Invoice'),('in_invoice','Set to Bill'),('other','Set to Others'),('no','Do Not Change'), ('use_source2', 'Use Source 2')], 'Source', default='other')
    dest = fields.Selection([('out_invoice', 'Invoice'),('in_invoice','Bill'),('other','Others')], 'Destination', compute='_get_dest', store=True, readonly=False)
    user_id = fields.Many2one('res.users', 'User', default=lambda x: x.env.user.id)
    company_id = fields.Many2one('res.company', 'Company', related='user_id.company_id', store=True, tracking=True)
    nbr_currency = fields.Integer('Sum Currency', compute='_get_nbr_currency', store=True, tracking=True)
    line_ids = fields.One2many('test.line', 'test_id')

    @api.depends('line_ids.currency_id')
    def _get_nbr_currency(self):
        print('_get_nbr_currency', self)
        for record in self:
            total = 0
            for line in record.line_ids:
                if line.currency_id:
                    total +=1
            record.nbr_currency = total
        print('_get_nbr_currency end', self)

    @api.depends('source')
    def _get_dest(self):
        for record in self:
            if record.source!='no':
                record.dest = record.source

    def testme(self):
        rec = self.create({
            'name': 'New Test',
        })
        if not rec.company_id:
            should_crash
        return True

class test_line(models.Model):
    _name = 'test.line'

    name = fields.Char()
    test_id = fields.Many2one('test.test')
    company_id = fields.Many2one('res.company', related="test_id.company_id")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')




