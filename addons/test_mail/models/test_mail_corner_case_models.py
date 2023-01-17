# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailPerformanceThread(models.Model):
    _name = 'mail.performance.thread'
    _description = 'Performance: mail.thread'
    _inherit = ['mail.thread']

    name = fields.Char()
    value = fields.Integer()
    value_pc = fields.Float(compute="_value_pc", store=True)
    track = fields.Char(default='test', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer')

    @api.depends('value')
    def _value_pc(self):
        for record in self:
            record.value_pc = float(record.value) / 100


class MailPerformanceTracking(models.Model):
    _name = 'mail.performance.tracking'
    _description = 'Performance: multi tracking'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    field_0 = fields.Char(tracking=True)
    field_1 = fields.Char(tracking=True)
    field_2 = fields.Char(tracking=True)


class MailTestFieldType(models.Model):
    """ Test default values, notably type, messing through models during gateway
    processing (i.e. lead.type versus attachment.type). """
    _description = 'Test Field Type'
    _name = 'mail.test.field.type'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()
    datetime = fields.Datetime(default=fields.Datetime.now)
    customer_id = fields.Many2one('res.partner', 'Customer')
    type = fields.Selection([('first', 'First'), ('second', 'Second')])
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        # Emulate an addon that alters the creation context, such as `crm`
        if not self._context.get('default_type'):
            self = self.with_context(default_type='first')
        return super(MailTestFieldType, self).create(vals_list)


class MailTestTrackCompute(models.Model):
    _name = 'mail.test.track.compute'
    _description = "Test tracking with computed fields"
    _inherit = ['mail.thread']

    partner_id = fields.Many2one('res.partner', tracking=True)
    partner_name = fields.Char(related='partner_id.name', store=True, tracking=True)
    partner_email = fields.Char(related='partner_id.email', store=True, tracking=True)
    partner_phone = fields.Char(related='partner_id.phone', tracking=True)


class MailTestMultiCompany(models.Model):
    """ This model can be used in multi company tests"""
    _name = 'mail.test.multi.company'
    _description = "Test Multi Company Mail"
    _inherit = 'mail.thread'

    name = fields.Char()
    company_id = fields.Many2one('res.company')


class MailTestSelectionTracking(models.Model):
    """ Test tracking for selection fields """
    _description = 'Test Selection Tracking'
    _name = 'mail.test.track.selection'
    _inherit = ['mail.thread']

    name = fields.Char()
    type = fields.Selection([('first', 'First'), ('second', 'Second')], tracking=True)
