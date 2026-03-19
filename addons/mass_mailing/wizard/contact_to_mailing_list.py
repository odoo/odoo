# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, fields, models


class ContactToMailingToList(models.TransientModel):
    _name = 'contact.to.mailing.list'
    _description = "Add Contacts to Mailing List"

    partner_ids = fields.Many2many('res.partner', string='Contacts')
    mailing_list_ids = fields.Many2many('mailing.list', string='Mailing List', required=True)

    def action_add_contacts_to_mailing_lists(self, show_notif=True):
        """Add contacts to the mailing lists and show a confirmation toaster."""
        added_count = self._add_contacts_to_mailing_lists()

        return self._show_notification(added_count) if show_notif else added_count

    def action_add_contacts_and_create_mailing(self):
        """Add contacts to the selected mailing lists, and then create a new mailing with those mailing
        lists set as targets.
        """
        added_count = self.action_add_contacts_to_mailing_lists(show_notif=False)

        res_mailing = self.env['mailing.mailing'].create({
            'subject': _('New...'),
            'mailing_model_id': self.env['ir.model']._get_id('mailing.list'),
            'contact_list_ids': self.mailing_list_ids
        })

        mailing_action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mailing.mailing',
            'res_id': res_mailing.id,
            'views': [(False, 'form')],
        }

        return self._show_notification(added_count, next_action=mailing_action)

    def _add_contacts_to_mailing_lists(self):
        """Add contacts (res_partners) to the selected mailing list(s).

        - If a contact doesn't have a linked mailing.contact, one is created.
        - If a contact has been opt_out, he is skipped.
        - If a contact is being added to a list to which he already belongs, only the
        corresponding subscription gets updated.

        Return the number of contacts that have been added to mailing list(s).
        """
        self.ensure_one()
        partners_with_linked_mailing_contacts = self.env['mailing.contact'].search([
            ('res_partner_id', 'in', self.partner_ids.ids)
        ]).mapped('res_partner_id')
        partners_with_no_linked_mailing_contact = self.partner_ids - partners_with_linked_mailing_contacts
        created_contacts = self._create_contacts_for_partners(partners_with_no_linked_mailing_contact)
        added_contacts_all = set(created_contacts)
        subscriptions = defaultdict(list)
        for contact in self.partner_ids.mapped("mailing_contact_id"):
            if contact.opt_out:
                continue
            for mail_list in self.mailing_list_ids:
                subscription = self.env['mailing.subscription'].search([('contact_id', '=', contact.id), ('list_id', '=', mail_list.id)], limit=1)
                if subscription.exists():
                    continue
                else:
                    subscriptions[mail_list].append(contact)
                    added_contacts_all.add(contact)

        for mail_list in subscriptions:
            mail_list.write({
                'subscription_ids': [
                    (0, 0, {
                        'contact_id': contact.id,
                        'list_id': mail_list.id,
                    })
                    for contact in subscriptions.get(mail_list, [])
                ]
            })

        return len(added_contacts_all)

    def _create_contacts_for_partners(self, partners):
        return self.env['mailing.contact'].create([
            {
                'name': p.name,
                'email': p.email,
                'company_name': p.company_id.name or p.parent_name,
                'country_id': p.country_id.id,
                'opt_out': False,
                'tag_ids': p.category_id.ids,
                'res_partner_id': p.id,
                'list_ids': self.mailing_list_ids.ids,
            }
            for p in partners
        ])

    def _show_notification(self, added_count, next_action=None):
        skipped_count = len(self.partner_ids) - added_count
        confirmation_message = f'{added_count} contacts added to mailing list(s).'
        confirmation_message += f"{skipped_count} skipped (already subscribed or opted-out)" if skipped_count != 0 else ""

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': confirmation_message,
                'type': 'success' if added_count == len(self.partner_ids) else 'info',
                'sticky': False,
                'next': next_action if next_action else {'type': 'ir.actions.act_window_close'},
            }
        }
