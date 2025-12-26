from odoo import _, http
from odoo.addons.mail_plugin.controllers import mail_plugin
from odoo.http import request
from odoo.tools.misc import formatLang


class MailPluginController(mail_plugin.MailPluginController):

    @http.route('/mail/plugin/leads/refresh', type='json', auth='outlook', cors='*')
    def refresh_leads(self, partner, **kwargs):
        partner = request.env['res.partner'].browse(partner['id'])
        leads = self._fetch_partner_leads(partner)

        return leads

    @http.route('/mail/plugin/leads/search', type='json', auth='outlook', cors='*')
    def get_leads(self, query='', partner=None, **kwargs):
        if not partner:
            return {'error': _('Partner ID is required.')}

        partner = request.env['res.partner'].browse(partner['id']).exists()
        if not partner:
            return {'error': _('The Partner does not exist.')}

        if not query.strip():
            return {'error': _('Search query cannot be empty.')}

        partner_leads = request.env['crm.lead'].search([
            '|','|',
            ('partner_id.email', 'ilike', query),
            ('partner_id.name', 'ilike', query),
            ('name', 'ilike', query)
        ], order='create_date')
        recurring_revenues = request.env.user.has_group('crm.group_use_recurring_revenues')

        leads = []
        for lead in partner_leads:
            record = {
                'lead_id': lead.id,
                'name': lead.name,
                'expected_revenue': formatLang(request.env, lead.expected_revenue, currency_obj=lead.company_currency),
                'probability': lead.probability,
            }

            if recurring_revenues:
                record.update({
                    'recurring_revenue': formatLang(request.env, lead.recurring_revenue, currency_obj=lead.company_currency),
                    'recurring_plan': lead.recurring_plan.name,
                })

            leads.append(record)

        return leads
