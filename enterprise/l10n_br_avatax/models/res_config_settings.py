# Part of Odoo. See LICENSE file for full copyright and licensing details.
from json import JSONDecodeError
from pprint import pformat

from odoo import fields, models, api, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import street_split
from odoo.tools.safe_eval import json


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_br_avatax_portal_email = fields.Char(
        related='company_id.l10n_br_avatax_portal_email',
        string='Avatax Portal Email',
        readonly=False,
    )
    l10n_br_avatax_show_overwrite_warning = fields.Boolean(
        compute='_compute_show_overwrite_warning',
        store=False,
        help="Technical field used to determine whether or not the user is about to overwrite his current API credentials"
             "with new ones, since the old credentials won't be recoverable we warn."
    )
    l10n_br_avatax_api_identifier = fields.Char(
        related='company_id.l10n_br_avatax_api_identifier',
        readonly=False,
        string='Avalara Brazil API ID'
    )
    l10n_br_avatax_api_key = fields.Char(
        related='company_id.l10n_br_avatax_api_key',
        readonly=False,
        string='Avalara Brazil API Key'
    )
    l10n_br_avalara_environment = fields.Selection(
        related='company_id.l10n_br_avalara_environment',
        readonly=False,
        string="Avalara Brazil Environment",
        required=True,
    )
    l10n_br_icms_rate = fields.Float(
        related='company_id.l10n_br_icms_rate',
        string='Simplified Regime ICMS Rate',
        help="This only applies if you are a simplified tax regime company.",
        readonly=False,
    )
    l10n_br_tax_regime = fields.Selection(related='company_id.partner_id.l10n_br_tax_regime')
    l10n_br_cnae_code_id = fields.Many2one(
        related='company_id.l10n_br_cnae_code_id',
        help="Main CNAE code registered with the government.",
        readonly=False,
    )

    @api.depends('l10n_br_avalara_environment', 'l10n_br_avatax_api_identifier', 'l10n_br_avatax_api_key')
    def _compute_show_overwrite_warning(self):
        for settings in self:
            settings.l10n_br_avatax_show_overwrite_warning = bool(settings.l10n_br_avatax_api_identifier)

    def create_account(self):
        """ This gathers all metadata needed to create an account, does the request to the IAP server and parses
        the response. """
        partner = self.company_id.partner_id
        street_data = street_split(partner.street)
        payload = {
            'subscriptionName': self.company_name,
            'corporateName': self.company_name,
            'tradeName': self.company_name,
            'cnpj': partner.vat,
            'municipalRegistration': partner.l10n_br_im_code,
            'stateRegistration': partner.l10n_br_ie_code,
            'suframa': partner.l10n_br_isuf_code,
            'address': street_data['street_name'],
            'neighborhood': partner.street2,
            'addressNumber': street_data['street_number'],
            'corporateContactEmailAddress': self.l10n_br_avatax_portal_email,
            'zipCode': partner.zip,
        }
        result = self.env['account.external.tax.mixin']._l10n_br_iap_create_account({k: v or '' for k, v in payload.items()}, self.company_id)

        if 'avalara_api_id' in result:
            self.company_id.l10n_br_avatax_api_identifier = result['avalara_api_id']
            self.company_id.l10n_br_avatax_api_key = result['avalara_api_key']
        else:
            # API returns errors either as a string containing JSON:
            # {'message': '{"errors":{"Login do usuário master":["Login já utlizado"]},"title":"One or more validation errors occurred.","status":400,"traceId":"0HMPVCEB27KLU:000000E5"}', 'isError': True}
            # Or as a regular string:
            # {'message': 'An unhandled error occurred. Trace ID: xxx', 'isError': True}
            if 'message' in result:
                try:
                    result = json.loads(result['message'])
                except JSONDecodeError:
                    if 'unhandled error occurred' in result['message']:
                        raise UserError(_('The Avatax platform failed to create your account. Please ensure the address on your company is correct. If it is please contact support at odoo.com/help.'))
                    else:
                        raise UserError(result['message'])

            errors = result.get('errors')
            if errors:
                msg = []
                for key, errors in errors.items():
                    curr = [key + ':'] + [f' - {error}' for error in errors]
                    msg.append('\n'.join(curr))
                raise UserError('\n'.join(msg))

    def button_l10n_br_avatax_ping(self):
        if not self.env.is_system():
            raise AccessError(_('Only administrators can ping Avatax.'))

        query_result = self.env['account.external.tax.mixin']._l10n_br_iap_ping(self.company_id)
        raise UserError(_(
            "Server Response:\n%s",
            pformat(query_result)
        ))

    def button_l10n_br_avatax_log(self):
        return self.env['account.external.tax.mixin']._l10n_br_avatax_log()
