# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _

class MailingContactToList(models.TransientModel):
    _name = "mailing.contact.to.list"
    _description = "Add Contacts to Mailing List"

    contact_ids = fields.Many2many('mailing.contact', string='Contacts')
    mailing_list_id = fields.Many2one('mailing.list', string='Mailing List', required=True)

    def action_add_contacts(self):
        """ Simply add contacts to the mailing list and close wizard. """
        return self._add_contacts_to_mailing_list({'type': 'ir.actions.act_window_close'})

    def action_add_contacts_and_send_mailing(self):
        """ Add contacts to the mailing list and redirect to a new mailing on
        this list. """
        self.ensure_one()

        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing.mailing_mailing_action_mail")
        action['views'] = [[False, "form"]]
        action['target'] = 'current'
        action['context'] = {
            'default_contact_list_ids': [self.mailing_list_id.id]
        }
        return self._add_contacts_to_mailing_list(action)

    def _add_contacts_to_mailing_list(self, action):
        self.ensure_one()

        previous_count = len(self.mailing_list_id.contact_ids)
        self.mailing_list_id.write({
            'contact_ids': [
                (4, contact.id)
                for contact in self.contact_ids
                if contact not in self.mailing_list_id.contact_ids]
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'message': _("%s Mailing Contacts have been added. ",
                             len(self.mailing_list_id.contact_ids) - previous_count
                            ),
                'sticky': False,
                'next': action,
            }
        }
