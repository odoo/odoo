from base64 import b64encode
from decorator import decorator

from odoo.tools.misc import file_open

DEMO_PRIVATE_KEY = 'account_peppol/tools/private_key.pem'

# -------------------------------------------------------------------------
# MOCKED FUNCTIONS
# -------------------------------------------------------------------------


def _mock_call_peppol_proxy(func, self, *args, **kwargs):
    if self.proxy_type != 'pdp':
        return func(self, *args, **kwargs)

    endpoint = args[0].split('/')[-1]
    if endpoint not in ('register_receiver', 'cancel_pdp_registration', 'get_all_ppf_documents', 'get_ppf_document'):
        return func(self, *args, **kwargs)

    return {
        'register_receiver': lambda _user, *args, **kwargs: {},
        'cancel_pdp_registration': lambda _user, *args, **kwargs: {},
        'get_all_ppf_documents': lambda _user, *args, **kwargs: {'messages': []},
        'get_ppf_document': lambda _user, *args, **kwargs: {'messages': []},
    }[endpoint](self, *args, **kwargs)


def _mock_register_proxy_user(func, self, *args, **kwargs):
    # The function already has some special logic to create an edi user.
    edi_user = func(self, *args, **kwargs)
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


def _mock_peppol_register_receiver(func, self, *args, **kwargs):
    func(self, *args, **kwargs)
    if self.proxy_type != 'pdp':
        return
    self.company_id.account_peppol_proxy_state = 'receiver'


def _mock_pdp_annuaire_lookup_participant(func, self, *args, **kwargs):
    edi_identification = args[0]
    peppol_eas = edi_identification.partition(":")[0]
    return {'in_annuaire': peppol_eas == '0225'}


def _mock_get_peppol_verification_state(func, self, *args, **kwargs):
    (peppol_endpoint, peppol_eas, invoice_edi_format) = args
    if peppol_eas != '0225':
        func(self, peppol_endpoint, peppol_eas, invoice_edi_format)
    if not invoice_edi_format:
        return 'not_valid'
    if invoice_edi_format not in self._get_peppol_formats():
        return 'not_valid_format'
    return 'valid'


_demo_behaviour = {
    '_register_proxy_user': _mock_register_proxy_user,  # account_edi_proxy_client.user
    '_peppol_register_receiver': _mock_peppol_register_receiver,  # account_edi_proxy_client.user
    '_call_peppol_proxy': _mock_call_peppol_proxy,  # account_edi_proxy_client.user
    '_pdp_annuaire_lookup_participant': _mock_pdp_annuaire_lookup_participant,  # res.partner
    '_get_peppol_verification_state': _mock_get_peppol_verification_state,  # res.partner
}

# -------------------------------------------------------------------------
# DECORATORS
# -------------------------------------------------------------------------


@decorator
def handle_demo(func, self, *args, **kwargs):
    """ This decorator is used on methods that should be mocked in demo mode.

    First handle the decision: "Are we in demo mode?", and conditionally decide which function to
    execute.
    """
    if self.env.company._get_peppol_edi_mode() == 'demo':
        return _demo_behaviour[func.__name__](func, self, *args, **kwargs)
    return func(self, *args, **kwargs)
