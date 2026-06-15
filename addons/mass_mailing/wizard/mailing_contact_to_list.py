# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import UserError


class MailingContactToList(models.TransientModel):
    _name = 'mailing.contact.to.list'
    _description = "Add (Mailing) Contacts to Mailing List"

    contact_ids = fields.Many2many('mailing.contact', string='Mailing Contacts')
    partner_ids = fields.Many2many('res.partner', string='Contacts')
    mailing_list_id = fields.Many2one('mailing.list', string='Mailing List', required=True)

    def action_add_contacts(self):
        if self.partner_ids:
            if self.contact_ids:
                raise UserError(self.env._('This action should be used with a single kind of Contacts as input.'))
            return self._action_add_res_partners()

        return self._action_add_mailing_contacts()

    def _action_add_mailing_contacts(self):
        """Add Mailing Contacts to the mailing list and go to the list."""
        self._add_contacts_to_mailing_list()

        action = self.env['ir.actions.actions']._for_xml_id('mass_mailing.action_view_mass_mailing_lists')
        action.update({
            'res_id': self.mailing_list_id.id,
            'target': 'current',
            'views': [[False, 'form']],
        })
        return action

    def _action_add_res_partners(self):
        """Add Partners to the mailing list and display recap notification."""
        context = {"default_list_ids": self.mailing_list_id.ids}
        contacts, nb_no_details = self.env['mailing.contact'].with_context(context)._from_partners(self.partner_ids)
        nb_added, nb_opt_out = self._add_contacts_to_mailing_list()
        message_parts = [self.env._("%(count)s added", count=nb_added)]
        notification_type = 'success' if nb_added else 'info'
        if nb_ignored := (len(contacts) - nb_no_details - nb_added):
            if n_subscribed := nb_ignored - nb_opt_out:
                message_parts.append(self.env._("%(count)s already subscribed", count=n_subscribed))
            if nb_opt_out:
                message_parts.append(self.env._("%(count)s opted out", count=nb_opt_out))
        if nb_no_details:
            message_parts.append(self._get_no_contact_details_message(nb_no_details))
        action = {
            'domain': [('id', 'in', contacts.ids)],
            'name': self.env._("Added to Mailing Lists"),
            'res_model': 'mailing.contact',
            'type': 'ir.actions.act_window',
            'views': [[False, 'list'], [False, 'kanban'], [False, 'form']],
        }
        return {
            'type': 'ir.actions.client',
            'tag': 'res_partner_to_list_results',
            'params': {
                'next': {'type': 'ir.actions.act_window_close'},
                'notification': {
                    'button': {'action': action, 'name': self.env._("View")},
                    'message': '%(NOTIF_NEWLINE)s'.join(message_parts),
                    'type': notification_type,
                },
            },
        }

    def _get_no_contact_details_message(self, count):
        return self.env._("%(count)s ignored (no email)", count=count)

    def _add_contacts_to_mailing_list(self):
        self.ensure_one()
        contacts_with_subscriptions = self.contact_ids.filtered(lambda c: c in self.mailing_list_id.contact_ids)
        contacts_opted_out = contacts_with_subscriptions.filtered('opt_out')
        contacts_to_add = self.contact_ids - contacts_with_subscriptions
        self.mailing_list_id.write({
            'subscription_ids': [
                (0, 0, {
                    'contact_id': contact.id,
                    'list_id': self.mailing_list_id.id,
                }) for contact in contacts_to_add
            ]
        })
        return len(contacts_to_add), len(contacts_opted_out)
