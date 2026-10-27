# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailingSubscription(models.Model):
    """ Intermediate model between mass mailing list and mass mailing contact
        Indicates if a contact is opted out for a particular list
    """
    _name = 'mailing.subscription'
    _description = 'Mailing List Subscription'
    _table = 'mailing_subscription'
    _rec_name = 'contact_id'
    _order = 'list_id DESC, contact_id DESC'

    contact_id = fields.Many2one('mailing.contact', string='Contact', ondelete='cascade', required=True)
    list_id = fields.Many2one('mailing.list', string='Mailing List', ondelete='cascade', required=True)
    opt_out = fields.Boolean(
        string='Opt Out',
        default=False,
        help='The contact has chosen not to receive mails anymore from this list')
    opt_out_reason_id = fields.Many2one(
        'mailing.subscription.optout', string='Reason',
        ondelete='restrict')
    opt_out_datetime = fields.Datetime(
        string='Unsubscription Date',
        compute='_compute_opt_out_datetime', readonly=False, store=True)
    message_bounce = fields.Integer(related='contact_id.message_bounce', store=False, readonly=False)
    is_blacklisted = fields.Boolean(related='contact_id.is_blacklisted', store=False, readonly=False)

    _sql_constraints = [
        ('unique_contact_list', 'unique (contact_id, list_id)',
         'A mailing contact cannot subscribe to the same mailing list multiple times.')
    ]

    @api.depends('opt_out')
    def _compute_opt_out_datetime(self):
        self.filtered(lambda sub: not sub.opt_out).opt_out_datetime = False
        for subscription in self.filtered('opt_out'):
            subscription.opt_out_datetime = self.env.cr.now()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('opt_out_datetime') or vals.get('opt_out_reason_id'):
                vals['opt_out'] = True
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('opt_out_datetime') or vals.get('opt_out_reason_id'):
            vals['opt_out'] = True
        return super().write(vals)
