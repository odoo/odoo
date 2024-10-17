# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard
from . import tools

from .models.account_edi_proxy_user import Account_Edi_Proxy_ClientUser
from .models.account_journal import AccountJournal
from .models.account_move import AccountMove
from .models.account_move_send import AccountMoveSend
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .wizard.account_move_send_batch_wizard import AccountMoveSendBatchWizard
from .wizard.account_move_send_wizard import AccountMoveSendWizard
from .wizard.peppol_registration import PeppolRegistration
from .wizard.service_wizard import Account_PeppolService, Account_PeppolServiceWizard


def _account_peppol_post_init(env):
    for company in env['res.company'].sudo().search([]):
        env['ir.default'].set('res.partner', 'peppol_verification_state', 'not_verified', company_id=company.id)
