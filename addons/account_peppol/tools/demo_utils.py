# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode
import uuid

from odoo.tools import _
from odoo.tools.misc import file_open

DEMO_BILL_PATH = 'account_peppol/tools/demo_bill'
DEMO_ENC_KEY = 'account_peppol/tools/enc_key'
DEMO_PRIVATE_KEY = 'account_peppol/tools/private_key.pem'

# -------------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------------

def get_demo_vendor_bill(user):
    return {
        'direction': 'incoming',
        'receiver': user.edi_identification,
        'uuid': f'{user.company_id.id}_demo_vendor_bill',
        'accounting_supplier_party': '0208:2718281828',
        'state': 'done',
        'filename': f'{user.company_id.id}_demo_vendor_bill',
        'enc_key': file_open(DEMO_ENC_KEY, mode='rb').read(),
        'document': file_open(DEMO_BILL_PATH, mode='rb').read(),
    }


def _get_notification_message(proxy_state):
    if proxy_state == 'receiver':
        title = _("Registered to receive documents via Peppol (demo).")
        message = _("You can now receive demo vendor bills.")
    else:
        title = _("Registered as a sender (demo).")
        message = _("You can now send invoices in demo mode.")
    return title, message

# -------------------------------------------------------------------------
# MOCKED FUNCTIONS
# -------------------------------------------------------------------------


def _mock_call_peppol_proxy(func, self, endpoint, params=None):

    def _mock_get_all_documents(user):
        if not user.env['account.move'].search_count([
            ('peppol_message_uuid', '=', f'{user.company_id.id}_demo_vendor_bill')
        ]):
            return {'messages': [get_demo_vendor_bill(user)]}
        return {'messages': []}

    def _mock_get_document(user):
        message_uuid = params['message_uuids'][0]
        if message_uuid.endswith('_demo_vendor_bill'):
            return {message_uuid: get_demo_vendor_bill(user)}
        return {message_uuid: {'state': 'done'}}

    def _mock_send_document(user):
        # Trigger the reception of vendor bills
        get_messages_cron = user.env['ir.cron'].sudo().env.ref(
            'account_peppol.ir_cron_peppol_get_new_documents',
            raise_if_not_found=False,
        )
        if get_messages_cron:
            get_messages_cron._trigger()
        return {
            'messages': [{
                'message_uuid': 'demo_%s' % uuid.uuid4(),
            } for i in params['documents']],
        }

    endpoint = endpoint.rsplit('/', 1)[-1]
    params = params or {}
    return {
        # participant routes
        'register_sender': lambda _user: {},
        'register_receiver': lambda _user: {},
        'register_sender_as_receiver': lambda _user: {},
        'update_user': lambda _user: {},
        'cancel_peppol_registration': lambda _user: {},
        'migrate_peppol_registration': lambda _user: {'migration_key': 'demo_migration_key'},
        'participant_status': lambda _user: {'peppol_state': 'receiver'},
        'set_webhook': lambda _user: {},
        # document routes
        'get_all_documents': _mock_get_all_documents,
        'get_document': _mock_get_document,
        'send_document': _mock_send_document,
        'ack': lambda _user: {},
        # service routes are not available in demo mode, mocked by safety
        'add_services': lambda _user: {},
        'get_services': lambda _user:  {'services': self.env['res.company']._peppol_supported_document_types()},
        'remove_services': lambda _user: {},
    }[endpoint](self)


def _mock_get_peppol_verification_state(func, self, *args, **kwargs):
    (endpoint, eas, xml_format) = args
    if not (eas and endpoint):
        return 'not_verified'
    if not xml_format:
        return 'not_valid'
    if xml_format not in self._get_peppol_formats():
        return 'not_valid_format'
    return 'valid'

def _mock_check_peppol_participant_exists(func, self, *args, **kwargs):
    # in demo, no participant already exists
    return False


def _mock_register_proxy_user(func, self, *args, **kwargs):
    edi_user = func(self, *args, **kwargs)
    if edi_user.proxy_type != 'peppol':
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


_demo_behaviour = {
    '_call_peppol_proxy': _mock_call_peppol_proxy,  # account_edi_proxy_client.user
    '_get_peppol_verification_state': _mock_get_peppol_verification_state,  # res.partner
    '_check_peppol_participant_exists': _mock_check_peppol_participant_exists,  # res.partner
    '_register_proxy_user': _mock_register_proxy_user,  # account_edi_proxy_client.user
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
