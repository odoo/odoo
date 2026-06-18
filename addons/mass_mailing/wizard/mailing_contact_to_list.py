# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class MailingContactToList(models.TransientModel):
    _name = 'mailing.contact.to.list'
    _description = "Add (Mailing) Contacts to Mailing List"

    contact_ids = fields.Many2many('mailing.contact', string='Mailing Contacts')
    partner_ids = fields.Many2many('res.partner', string='Contacts')
    mailing_list_ids = fields.Many2many('mailing.list', string='Mailing Lists', required=True)

    def action_add_contacts(self):
        if self.partner_ids:
            if self.contact_ids:
                raise UserError(self.env._('This action should be used with a single kind of Contacts as input.'))
            return self._action_add_res_partners()

        return self._action_add_mailing_contacts()

    def _action_add_mailing_contacts(self):
        """Add Mailing Contacts to the mailing lists and go to the list(s) view."""
        for mailing_list in self.mailing_list_ids:
            self._add_contacts_to_mailing_list(mailing_list, self.contact_ids)

        action = self.env['ir.actions.actions']._for_xml_id('mass_mailing.action_view_mass_mailing_lists')
        action['target'] = 'current'
        if len(self.mailing_list_ids) == 1:
            action.update({
                'res_id': self.mailing_list_ids.id,
                'views': [[False, 'form']],
            })
        return action

    def _action_add_res_partners(self):
        """Add Partners to the mailing lists and display a per-contact recap notification."""
        contacts = self.env['mailing.contact']
        contacts_added_to_any = set()
        nb_no_details, nb_opt_out = 0, 0
        for mailing_list in self.mailing_list_ids:
            list_contacts, nb_no_details = self.env['mailing.contact'].with_context(
                default_list_ids=mailing_list.ids)._from_partners(self.partner_ids)
            contacts |= list_contacts
            newly_added_ids, list_nb_opt_out = self._add_contacts_to_mailing_list(mailing_list, list_contacts)
            contacts_added_to_any |= newly_added_ids
            nb_opt_out += list_nb_opt_out

        nb_added = len(contacts_added_to_any)
        nb_already_in_all = len(contacts) - nb_added

        message_parts = [self.env._("%(count)s added", count=nb_added)]
        notification_type = 'success' if nb_added else 'info'
        if nb_already_in_all:
            message_parts.append(self.env._("%(count)s already subscribed", count=nb_already_in_all))
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

    @api.model
    def _add_contacts_to_mailing_list(self, mailing_list, contacts):
        mailing_list.invalidate_recordset(["contact_ids"])  # See task-2366811
        contacts_with_subscriptions = contacts.filtered(lambda c: c in mailing_list.contact_ids)
        contacts_opted_out = contacts_with_subscriptions.filtered('opt_out')
        contacts_to_add = contacts - contacts_with_subscriptions
        mailing_list.write({
            'subscription_ids': [
                (0, 0, {
                    'contact_id': contact.id,
                    'list_id': mailing_list.id,
                }) for contact in contacts_to_add
            ]
        })
        return set(contacts_to_add.ids), len(contacts_opted_out)
