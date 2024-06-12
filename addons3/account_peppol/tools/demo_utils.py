# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode
from decorator import decorator
import uuid

from odoo import _, fields, modules, tools
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

# -------------------------------------------------------------------------
# MOCKED FUNCTIONS
# -------------------------------------------------------------------------

def _mock_make_request(func, self, *args, **kwargs):

    def _mock_get_all_documents(user, args, kwargs):
        if not user.env['account.move'].search_count([
            ('peppol_message_uuid', '=', f'{user.company_id.id}_demo_vendor_bill')
        ]):
            return {'messages': [get_demo_vendor_bill(user)]}
        return {'messages': []}

    def _mock_get_document(user, args, kwargs):
        message_uuid = args[1]['message_uuids'][0]
        if message_uuid.endswith('_demo_vendor_bill'):
            return {message_uuid: get_demo_vendor_bill(user)}
        return {message_uuid: {'state': 'done'}}

    def _mock_send_document(user, args, kwargs):
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
            } for i in args[1]['documents']],
        }

    endpoint = args[0].split('/')[-1]
    return {
        'ack': lambda _user, _args, _kwargs: {},
        'activate_participant': lambda _user, _args, _kwargs: {},
        'get_all_documents': _mock_get_all_documents,
        'get_document': _mock_get_document,
        'participant_status': lambda _user, _args, _kwargs: {'peppol_state': 'active'},
        'send_document': _mock_send_document,
    }[endpoint](self, args, kwargs)

def _mock_button_verify_partner_endpoint(func, self, *args, **kwargs):
    self.ensure_one()
    self.account_peppol_validity_last_check = fields.Date.today()
    self.account_peppol_is_endpoint_valid = True

def _mock_user_creation(func, self, *args, **kwargs):
    func(self, *args, **kwargs)
    self.write({
        'account_peppol_proxy_state': 'active',
    })
    self.account_peppol_edi_user.write({
        'private_key': b64encode(file_open(DEMO_PRIVATE_KEY, 'rb').read()),
    })

def _mock_deregister_participant(func, self, *args, **kwargs):
    # Set documents sent in demo to a state where they can be re-sent
    demo_moves = self.env['account.move'].search([
        ('company_id', '=', self.company_id.id),
        ('peppol_message_uuid', '=like', 'demo_%'),
    ])
    demo_moves.write({
        'peppol_message_uuid': None,
        'peppol_move_state': None,
    })
    demo_moves.message_main_attachment_id.unlink()
    demo_moves.ubl_cii_xml_id.unlink()
    log_message = _('The peppol status of the documents has been reset when switching from Demo to Live.')
    demo_moves._message_log_batch(bodies=dict((move.id, log_message) for move in demo_moves))

    # also unlink the demo vendor bill
    self.env['account.move'].search([
        ('company_id', '=', self.company_id.id),
        ('peppol_message_uuid', '=', f'{self.company_id.id}_demo_vendor_bill'),
    ]).unlink()

    mode_constraint = self.env['ir.config_parameter'].get_param('account_peppol.mode_constraint')
    self.account_peppol_edi_user.unlink()
    self.account_peppol_proxy_state = 'not_registered'
    self.account_peppol_edi_mode = mode_constraint


def _mock_update_user_data(func, self, *args, **kwargs):
    pass

def _mock_migrate_participant(func, self, *args, **kwargs):
    self.account_peppol_migration_key = 'I9cz9yw*ruDM%4VSj94s'

_demo_behaviour = {
    '_make_request': _mock_make_request,
    'button_account_peppol_check_partner_endpoint': _mock_button_verify_partner_endpoint,
    'button_create_peppol_proxy_user': _mock_user_creation,
    'button_deregister_peppol_participant': _mock_deregister_participant,
    'button_migrate_peppol_registration': _mock_migrate_participant,
    'button_update_peppol_user_data': _mock_update_user_data,
}

# -------------------------------------------------------------------------
# DECORATORS
# -------------------------------------------------------------------------

@decorator
def handle_demo(func, self, *args, **kwargs):
    """ This decorator is used on methods that should be mocked in demo mode.

    First handle the decision: "Are we in demo mode?", and conditionally decide which function to
    execute. Whether we are in demo mode depends on the edi_mode of the EDI user, but the EDI user
    is accessible in different ways depending on the model the function is called from and in some
    contexts it might not yet exist, in which case demo mode should instead depend on the content
    of the "account_peppol.edi.mode" config param.
    """
    def get_demo_mode_account_edi_proxy_client_user(self, args, kwargs):
        if self.id:
            return self.edi_mode == 'demo' and self.proxy_type == 'peppol'
        demo_param = self.env['ir.config_parameter'].get_param('account_peppol.edi.mode') == 'demo'
        if len(args) > 1 and 'proxy_type' in args[1]:
            return demo_param and args[1]['proxy_type'] == 'peppol'
        return demo_param

    def get_demo_mode_res_config_settings(self, args, kwargs):
        if self.account_peppol_edi_user:
            return self.account_peppol_edi_user.edi_mode == 'demo'
        return self.account_peppol_edi_mode == 'demo'

    def get_demo_mode_res_partner(self, args, kwargs):
        peppol_user = self.env.company.sudo().account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'peppol')
        if peppol_user:
            return peppol_user.edi_mode == 'demo'
        return False

    get_demo_mode = {
        'account_edi_proxy_client.user': get_demo_mode_account_edi_proxy_client_user,
        'res.config.settings': get_demo_mode_res_config_settings,
        'res.partner': get_demo_mode_res_partner,
    }
    demo_mode = get_demo_mode.get(self._name) and get_demo_mode[self._name](self, args, kwargs) or False

    if not demo_mode or tools.config['test_enable'] or modules.module.current_test:
        return func(self, *args, **kwargs)
    return _demo_behaviour[func.__name__](func, self, *args, **kwargs)
