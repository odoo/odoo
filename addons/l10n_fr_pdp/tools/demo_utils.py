from base64 import b64encode

from odoo import fields
from odoo.tools.misc import file_open

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

    edi_user.private_key = b64encode(file_open(DEMO_PRIVATE_KEY, 'rb').read())
    return edi_user


def _mock_peppol_register_receiver(func, self):
    if self.proxy_type != 'pdp':
        return
    func(self)
    self.company_id.account_peppol_proxy_state = 'active'
    if self.company_id.l10n_fr_pdp_pilot_phase:
        self.sudo().company_id.l10n_fr_pdp_annuaire_start_date = fields.Date.to_date(fields.Datetime.now())
    else:
        self.sudo().company_id.l10n_fr_pdp_annuaire_start_date = fields.Date.to_date('2026-09-01')


def _mock_pdp_annuaire_lookup_participant(func, self, edi_identification):
    peppol_eas = edi_identification.partition(":")[0]
    return {'in_annuaire': peppol_eas == '0225'}


def _mock_l10n_fr_pdp_update_pilot_phase(func, self, value):
    self.sudo().l10n_fr_pdp_pilot_phase = value
    if value:
        self.sudo().l10n_fr_pdp_annuaire_start_date = fields.Date.to_date(fields.Datetime.now())
    else:
        self.sudo().l10n_fr_pdp_annuaire_start_date = fields.Date.to_date('2026-09-01')


def _mock_button_trigger_authentication(func, self):
    self.pdp_kyc_status = 'success'
    return self._action_open_pdp_form()


_demo_behaviour = {
    '_register_proxy_user': _mock_register_proxy_user,  # account_edi_proxy_client.user
    '_peppol_register_receiver': _mock_peppol_register_receiver,  # account_edi_proxy_client.user
    '_call_peppol_proxy': _mock_call_peppol_proxy,  # account_edi_proxy_client.user
    '_pdp_annuaire_lookup_participant': _mock_pdp_annuaire_lookup_participant,  # res.partner
    '_l10n_fr_pdp_update_pilot_phase': _mock_l10n_fr_pdp_update_pilot_phase,  # res.company
    'button_trigger_authentication': _mock_button_trigger_authentication,  # pdp.registration
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
