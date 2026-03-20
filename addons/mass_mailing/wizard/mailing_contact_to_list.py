# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailingContactToList(models.TransientModel):
    _name = 'mailing.contact.to.list'
    _description = "Add Contacts to Mailing List"

    contact_ids = fields.Many2many('mailing.contact', string='Contacts')
    mailing_list_id = fields.Many2one('mailing.list', string='Mailing List', required=True)

    def action_add_contacts(self):
        """Simply add contacts to the mailing list and go to the list."""
        self._add_contacts_to_mailing_list()

        action = self.env['ir.actions.actions']._for_xml_id('mass_mailing.action_view_mass_mailing_lists')
        action.update({
            'res_id': self.mailing_list_id.id,
            'target': 'current',
            'views': [[False, 'form']],
        })
        return action

    def _add_contacts_to_mailing_list(self):
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
