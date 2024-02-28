# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailTestPortal(models.Model):
    """ A model intheriting from mail.thread with some fields used for portal
    sharing, like a partner, ..."""
    _description = 'Chatter Model for Portal'
    _name = 'mail.test.portal'
    _inherit = [
        'mail.thread',
        'portal.mixin',
    ]

    name = fields.Char()
    partner_id = fields.Many2one('res.partner', 'Customer')

    def _compute_access_url(self):
        self.access_url = False
        for record in self.filtered('id'):
            record.access_url = '/my/test_portal/%s' % self.id


class MailTestPortalNoPartner(models.Model):
    """ A model inheriting from portal, but without any partner field """
    _description = 'Chatter Model for Portal (no partner field)'
    _name = 'mail.test.portal.no.partner'
    _inherit = [
        'mail.thread',
        'portal.mixin',
    ]

    name = fields.Char()

    def _compute_access_url(self):
        self.access_url = False
        for record in self.filtered('id'):
            record.access_url = '/my/test_portal_no_partner/%s' % self.id


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

    def _mail_get_partner_fields(self):
        return ['customer_id']

    def _rating_apply_get_default_subtype_id(self):
        return self.env['ir.model.data']._xmlid_to_res_id("test_mail_full.mt_mail_test_rating_rating_done")

    def _rating_get_partner(self):
        return self.customer_id
