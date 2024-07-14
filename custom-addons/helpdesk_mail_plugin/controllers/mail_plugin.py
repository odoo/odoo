# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.mail_plugin.controllers import mail_plugin


class MailPluginController(mail_plugin.MailPluginController):

    def _get_contact_data(self, partner):
        """
        Return the tickets key only if the current user can create tickets. So, if they can not
        create tickets, the section won't be visible on the addin side (like if the Helpdesk
        module was not installed on the database).
        """
        contact_values = super(MailPluginController, self)._get_contact_data(partner)

        if not request.env['helpdesk.ticket'].check_access_rights('create', raise_exception=False):
            return contact_values

        contact_values['tickets'] = self._fetch_partner_tickets(partner) if partner else []

        return contact_values

    def _fetch_partner_tickets(self, partner, offset=0, limit=5):
        """Returns an array containing partner tickets, each ticket will have the following structure :
                {
                    ticket_id: the ticket's id,
                    name: the ticket's name,
                    fold: True if the ticket has been closed, false otherwise
                }
        """
        tickets = request.env['helpdesk.ticket'].search(
            [('partner_id', '=', partner.id)], offset=offset, limit=limit)

        return [{
            'ticket_id': ticket.id,
            'name': ticket.display_name,
            'fold': ticket.stage_id.fold
        } for ticket in tickets]

    def _mail_content_logging_models_whitelist(self):
        models_whitelist = super(MailPluginController, self)._mail_content_logging_models_whitelist()
        if not request.env['helpdesk.ticket'].check_access_rights('create', raise_exception=False):
            return models_whitelist
        return models_whitelist + ['helpdesk.ticket']

    def _translation_modules_whitelist(self):
        modules_whitelist = super(MailPluginController, self)._translation_modules_whitelist()
        if not request.env['helpdesk.ticket'].check_access_rights('create', raise_exception=False):
            return modules_whitelist
        return modules_whitelist + ['helpdesk_mail_plugin']
