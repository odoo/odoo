# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
from requests.exceptions import RequestException, Timeout
import json
from json.decoder import JSONDecodeError
from markupsafe import Markup
from urllib.parse import urljoin
import contextlib
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError, RedirectWarning
from odoo.http import request
from odoo.tools import file_open

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'
    l10n_ke_branch_code = fields.Char(
        related='partner_id.l10n_ke_branch_code',
        readonly=False,
        store=True,
    )
    l10n_ke_oscu_serial_number = fields.Char(
        string="Serial Number",
        help="Unique Serial Number you will need to specify in the commitment form of "
             "your eTIMS taxpayer portal during the integration process. ",
        tracking=True,
        compute='_compute_l10n_ke_oscu_serial_number',
        readonly=False,
        store=True,
    )
    l10n_ke_control_unit = fields.Char(
        string="Control Unit ID",
        help="This is retrieved from the device during initialization.",
    )
    l10n_ke_oscu_cmc_key = fields.Char(
        string="Device Communication Key",
        help="If you have an already initialized device, you can put your key here.",
        groups='base.group_system'
    )
    l10n_ke_insurance_code = fields.Char(
        string="Insurance Code",
        help="If this branch has a mandatory insurance policy (e.g. a pharmacy), put its code here.",
    )
    l10n_ke_insurance_name = fields.Char(
        string="Insurance Name",
        help="The name of the branch's insurance policy",
    )
    l10n_ke_insurance_rate = fields.Float(
        string="Insurance Rate",
        help="The premium rate of the branch's insurance policy",
    )
    l10n_ke_server_mode = fields.Selection(
        selection=[
            ('prod', "Production"),
            ('test', "Test"),
            ('demo', "Demo"),
        ],
        string="eTIMS Server Mode",
        help="""
            - Production: Connection to eTIMS in production mode.
            - Test: Connection to eTIMS in test mode.
            - Demo: Mocked data, does not require an initialized OSCU.
        """,
    )
    l10n_ke_oscu_user_help = fields.Boolean(
        string="User should go with the number to KRA first. "
    )
    l10n_ke_oscu_user_agreement = fields.Boolean(
        string="Odoo OSCU user agreement",
        help="Agreement is required to use Odoo as an OSCU service provider.",
        tracking=True,
    )
    l10n_ke_oscu_is_active = fields.Boolean(
        search='_search_l10n_ke_oscu_is_active',
        compute_sudo=True,
    )

    l10n_ke_oscu_last_fetch_purchase_date = fields.Datetime(default=datetime(2018, 1, 1))

    # === Computes === #
    @api.depends('l10n_ke_oscu_cmc_key', 'l10n_ke_branch_code', 'l10n_ke_server_mode')
    def _compute_l10n_ke_oscu_is_active(self):
        for company in self:
            company.l10n_ke_oscu_is_active = (
                company.l10n_ke_server_mode == 'demo'
                or (
                    company.l10n_ke_server_mode in ['test', 'prod']
                    and company.l10n_ke_oscu_cmc_key
                    and company.l10n_ke_branch_code
                    and company.l10n_ke_oscu_user_agreement
                )
            )

    def _search_l10n_ke_oscu_is_active(self, operator, value):
        domain_true = [
            '|',
            ('l10n_ke_server_mode', '=', 'demo'),
            '&', '&', '&',
            ('l10n_ke_server_mode', 'in', ['test', 'prod']),
            ('l10n_ke_oscu_cmc_key', '!=', False),
            ('l10n_ke_branch_code', '!=', False),
            ('l10n_ke_oscu_user_agreement', '=', True),
        ]
        if (operator == '=' and value) or (operator == '!=' and not value):
            return domain_true
        elif (operator == '=' and not value) or (operator == '!=' and value):
            return ['!'] + domain_true

    @api.depends('country_code', 'vat')
    def _compute_l10n_ke_oscu_serial_number(self):
        for company in self.filtered(lambda c: c.country_code == 'KE'):
            company.l10n_ke_oscu_serial_number = f'ODOO/{company.vat}/0'

    # === Overrides === #
    def write(self, vals):
        # If the user has checked the user agreement box, we make it readonly,
        # create an ir.logging entry recording this, and send a confirmation e-mail to the user.
        email_is_not_sent = self.filtered(lambda c: not c.l10n_ke_oscu_user_agreement or not c.l10n_ke_oscu_cmc_key)
        res = super().write(vals)
        if email_is_not_sent:
            for company in email_is_not_sent.filtered(lambda c: c.l10n_ke_oscu_user_agreement and c.l10n_ke_oscu_cmc_key):
                logging_message = f"""
                    Checkbox `Odoo OSCU user agreement` was set to True
                    on Company `{company.name}` (id: {company.id})
                    by user {self.env.user.name} (id: {self.env.user.id}
                    on {fields.Datetime.now()}
                """
                with contextlib.suppress(RuntimeError):  # a RuntimeError would be raised in cases where there is no request
                    logging_message += f"""
                        remote_user: {request.httprequest.remote_user}
                        IP: {request.httprequest.remote_addr}
                        User-Agent: {request.httprequest.user_agent}
                    """
                self.env['ir.logging'].create({
                    'name': 'l10n_ke_edi_oscu',
                    'type': 'server',
                    'level': 'INFO',
                    'dbname': self.env.cr.dbname,
                    'message': logging_message,
                    'func': '',
                    'path': '',
                    'line': '',
                })
                mail_body = Markup("""
                    <div style="margin: 0px; padding: 0px;">
                        <p style="margin: 0px; padding: 0px;">
                            Dear %s,
                            <br/>
                            This is a notification that you have agreed to Odoo's OSCU user agreement. %s can now
                            use OSCU flows in Odoo to declare your activities with the KRA.
                            <br/>
                            This is an automated e-mail and no further action is needed on your part.
                            <br/>
                            Thank you for choosing Odoo for your Kenyan ERP needs.
                        </p>
                    </div>
                """) % (self.env.user.name, company.name)
                mail_subject = f" {company.name} - Odoo OSCU User Agreement confirmation"
                mail_values = {
                    'email_from': self.env.user.email_formatted,
                    'author_id': self.env.user.partner_id.id,
                    'model': None,
                    'res_id': None,
                    'subject': mail_subject,
                    'body_html': mail_body,
                    'email_to': self.env.user.email_formatted,
                }
                self.env['mail.mail'].sudo().create(mail_values)
        return res

    # === Actions === #

    def _l10n_ke_preinitialization_checks(self):
        if not self.l10n_ke_oscu_user_help:
            raise UserError(_('Please confirm that you did the necessary steps in the eTIMS portal first. '))
        if not self.l10n_ke_oscu_user_agreement:
            raise UserError(_("Please agree to the terms of use of Odoo as an OSCU service provider first. "))
        error_fields = []
        on_company = False
        if not self.vat:
            error_fields.append(_('PIN Number (VAT)'))
            on_company = True
        if not self.l10n_ke_branch_code:
            error_fields.append(_('Branch Code'))
            on_company = True
        if not self.l10n_ke_oscu_serial_number:
            error_fields.append(_('OSCU Serial Number'))
        if error_fields:
            error_fields = ["- " + e for e in error_fields]
            msg = _('To initialize the device, please fill in the following elements:   \n%s', '\n'.join(error_fields))
            if not on_company:
                raise UserError(msg)
            else:
                raise RedirectWarning(
                    msg,
                    self._get_records_action(),
                    _("Go to the company"),
                )

        if not self.l10n_ke_oscu_serial_number.upper().startswith('ODOO/' + self.vat.upper() + '/'):
            raise UserError(_('Your serial number should contain the PIN number and start: ODOO/%s/', self.vat))

    def action_l10n_ke_oscu_initialize(self):
        """ Initializing the device is necessary in order to receive the cmc key

        The cmc key is a token, necessary for all subsequent communication with the device.
        """
        self.ensure_one()
        self._l10n_ke_preinitialization_checks()
        content = {
            'tin':       self.vat,                         # VAT No
            'bhfId':     self.l10n_ke_branch_code,         # Branch ID
            'dvcSrlNo':  self.l10n_ke_oscu_serial_number,  # Device serial number
        }
        session = requests.Session()
        url = urljoin(self._l10n_ke_oscu_get_base_url(), 'selectInitOsdcInfo')
        _logger.debug("Calling OSCU initialization")
        try:
            response = session.post(url, json=content, timeout=30)
        except (ValueError, RequestException):
            raise UserError(_('Error connecting with the KRA.'))
        try:
            response_content = response.json()
        except JSONDecodeError:
            raise UserError(_('Error decoding response from KRA.'))
        _logger.debug("Response: %s", response_content)
        if response_content['resultCd'] != '000':
            if response_content['resultCd'] == '901':
                raise ValidationError(_('The registration failed.  Maybe you did not do the necessary steps with '
                                        'the KRA or the device has been registered before elsewhere and you can copy the CMC key and '
                                        'control unit id manually. '))
            raise ValidationError(
                _('Request Error Code: %(code)s, Message: %(msg)s',
                  code=response_content['resultCd'],
                  msg=response_content['resultMsg'])
            )
        if response_content['resultCd'] == '000':
            info = response_content['data']['info']
            self.l10n_ke_oscu_cmc_key = info['cmcKey']
            self.l10n_ke_control_unit = info['sdcId']

    def action_l10n_ke_get_items(self):
        """ Fetch all the products we've saved on eTIMS.
            We don't use this method, but must have it to demonstrate we are able to query their API.
        """
        last_request_date = self.env['ir.config_parameter'].get_param('l10n_ke_edi_oscu.last_fetch_items_request_date', '20180101000000')
        content = {'lastReqDt': last_request_date}
        error, data, _dummy = self._l10n_ke_call_etims('selectItemList', content)
        if error:
            raise UserError(error['message'])
        raise UserError(json.dumps(data, indent=4))

    def action_l10n_ke_get_stock_moves(self):
        """ Fetch all the stock moves we've saved on eTIMS.
            We don't use this method, but must have it to demonstrate we are able to query their API.
        """
        content = {
            'lastReqDt': '20180301000000',
        }
        error, data, _dummy = self._l10n_ke_call_etims('selectStockMoveList', content)
        if error:
            raise UserError(error['message'])
        raise UserError(json.dumps(data, indent=4))

    def action_l10n_ke_send_insurance(self):
        """ Send the company's insurance status to eTIMS.
            We don't use this method, but must have it to demonstrate we are able to query their API.
            It may be useful for companies that must mandatorily take an insurance policy (e.g. pharmacies)
        """
        content = {
            'isrccCd': self.l10n_ke_insurance_code,
            'isrccNm': self.l10n_ke_insurance_name,
            'isrcRt': self.l10n_ke_insurance_rate,
            'useYn': 'Y',
            **self._l10n_ke_get_user_dict(self.env.user, self.env.user),
        }
        error, _data, _dummy = self._l10n_ke_call_etims('saveBhfInsurance', content)
        if error:
            raise UserError(error['message'])
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'message': _("Insurance status successfully registered"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_l10n_ke_create_branches(self):
        """ Query eTIMS for saved company branches, then create those branches in Odoo. """
        content = {'lastReqDt': '20180101000000'}
        error, data, _dummy = self._l10n_ke_call_etims('selectBhfList', content)
        if error:
            raise UserError(error['message'])
        for bhf in data['bhfList']:
            if bhf['bhfId'] != self.l10n_ke_branch_code:
                company = self.search([('id', 'child_of', self.id), ('l10n_ke_branch_code', '=', bhf['bhfId'])], limit=1)
                if not company:
                    self.create({
                        'parent_id': self.id,
                        'name': bhf['bhfNm'],
                        'vat': bhf['tin'],
                        'l10n_ke_server_mode': self.l10n_ke_server_mode,
                        'l10n_ke_branch_code': bhf['bhfId'],
                        'state_id': self.env['res.country.state'].search([('country_id.code', '=', 'KE'), ('name', '=', bhf['prvncNm'])], limit=1).id,
                        'street': bhf['dstrtNm'],
                        'street2': bhf['sctrNm'],
                        'email': bhf['mgrEmail'],
                        'country_id': self.env.ref('base.ke').id,
                    })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'message': _("Branches successfully created"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    # === Helpers: calling eTIMS endpoints ===

    def _l10n_ke_oscu_get_base_url(self):
        """ Returns the base url for the OSCU API depending on whether the company is in test mode """
        return f"https://etims-api{'-sbx' if self.l10n_ke_server_mode == 'test' else ''}.kra.go.ke/etims-api/"

    def _l10n_ke_call_etims(self, urlext, content):
        """ Make a request to the OSCU

        :param string urlext: the extension of the url, represents the API endpoint to call.
        :param dict content:  represents the json content to be used in the request
        :returns: a tuple (dict errors, dict data, string result_date)
        """

        session = requests.Session()
        session.headers.update({
            'tin': self.vat,
            'bhfid': self.l10n_ke_branch_code,
            'cmcKey': self.sudo().l10n_ke_oscu_cmc_key,
        })
        url = urljoin(self._l10n_ke_oscu_get_base_url(), urlext)

        _logger.debug("Calling endpoint: %s", urlext)
        _logger.debug(content)

        try:
            if self.l10n_ke_server_mode != 'demo':
                response = session.post(url, json=content, timeout=120)  # Long timeout because eTIMS can often have congestion
            else:
                response = self._l10n_ke_get_demo_response(urlext, content)
            _logger.debug(response.text)
        except Timeout:
            msg = _("Timeout Error: KRA is currently unable to process your document. Please try again later. Thank you for your patience.")
            _logger.warning('Timeout when calling: %s', url)
            return {'code': 'TIM', 'message': msg}, {}, 'timeout_error'
        except (ValueError, RequestException) as e:
            _logger.warning('Connection error when calling: %s', url)
            return {'code': 'CON', 'message': _("Connection Error: %s\n", e)}, {}, 'connection_error'

        try:
            response_dict = response.json()
        except JSONDecodeError:
            return {'code': 'JSON', 'message': response.content}, {}, None

        if response_dict['resultCd'] == '000':
            return {}, response_dict['data'], response_dict['resultDt']
        else:
            return {'code': response_dict['resultCd'], 'message': response_dict['resultMsg']}, {}, response_dict['resultDt']

    @api.model
    def _l10n_ke_get_user_dict(self, create_user, write_user):
        return {
            'regrId': create_user.id,
            'regrNm': create_user.name,
            'modrId': write_user.id,
            'modrNm': write_user.name,
        }

    def _l10n_ke_get_demo_response(self, urlext, content):
        """ Get a mocked response in demo mode. """
        class Response:
            def __init__(self, content):
                self.content = content
                self.text = content.decode()

            def json(self):
                return json.loads(self.content)

        stock_services = (
            'insertStockIO',
            'saveStockMaster',
            'selectImportItemList',
            'selectItemList',
            'updateImportItem',
        )
        module = 'l10n_ke_edi_oscu_stock' if urlext in stock_services else 'l10n_ke_edi_oscu'

        response_files = {
            'insertTrnsPurchase': 'success',
            'insertStockIO': 'success',
            'saveBhfCustomer': 'success',
            'saveBhfInsurance': 'success',
            'saveBhfUser': 'success',
            'saveItem': 'success',
            'saveItemComposition': 'success',
            'saveStockMaster': 'success',
            'saveTrnsSalesOsdc': 'save_sale_success',
            'selectInvoiceDetails': 'get_invoice_details_success',
            'selectBhfList': 'get_branches',
            'selectCodeList': 'get_codes',
            'selectCustomer': 'get_customer',
            'selectImportItemList': 'get_imports_1',
            'selectItemClsList': 'get_unspsc_codes',
            'selectItemList': 'get_items',
            'selectNoticeList': 'get_notices',
            'selectStockMoveList': 'get_stock_moves',
            'selectTrnsPurchaseSalesList': 'get_purchases_1' if 'l10n_ke_oscu_last_fetch_customs_import_date' in self else 'get_purchases_2',
            'updateImportItem': 'success',
        }

        with file_open(f'{module}/tests/mocked_responses/{response_files[urlext]}.json', 'rb') as response_file:
            content = response_file.read()
        return Response(content)

    def _l10n_ke_find_for_cron(self, failed_action=''):
        company = self.env['res.company'].search(
            [
                ('l10n_ke_oscu_is_active', '=', True),
                ('l10n_ke_server_mode', '!=', 'demo'),
            ],
            limit=1,
        )
        if not company:
            _logger.warning("No OSCU initialized company could be found. %s", failed_action)

        return company


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_company_details(self):
        """The KRA requires that the VAT number appears in the header of the document."""
        company_details = super()._default_company_details()
        company = self.env.company
        if company.vat and company.l10n_ke_oscu_is_active:
            return company_details + Markup('<br/> %s') % _('KRA PIN: %s', company.vat)
        return company_details

    @api.model
    def _default_report_footer(self):
        if (company := self.env.company) and company.vat and company.l10n_ke_oscu_is_active:
            footer_fields = filter(None, [company.phone, company.email, company.website])
            return Markup(' ').join(footer_fields)
        return super()._default_report_footer()
