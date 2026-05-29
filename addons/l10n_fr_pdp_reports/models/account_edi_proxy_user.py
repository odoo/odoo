import uuid

from odoo import fields, models
from odoo.exceptions import UserError

DEMO_ENDPOINTS = {  # pdp reports specific endpoints not already mocked by l10n_fr_pdp demo utils
    'pilot_phase': lambda params: {
        'annuaire_line_start_date': fields.Date.today(),
        'pilot_phase': params['pdp_pilot_phase'],
    },
    'participant_status': lambda params: {},
    'send_document': lambda params: {
        'ppf_messages': [{'message_uuid': f'demo_{uuid.uuid4()}'} for _d in params['documents']],
    },
    'pdp_state': lambda params: {},
}


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _call_peppol_proxy(self, endpoint, params=None):
        if self.env.company._get_peppol_edi_mode() == 'demo' and (demo_endpoint := DEMO_ENDPOINTS.get(endpoint.split('/')[-1])):
            self.ensure_one()
            if self.proxy_type != 'pdp':
                raise UserError(self.env._('EDI user should be of type PDP'))
            return demo_endpoint(params)
        else:
            return super()._call_peppol_proxy(endpoint, params)
