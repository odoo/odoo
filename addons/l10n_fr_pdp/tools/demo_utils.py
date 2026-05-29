from base64 import b64encode

from odoo import fields
from odoo.tools.misc import file_open

from odoo.addons.account_peppol.models.res_partner import ResPartner

DEMO_PRIVATE_KEY = 'account_peppol/tools/private_key.pem'

# -------------------------------------------------------------------------
# MOCKED FUNCTIONS
# -------------------------------------------------------------------------


def _mock_call_peppol_proxy(func, self, endpoint, params=None):
    if self.proxy_type != 'pdp':
        return func(self, endpoint, params=params)

    endpoint = endpoint.rsplit('/', 1)[-1]
    if endpoint not in ('register_receiver', 'cancel_pdp_registration', 'get_all_ppf_documents', 'get_ppf_document', 'pilot_phase', 'send_response'):
        return func(self, endpoint, params=params)

    return {
        'register_receiver': lambda _user, *args, **kwargs: {},
        'cancel_pdp_registration': lambda _user, *args, **kwargs: {},
        'get_all_ppf_documents': lambda _user, *args, **kwargs: {'messages': []},
        'get_ppf_document': lambda _user, *args, **kwargs: {'messages': []},
        'send_response': lambda _user, *args, **kwargs: {'messages': []},
    }[endpoint](self, endpoint, params=params)


def _mock_register_proxy_user(func, self, company, proxy_type, edi_mode):
    # The function already has some special logic to create an edi user.
    edi_user = func(self, company, proxy_type, edi_mode)
    if edi_user.proxy_type != 'pdp':
        return edi_user

    content = b64encode(file_open(DEMO_PRIVATE_KEY, 'rb').read())

    attachments = self.env['ir.attachment'].search([
        ('res_model', '=', 'certificate.key'),
        ('res_field', '=', 'content'),
        ('company_id', '=', edi_user.company_id.id)
    ])
    content_to_key_id = {attachment.datas: attachment.res_id for attachment in attachments}
    pkey_id = content_to_key_id.get(content)
    if not pkey_id:
        pkey_id = self.env['certificate.key'].create({
            'content': content,
            'company_id': edi_user.company_id.id,
        })
    edi_user.private_key_id = pkey_id
    return edi_user


def _mock_pdp_register_receiver(func, self):
    func(self)
    if self.proxy_type != 'pdp':
        return
    self.company_id.account_peppol_proxy_state = 'receiver'
    if self.company_id.l10n_fr_pdp_pilot_phase:
        self.sudo().company_id.l10n_fr_pdp_annuaire_start_date = fields.Date.to_date(fields.Datetime.now())
    else:
        self.sudo().company_id.l10n_fr_pdp_annuaire_start_date = fields.Date.to_date('2026-09-01')


def _mock_pdp_annuaire_lookup_participant(func, self, edi_identification):
    peppol_eas = edi_identification.partition(":")[0]
    return {'in_annuaire': peppol_eas == '0225'}


def _mock_get_peppol_verification_state(func, self, peppol_endpoint, peppol_eas, invoice_edi_format, process_type='billing'):
    if peppol_eas != '0225':
        return func(self, peppol_endpoint, peppol_eas, invoice_edi_format, process_type=process_type)
    if not invoice_edi_format:
        return 'not_valid'
    if invoice_edi_format != 'ubl_21_fr':
        return 'not_valid_format'
    return 'valid'


def _mock_button_verify_partner_endpoint(func, self, company=None):
    self.ensure_one()
    old_value = self.peppol_verification_state
    company = company or self.env.company
    endpoint, eas, edi_format = self.peppol_endpoint, self.peppol_eas, self._get_peppol_edi_format()
    state = _mock_get_peppol_verification_state(ResPartner._get_peppol_verification_state, self, endpoint, eas, edi_format)
    self.with_company(company).peppol_verification_state = state
    self._log_verification_state_update(company, old_value, state)


def _mock_l10n_fr_pdp_update_pilot_phase(func, self, value):
    self.sudo().l10n_fr_pdp_pilot_phase = value
    if value:
        self.sudo().l10n_fr_pdp_annuaire_start_date = fields.Date.to_date(fields.Datetime.now())
    else:
        self.sudo().l10n_fr_pdp_annuaire_start_date = fields.Date.to_date('2026-09-01')


_demo_behaviour = {
    'button_account_peppol_check_partner_endpoint': _mock_button_verify_partner_endpoint,
    '_register_proxy_user': _mock_register_proxy_user,  # account_edi_proxy_client.user
    '_pdp_register_receiver': _mock_pdp_register_receiver,  # account_edi_proxy_client.user
    '_call_peppol_proxy': _mock_call_peppol_proxy,  # account_edi_proxy_client.user
    '_pdp_annuaire_lookup_participant': _mock_pdp_annuaire_lookup_participant,  # res.partner
    '_get_peppol_verification_state': _mock_get_peppol_verification_state,  # res.partner
    '_l10n_fr_pdp_update_pilot_phase': _mock_l10n_fr_pdp_update_pilot_phase,  # res.company
}

# -------------------------------------------------------------------------
# DECORATORS
# -------------------------------------------------------------------------


def handle_demo(func, /):
    """ This decorator is used on methods that should be mocked in demo mode.

    First handle the decision: "Are we in demo mode?", and conditionally decide which function to
    execute.
    """
    def wrapped(self, *args, **kwargs):
        if self.env.company._get_peppol_edi_mode() == 'demo':
            return _demo_behaviour[func.__name__](func, self, *args, **kwargs)
        return func(self, *args, **kwargs)
    return wrapped
