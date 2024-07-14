# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MarketingTest(models.Model):
    _name = 'marketing.test'
    _description = 'MarketAuto: simple thread-enabled model'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()
    description = fields.Text()
    partner_id = fields.Many2one('res.partner', 'Partner')


class MarketingTestUTM(models.Model):
    _name = 'marketing.test.utm'
    _description = 'MarketAuto: simple thread-enabled model with UTMs'
    _inherit = ['mail.thread', 'utm.mixin']

    name = fields.Char()
    partner_id = fields.Many2one('res.partner', 'Partner')


class MarketingTestBlPhone(models.Model):
    _name = 'marketing.test.sms'
    _description = 'MarketAuto: blacklist + phone-enabled model'
    _inherit = ['mail.thread.blacklist', 'mail.thread.phone']
    _primary_email = 'email_from'
    _order = 'id ASC'

    name = fields.Char()
    email_from = fields.Char(compute='_compute_from_customer', readonly=False, store=True)
    phone = fields.Char(compute='_compute_from_customer', readonly=False, store=True)
    mobile = fields.Char(compute='_compute_from_customer', readonly=False, store=True)
    description = fields.Text()
    customer_id = fields.Many2one('res.partner', 'Partner')
    text_trans = fields.Char(translate=True)

    @api.depends('customer_id')
    def _compute_from_customer(self):
        for record in self:
            if not record.email_from and record.customer_id.email:
                record.email_from = record.customer_id.email
            if not record.phone and record.customer_id.phone:
                record.phone = record.customer_id.phone
            if not record.mobile and record.customer_id.mobile:
                record.mobile = record.customer_id.mobile

    def _mail_get_partner_fields(self, introspect_fields=False):
        """ Override to return the recipient linked to SMS sending. """
        return ['customer_id']
