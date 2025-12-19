# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class MailingContactToList(models.TransientModel):
    _name = 'mailing.contact.to.list'
    _description = "Add Contacts to Mailing List"

    contact_ids = fields.Many2many('mailing.contact', string='Contacts')
    mailing_list_id = fields.Many2one('mailing.list', string='Mailing List', required=True)

    def action_add_contacts(self):
        """ Simply add contacts to the mailing list and close wizard. """
        return self._add_contacts_to_mailing_list({'type': 'ir.actions.act_window_close'})

    def _add_contacts_to_mailing_list(self, action):
        self.ensure_one()

        contacts_to_add = self.contact_ids.filtered(lambda c: c not in self.mailing_list_id.contact_ids)
        self.mailing_list_id.write({
            'subscription_ids': [
                (0, 0, {
                    'contact_id': contact.id,
                    'list_id': self.mailing_list_id.id,
                }) for contact in contacts_to_add
            ]
        })
        already_on_list_count = len(self.contact_ids) - len(contacts_to_add)
        message = _("%(added_contacts_count)s Mailing Contacts have been added.", added_contacts_count=len(contacts_to_add))
        if already_on_list_count:
            message += _("\n\n%(already_on_list_count)s Mailing Contacts were already on this list.", already_on_list_count=already_on_list_count)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'message': message,
                'sticky': False,
                'next': action,
            }
        }
