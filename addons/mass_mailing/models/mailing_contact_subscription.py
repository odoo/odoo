# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MassMailingContactListRel(models.Model):
    """ Intermediate model between mass mailing list and mass mailing contact
        Indicates if a contact is opted out for a particular list
    """
    _name = 'mailing.contact.subscription'
    _description = 'Mass Mailing Subscription Information'
    _table = 'mailing_contact_list_rel'
    _rec_name = 'contact_id'
    _order = 'list_id DESC, contact_id DESC'

    contact_id = fields.Many2one('mailing.contact', string='Contact', ondelete='cascade', required=True)
    list_id = fields.Many2one('mailing.list', string='Mailing List', ondelete='cascade', required=True)
    opt_out = fields.Boolean(
        string='Opt Out',
        default=False,
        help='The contact has chosen not to receive mails anymore from this list')
    unsubscription_date = fields.Datetime(string='Unsubscription Date')
    message_bounce = fields.Integer(related='contact_id.message_bounce', store=False, readonly=False)
    is_blacklisted = fields.Boolean(related='contact_id.is_blacklisted', store=False, readonly=False)

    _sql_constraints = [
        ('unique_contact_list', 'unique (contact_id, list_id)',
         'A mailing contact cannot subscribe to the same mailing list multiple times.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            if 'opt_out' in vals and 'unsubscription_date' not in vals:
                vals['unsubscription_date'] = now if vals['opt_out'] else False
            if vals.get('unsubscription_date'):
                vals['opt_out'] = True
        return super().create(vals_list)

    def write(self, vals):
        if 'opt_out' in vals and 'unsubscription_date' not in vals:
            vals['unsubscription_date'] = fields.Datetime.now() if vals['opt_out'] else False
        if vals.get('unsubscription_date'):
            vals['opt_out'] = True
        return super(MassMailingContactListRel, self).write(vals)
