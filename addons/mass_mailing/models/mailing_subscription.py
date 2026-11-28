# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from odoo import _, api, fields, models


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
    list_id = fields.Many2one('mailing.list', string='Mailing List', ondelete='cascade', required=True, index=True)
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

    _unique_contact_list = models.Constraint(
        'unique (contact_id, list_id)',
        'A mailing contact cannot subscribe to the same mailing list multiple times.',
    )

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
        subscriptions = super().create(vals_list)
        subscription_changes = [
            (subscription.contact_id, subscription.list_id)
            for subscription in subscriptions if not subscription.opt_out
        ]
        self._log_subscription_changes(subscription_changes, subscribed=True)
        return subscriptions

    def write(self, vals):
        if vals.get('opt_out_datetime') or vals.get('opt_out_reason_id'):
            vals['opt_out'] = True

        if not {'contact_id', 'list_id', 'opt_out'} & vals.keys():
            return super().write(vals)

        subscription_values = [
            (subscription.contact_id, subscription.list_id, subscription.opt_out)
            for subscription in self
        ]
        result = super().write(vals)

        new_subscription_changes = []
        new_unsubscription_changes = []

        for subscription, (old_contact, old_list, old_opt_out) in zip(self, subscription_values):
            relation_changed = old_contact != subscription.contact_id or old_list != subscription.list_id
            # When the subscription was active and (1) the relation changed or (2) the subscription is now inactive
            if not old_opt_out and (relation_changed or subscription.opt_out):
                new_unsubscription_changes.append((old_contact, old_list))
            # When the subscription is now active and (1) the relation changed or (2) the subscription was inactive
            if not subscription.opt_out and (relation_changed or old_opt_out):
                new_subscription_changes.append((subscription.contact_id, subscription.list_id))

        self._log_subscription_changes(new_unsubscription_changes, subscribed=False)
        self._log_subscription_changes(new_subscription_changes, subscribed=True)

        return result

    def unlink(self):
        self._log_subscription_changes(
            [(sub.contact_id, sub.list_id) for sub in self if not sub.opt_out],
            subscribed=False,
        )
        return super().unlink()

    def _log_subscription_changes(self, changes, subscribed):
        if not changes or self.env.context.get('tracking_disable'):
            return
        lists_per_contact = {}
        for contact, mailing_list in changes:
            lists_per_contact.setdefault(contact, []).append(mailing_list.name)

        bodies = {}
        for contact, list_names in lists_per_contact.items():
            title = _(
                '%(contact_name)s subscribed to the following mailing list(s)',
                contact_name=contact.display_name,
            ) if subscribed else _(
                '%(contact_name)s unsubscribed from the following mailing list(s)',
                contact_name=contact.display_name,
            )
            bodies[contact.id] = Markup('<p>%s</p><ul>%s</ul>') % (
                title,
                Markup().join(Markup('<li>%s</li>') % name for name in list_names),
            )

        contacts = self.env['mailing.contact'].browse(list(bodies))
        contacts._message_log_batch(bodies=bodies)

    def open_mailing_contact(self):
        action = {
            'name': _('Mailing Contacts'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.contact_id.ids)],
            'res_model': 'mailing.contact',
        }
        if len(self) == 1:
            action.update({
                'name': _('Mailing Contact'),
                'view_mode': 'form',
                'res_id': self.contact_id.id,
            })
        return action
