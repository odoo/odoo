from odoo import _, api, fields, models, tools
from odoo.addons.iap.tools import iap_tools

DIRECTORY_CORRESPONDENCE_TABLE = {
    'partner_name':     'name',
    'email':            'email_ids',
    'mobile':           'phone_ids',
    'street':           'street',
    'zip':              'postal_code',
    'city':             'city',
    'state_id':         'state_id',
    'country_id':       'country_id',
}

class Lead(models.Model):
    _inherit = 'crm.lead'
    _DEFAULT_IAP_ENDPOINT = 'https://directory.api.odoo.com'

    def _cron_send_votes(self):
        iap_payload = []
        domains = self.env['crm.lead.domain'].search([])
        
        for domain in domains:
            domain_values = {}
            votes = self.env['crm.lead.vote'].search([('domain_id', '=', domain.id)])
            for vote in votes:
                domain_values[vote.field] = vote.value
            iap_payload.append({
                'domain': domain.name,
                'values': domain_values,
            })
        if iap_payload:
            try:
                dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
                endpoint = self.env['ir.config_parameter'].sudo().get_param('enrich.endpoint', self._DEFAULT_IAP_ENDPOINT) + '/api/directory/1/vote'
                params = {
                    'db_uuid': dbuuid,
                    'companies_data': iap_payload,
                }
                iap_tools.iap_jsonrpc(endpoint, params=params)
                domains.unlink()
            except Exception:
                    pass

    def write(self, values):
        self.ensure_one()
        if self.iap_enrich_done:
            if self.website:
                company_domain = tools.url_domain_extract(self.website)
            elif self.email:
                company_domain = tools.email_domain_extract(self.email)
            else:
                return super(Lead, self).write(values)

            domain = self.env['crm.lead.domain'].sudo().search([('name', '=', company_domain)], limit=1)
            if not domain:
                domain = self.env['crm.lead.domain'].sudo().create({'name': company_domain})
            else:
                domain = domain[0]

            votes =  self.env['crm.lead.vote'].sudo().search([('domain_id', '=', domain.id)], limit=1)
            for field, value in values.items():
                if field in DIRECTORY_CORRESPONDENCE_TABLE:
                    vote = list(filter(lambda v: v.field == field, votes))
                    if vote:
                        vote[0].unlink()
                    self.env['crm.lead.vote'].sudo().create({
                        'field': DIRECTORY_CORRESPONDENCE_TABLE[field],
                        'value': value,
                        'domain_id': domain.id,
                    })
        return super(Lead, self).write(values)
