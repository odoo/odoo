# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, Command, _
from odoo.tools.misc import clean_context


class MailingContactImport(models.TransientModel):
    _name = 'mailing.contact.import'
    _description = 'Mailing Contact Import'

    mailing_list_ids = fields.Many2many('mailing.list', string='Lists')
    contact_list = fields.Text('Contact List', help='Contact list that will be imported, one contact per line')

    def action_import(self):
        """Import each lines of "contact_list" as a new contact."""
        self.ensure_one()
        contacts = tools.mail.email_split_tuples(', '.join((self.contact_list or '').splitlines()))
        if not contacts:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No valid email address found.'),
                    'next': {'type': 'ir.actions.act_window_close'},
                    'sticky': False,
                    'type': 'warning',
                }
            }

        if len(contacts) > 5000:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('You have to much emails, please upload a file.'),
                    'type': 'warning',
                    'sticky': False,
                    'next': self.action_open_base_import(),
                }
            }

        all_emails = list({values[1].lower() for values in contacts})

        existing_contacts = self.env['mailing.contact'].search([
            ('email_normalized', 'in', all_emails),
            ('list_ids', 'in', self.mailing_list_ids.ids),
        ])
        existing_contacts = {
            contact.email_normalized: contact
            for contact in existing_contacts
        }

        # Remove duplicated record, keep only the first non-empty name for each email address
        unique_contacts = {}
        for name, email in contacts:
            email = email.lower()
            if unique_contacts.get(email, {}).get('name'):
                continue

            if email in existing_contacts and not self.mailing_list_ids < existing_contacts[email].list_ids:
                existing_contacts[email].list_ids |= self.mailing_list_ids
            if email not in existing_contacts:
                unique_contacts[email] = {
                    'name': name,
                    'subscription_ids': [
                        Command.create({'list_id': mailing_list_id.id})
                        for mailing_list_id in self.mailing_list_ids
                    ],
                }

        if not unique_contacts:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No contacts were imported. All email addresses are already in the mailing list.'),
                    'next': {'type': 'ir.actions.act_window_close'},
                    'sticky': False,
                    'type': 'warning',
                }
            }

        new_contacts = self.env['mailing.contact'].with_context(clean_context(self.env.context)).create([
            {
                'email': email,
                **values,
            }
            for email, values in unique_contacts.items()
        ])

        if ignored := len(contacts) - len(unique_contacts):
            message = _(
                "Contacts successfully imported. Number of contacts imported: %(imported_count)s. Number of duplicates ignored: %(duplicate_count)s",
                imported_count=len(unique_contacts),
                duplicate_count=ignored,
            )
        else:
            message = _("Contacts successfully imported. Number of contacts imported: %(imported_count)s", imported_count=len(unique_contacts))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {
                    'context': self.env.context,
                    'domain': [('id', 'in', new_contacts.ids)],
                    'name': _('New contacts imported'),
                    'res_model': 'mailing.contact',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'list',
                    'views': [[False, 'list'], [False, 'form']],
                },
            }
        }

    def action_open_base_import(self):
        """Open the base import wizard to import mailing list contacts with a xlsx file."""
        self.ensure_one()

        return {
            'type': 'ir.actions.client',
            'tag': 'import',
            'name': _('Import Mailing Contacts'),
            'params': {
                'context': self.env.context,
                'active_model': 'mailing.contact',
            }
        }
