# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_mass_mailing_campaign = fields.Boolean(
        string="Mailing Campaigns",
        implied_group='mass_mailing.group_mass_mailing_campaign',
        help="""This is useful if your marketing campaigns are composed of several emails""")
    mass_mailing_outgoing_mail_server = fields.Boolean(
        string="Dedicated Server",
        config_parameter='mass_mailing.outgoing_mail_server',
        help='Use a specific mail server in priority. Otherwise Odoo relies on the first outgoing mail server available (based on their sequencing) as it does for normal mails.')
    mass_mailing_mail_server_id = fields.Many2one(
        'ir.mail_server', string='Mail Server',
        config_parameter='mass_mailing.mail_server_id')
    show_blacklist_buttons = fields.Boolean(
        string="Blacklist Option when Unsubscribing",
        config_parameter='mass_mailing.show_blacklist_buttons',
        help="""Allow the recipient to manage themselves their state in the blacklist via the unsubscription page.""")
    mass_mailing_reports = fields.Boolean(
        string='24H Stat Mailing Reports',
        config_parameter='mass_mailing.mass_mailing_reports',
        help='Check how well your mailing is doing a day after it has been sent.')
    mass_mailing_split_contact_name = fields.Boolean(
        string='Split First and Last Name',
        help='Separate Mailing Contact Names into two fields')

    @api.onchange('mass_mailing_outgoing_mail_server')
    def _onchange_mass_mailing_outgoing_mail_server(self):
        if not self.mass_mailing_outgoing_mail_server:
            self.mass_mailing_mail_server_id = False

    @api.model
    def get_values(self):
        res = super().get_values()
        res.update(
            mass_mailing_split_contact_name=self.env['mailing.contact']._is_name_split_activated(),
        )
        return res

    def set_values(self):
        super().set_values()
        ab_test_cron = self.env.ref('mass_mailing.ir_cron_mass_mailing_ab_testing').sudo()
        if ab_test_cron and ab_test_cron.active != self.group_mass_mailing_campaign:
            ab_test_cron.active = self.group_mass_mailing_campaign
        if self.env['mailing.contact']._is_name_split_activated() != self.mass_mailing_split_contact_name:
            self.env.ref(
                "mass_mailing.mailing_contact_view_tree_split_name").active = self.mass_mailing_split_contact_name
            self.env.ref(
                "mass_mailing.mailing_contact_view_form_split_name").active = self.mass_mailing_split_contact_name
