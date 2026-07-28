# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.http import request
from odoo.tools.misc import formatLang

from odoo.addons.mail_plugin.controllers import mail_plugin

_logger = logging.getLogger(__name__)


class MailPluginController(mail_plugin.MailPluginController):

    def _fetch_partner_leads(self, partner, limit=5, offset=0):
        """
        Returns an array containing partner leads, each lead will have the following structure :
        {
            id: the lead's id,
            name: the lead's name,
            expected_revenue: the expected revenue field value
            probability: the value of the probability field,
            recurring_revenue: the value of the recurring_revenue field if the lead has a recurring revenue
            recurring_plan: the value of the recurring plan field if the lead has a recurring revenue
        }
        """

        partner_leads = request.env['crm.lead'].search(
            [('partner_id', '=', partner.id)], offset=offset, limit=limit)
        recurring_revenues = request.env.user.has_group('crm.group_use_recurring_revenues')

        leads = []
        for lead in partner_leads:
            lead_values = {
                'lead_id': lead.id,
                'name': lead.name,
                'expected_revenue': formatLang(request.env, lead.expected_revenue, monetary=True,
                                               currency_obj=lead.company_currency),
                'probability': lead.probability,
            }

            if recurring_revenues:
                lead_values.update({
                    'recurring_revenue': formatLang(request.env, lead.recurring_revenue, monetary=True,
                                                    currency_obj=lead.company_currency),
                    'recurring_plan': lead.recurring_plan.name,
                })

            leads.append(lead_values)

        return leads

    def _get_contact_data(self, partner):
        """
        Return the leads key only if the current user can create leads. So, if they can not
        create leads, the section won't be visible on the addin side (like if the CRM
        module was not installed on the database).
        """
        contact_values = super(MailPluginController, self)._get_contact_data(partner)

        if not request.env['crm.lead'].check_access_rights('create', raise_exception=False):
            return contact_values

        if not partner:
            contact_values['leads'] = []
        else:
            contact_values['leads'] = self._fetch_partner_leads(partner)
        return contact_values

    def _mail_content_logging_models_whitelist(self):
        models_whitelist = super(MailPluginController, self)._mail_content_logging_models_whitelist()
        if not request.env['crm.lead'].check_access_rights('create', raise_exception=False):
            return models_whitelist
        return models_whitelist + ['crm.lead']

    def _translation_modules_whitelist(self):
        modules_whitelist = super(MailPluginController, self)._translation_modules_whitelist()
        if not request.env['crm.lead'].check_access_rights('create', raise_exception=False):
            return modules_whitelist
        return modules_whitelist + ['crm_mail_plugin']
