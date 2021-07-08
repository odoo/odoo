# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


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
    user_id = fields.Many2one('res.users', 'Responsible', track_visibility='onchange')

    @api.model_create_multi
    def create(self, vals_list):
        # Emulate an addon that alters the creation context, such as `crm`
        if not self._context.get('default_type'):
            self = self.with_context(default_type='first')
        return super(MailTestFieldType, self).create(vals_list)
