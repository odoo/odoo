# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailTestRating(models.Model):
    """ A model inheriting from mail.thread with some fields used for SMS
    gateway, like a partner, a specific mobile phone, ... """
    _description = 'Rating Model (ticket-like)'
    _name = 'mail.test.rating'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'rating.mixin',
        'portal.mixin',
    ]
    _mailing_enabled = True
    _order = 'name asc, id asc'

    name = fields.Char()
    subject = fields.Char()
    company_id = fields.Many2one('res.company', 'Company')
    customer_id = fields.Many2one('res.partner', 'Customer')
    email_from = fields.Char(compute='_compute_email_from', precompute=True, readonly=False, store=True)
    mobile_nbr = fields.Char(compute='_compute_mobile_nbr', precompute=True, readonly=False, store=True)
    phone_nbr = fields.Char(compute='_compute_phone_nbr', precompute=True, readonly=False, store=True)
    user_id = fields.Many2one('res.users', 'Responsible', tracking=1)

    @api.depends('customer_id')
    def _compute_email_from(self):
        for rating in self:
            if rating.customer_id.email_normalized:
                rating.email_from = rating.customer_id.email_normalized
            elif not rating.email_from:
                rating.email_from = False

    @api.depends('customer_id')
    def _compute_mobile_nbr(self):
        for rating in self:
            if rating.customer_id.mobile:
                rating.mobile_nbr = rating.customer_id.mobile
            elif not rating.mobile_nbr:
                rating.mobile_nbr = False

    @api.depends('customer_id')
    def _compute_phone_nbr(self):
        for rating in self:
            if rating.customer_id.phone:
                rating.phone_nbr = rating.customer_id.phone
            elif not rating.phone_nbr:
                rating.phone_nbr = False

    def rating_get_partner_id(self):
        return self.customer_id
