from math import floor, log10
from odoo import api, models


class CRMHelpers(models.Model):
    _name = 'crm.iap.lead.helpers'
    _description = 'Helper methods for crm_iap_lead modules'

    @api.model
    def notify_no_more_credit(self, service_name, model_name, notification_parameter):
        """
        Notify about the number of credit.
        In order to avoid to spam people each hour, an ir.config_parameter is set
        """
        already_notified = self.env['ir.config_parameter'].sudo().get_param(notification_parameter, False)
        if already_notified:
            return
        mail_template = self.env.ref('crm_iap_lead.lead_generation_no_credits')
        iap_account = self.env['iap.account'].search([('service_name', '=', service_name)], limit=1)
        # Get the email address of the creators of the records
        res = self.env[model_name].search_read([], ['create_uid'])
        uids = set(r['create_uid'][0] for r in res if r.get('create_uid'))
        res = self.env['res.users'].search_read([('id', 'in', list(uids))], ['email'])
        emails = set(r['email'] for r in res if r.get('email'))

        email_values = {
            'email_to': ','.join(emails)
        }
        mail_template.send_mail(iap_account.id, force_send=True, email_values=email_values)
        self.env['ir.config_parameter'].sudo().set_param(notification_parameter, True)

    @api.model
    def lead_vals_from_response(self, lead_type, team_id, tag_ids, user_id, company_data, people_data):
        country_id = self.env['res.country'].search([('code', '=', company_data['country_code'])]).id
        website_url = 'https://www.%s' % company_data['domain'] if company_data['domain'] else False
        lead_vals = {
            # Lead vals from record itself
            'type': lead_type,
            'team_id': team_id,
            'tag_ids': [(6, 0, tag_ids)],
            'user_id': user_id,
            'reveal_id': company_data['clearbit_id'],
            # Lead vals from data
            'name': company_data['name'] or company_data['domain'],
            'partner_name': company_data['legal_name'] or company_data['name'],
            'email_from': ",".join(company_data['email'] or []),
            'phone': company_data['phone'] or (company_data['phone_numbers'] and company_data['phone_numbers'][0]) or '',
            'website': website_url,
            'street': company_data['location'],
            'city': company_data['city'],
            'zip': company_data['postal_code'],
            'country_id': country_id,
            'state_id': self._find_state_id(company_data['state_code'], country_id),
            'description': self._prepare_lead_description(company_data),
        }

        # If type is people then add first contact in lead data
        if people_data:
            lead_vals.update({
                'contact_name': people_data[0]['full_name'],
                'email_from': people_data[0]['email'],
                'function': people_data[0]['title'],
            })
        return lead_vals

    @api.model
    def _find_state_id(self, state_code, country_id):
        state_id = self.env['res.country.state'].search([('code', '=', state_code), ('country_id', '=', country_id)])
        if state_id:
            return state_id.id
        return False

    @api.model
    def _prepare_lead_description(self, reveal_data):
        description = ''
        if reveal_data['sector']:
            description += reveal_data['sector']
        if reveal_data['website_title']:
            description += '\n' + reveal_data['website_title']
        if reveal_data['twitter_bio']:
            description += '\n' + "Twitter Bio: " + reveal_data['twitter_bio']
        if reveal_data['twitter_followers']:
            description += ('\nTwitter %s followers, %s \n') % (reveal_data['twitter_followers'], reveal_data['twitter_location'] or '')

        numbers = ['raised', 'market_cap', 'employees', 'estimated_annual_revenue']
        millnames = ['', ' K', ' M', ' B', 'T']

        def millify(n):
            try:
                n = float(n)
                millidx = max(0, min(len(millnames) - 1, int(floor(0 if n == 0 else log10(abs(n)) / 3))))
                return '{:.0f}{}'.format(n / 10**(3 * millidx), millnames[millidx])
            except Exception:
                return n

        for key in numbers:
            if reveal_data.get(key):
                description += ' %s : %s,' % (key.replace('_', ' ').title(), millify(reveal_data[key]))
        return description

    @api.model
    def format_data_for_message_post(self, company_data, people_data):
        log_data = {
            'twitter': company_data['twitter'],
            'description': company_data['description'],
            'logo': company_data['logo'],
            'name': company_data['name'],
            'phone_numbers': company_data['phone_numbers'],
            'facebook': company_data['facebook'],
            'linkedin': company_data['linkedin'],
            'crunchbase': company_data['crunchbase'],
            'tech': [t.replace('_', ' ').title() for t in company_data['tech']],
            'people_data': people_data,
        }
        timezone = company_data['timezone']
        if timezone:
            log_data.update({
                'timezone': timezone.replace('_', ' ').title(),
                'timezone_url': company_data['timezone_url'],
            })
        return log_data
