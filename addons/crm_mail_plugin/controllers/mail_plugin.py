# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.fields import Domain
from odoo.http import request, route
from odoo.tools import html2plaintext, email_normalize
from odoo.tools.misc import formatLang
from odoo.tools.image import image_data_uri

from odoo.addons.mail_plugin.controllers import mail_plugin

_logger = logging.getLogger(__name__)


class MailPluginController(mail_plugin.MailPluginController):
    def _get_record_redirect_url(self, model, record_id):
        if model == 'crm.lead':
            return f'/odoo/crm/{int(record_id)}'

        return super()._get_record_redirect_url(model, record_id)

    def _search_records(self, model, terms, limit=30):
        if model == "crm.lead":
            domain = Domain.OR([('name', 'ilike', term)] for term in terms)
            return self._search_and_format_leads(domain, limit=limit)

        return super()._search_records(model, terms, limit)

    def _search_and_format_leads(self, domain, limit=30):
        """Search the leads base on the domain and format the result.

        The lead structure is:
        {
            id: the lead's id,
            name: the lead's name,
            revenues_description: the expected revenue with probability
        }
        """
        lead_count = request.env['crm.lead'].search_count(domain)
        partner_leads = request.env['crm.lead'].search(
            domain,
            limit=limit,
            order='probability ASC, priority ASC, create_date DESC',
        )
        leads = [self._format_lead(lead) for lead in partner_leads]
        return leads, lead_count

    def _get_contact_data(self, partner, email, **kwargs):
        """
        Return the leads key only if the current user can create leads. So, if they can not
        create leads, the section won't be visible on the addin side (like if the CRM
        module was not installed on the database).
        """
        contact_values = super()._get_contact_data(partner, email, **kwargs)

        if not request.env['crm.lead'].has_access('create'):
            return contact_values

        domain = []
        if partner:
            domain = Domain('partner_id', '=', partner.id)
            if partner.email_normalized:
                domain |= Domain('email_normalized', '=', partner.email_normalized)
            elif partner.email:
                domain |= Domain('email', '=', partner.email)

        elif email_normalized := email_normalize(email):
            domain = [('email_normalized', '=', email_normalized)]

        elif email:
            domain = [('email', '=', email)]

        if not domain:
            contact_values['leads'] = []
        else:
            contact_values['leads'], contact_values['lead_count'] = self._search_and_format_leads(
                domain)

        return contact_values

    def _mail_models_access_whitelist(self, access):
        models_whitelist = super()._mail_models_access_whitelist(access)
        if not request.env['crm.lead'].has_access(access):
            return models_whitelist
        return models_whitelist + ['crm.lead']

    def _translation_modules_whitelist(self):
        modules_whitelist = super()._translation_modules_whitelist()
        if not request.env['crm.lead'].has_access('create'):
            return modules_whitelist
        return modules_whitelist + ['crm_mail_plugin']

    @route('/mail_plugin/lead/create', type='jsonrpc', auth='outlook', cors="*")
    def crm_lead_create(self,
        email_body, email_subject, partner_email, partner_name,
        partner_id=None, attachments=None):
        Lead = request.env['crm.lead']
        if partner_id:
            partner = request.env['res.partner'].browse(partner_id).exists()
            if not partner:
                return {'error': 'partner_not_found'}
            Lead = Lead.with_company(partner.company_id)
        else:
            partner = self._search_or_create_partner(partner_email, partner_name)

        lead = Lead.create({
            'name': html2plaintext(email_subject),
            'partner_id': partner.id,
            'description': email_body,
        })

        if attachments:
            request.env["ir.attachment"].create([{
                "name": name,
                "datas": content,
                "res_model": lead._name,
                "res_id": lead.id,
            } for name, content in attachments])

        values = self._format_lead(lead)
        values['partner_id'] = lead.partner_id.id
        values['partner_image'] = image_data_uri(partner.avatar_128)
        return values

    def _format_lead(self, lead):
        lead_values = {
            'id': lead.id,
            'name': lead.name,
        }

        expected_revenue = formatLang(
            request.env,
            lead.expected_revenue,
            currency_obj=lead.company_currency,
        )

        if (
            request.env.user.has_group('crm.group_use_recurring_revenues')
            and lead.recurring_revenue
            and lead.recurring_plan
        ):
            recurring_revenue = formatLang(
                request.env,
                lead.recurring_revenue,
                currency_obj=lead.company_currency,
            )
            lead_values['revenues_description'] = request.env._(
                "%(expected_revenue)s + %(recurring_revenue)s %(recurring_plan)s at %(probability)s%%",
                expected_revenue=expected_revenue,
                recurring_revenue=recurring_revenue,
                recurring_plan=lead.recurring_plan.name,
                probability=lead.probability,
            )
        else:
            lead_values['revenues_description'] = request.env._(
                "%(expected_revenue)s at %(probability)s%%",
                expected_revenue=expected_revenue,
                probability=lead.probability,
            )

        return lead_values
