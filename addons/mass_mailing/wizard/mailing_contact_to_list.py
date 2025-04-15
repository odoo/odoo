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
        self._add_contacts_to_mailing_list()

        action = self.env['ir.actions.actions']._for_xml_id('mass_mailing.action_view_mass_mailing_lists')
        action.update({
            'res_id': self.mailing_list_id.id,
            'target': 'current',
            'views': [[False, 'form']],
        })
        return action


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
        self._add_contacts_to_mailing_list()
        return action

    def _add_contacts_to_mailing_list(self):
        self.ensure_one()
        self.mailing_list_id.write({
            'contact_ids': [
                (4, contact.id)
                for contact in self.contact_ids
                if contact not in self.mailing_list_id.contact_ids]
            })
