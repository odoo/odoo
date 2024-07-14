# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import requests
import logging
import datetime
from re import match
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

_logger = logging.getLogger(__name__)

class HmrcVatObligation(models.Model):
    """ VAT obligations retrieved from HMRC """

    _name = 'l10n_uk.vat.obligation'
    _description = 'HMRC VAT Obligation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'date_due'
    _order = 'date_due'

    # fields retrieved from HMRC
    date_start = fields.Date('Period Start', readonly=True)
    date_end = fields.Date('Period End', readonly=True)
    date_due = fields.Date('Period Due', readonly=True)
    status = fields.Selection([('open', 'Open'), ('fulfilled', 'Fulfilled')], string='Period Status', readonly=True)
    period_key = fields.Char('Period Key', readonly=True)
    date_received = fields.Date('Received Submission date', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', required=True,
        default=lambda self: self.env.company)

    @api.depends('date_due', 'date_start', 'date_end')
    def _compute_display_name(self):
        for o in self:
            o.display_name = f"{o.date_due} ({o.date_start} - {o.date_end})"

    @api.model
    def _get_auth_headers(self, bearer, client_data=None):
        headers = {
            'Accept': 'application/vnd.hmrc.1.0+json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % bearer,
            **self.env['hmrc.service']._get_fraud_prevention_info(client_data),
        }
        return headers

    @api.model
    def retrieve_vat_obligations(self, vat, from_date, to_date, status=''):
        """ Retrieve vat obligations

        The User should be logged in before doing this
        :param vat:
        :param from_date:
        :param to_date:
        :param status:
        :return: list of obligations of the status type for the requested period
        """
        if not match(r'^[0-9]{9}$', vat or ''):
            raise UserError(_("VAT numbers of UK companies should have exactly 9 figures or 11 with the GB or XI prefix. Please check the settings of the current company."))

        user = self.env.user
        bearer = user.l10n_uk_hmrc_vat_token
        headers = self._get_auth_headers(bearer)

        url = self.env['hmrc.service']._get_endpoint_url('/organisations/vat/%s/obligations' % vat)
        params = {
            'from': from_date,
            'to': to_date,
        }
        if status:
            status = 'O' if status == 'open' else 'F'
            params.update({'status': status})
        resp = requests.get(url, headers=headers, params=params)
        response = json.loads(resp.content.decode())
        if resp.status_code == 200:
            # Create obligations
            return response.get('obligations')

        # Show a nice error when something goes wrong
        error_code = response.get('code')
        if error_code == 'VRN_INVALID':
            error_message = _('Invalid Company VAT number. Please fill in the correct VAT on the company form. ')
        elif error_code in ('INVALID_DATE_FROM', 'INVALID_DATE_TO', 'INVALID_DATE_RANGE'):
            error_message = _('Issue with the selected dates.')
        elif error_code == 'INVALID_STATUS':
            error_message = _('Invalid Status.')
        elif error_code == 'NOT_FOUND':
            error_message = _('No open obligations were found for the moment.')
        elif error_code == 'CLIENT_OR_AGENT_NOT_AUTHORISED':
            # In case one user needs to submit the report for two companies, they will need to re-login.
            self.env['hmrc.service'].sudo()._clean_tokens()
            return []
        else:
            error_message = response.get('message', error_code)
        raise UserError(error_message)

    def _get_vat(self):
        # Use company's VAT if company is British, otherwise try to look for a UK fiscal position.
        foreign_vat = False
        if not self.env.company.country_id.code == 'GB':
            foreign_vat = self.env.company.fiscal_position_ids.filtered(lambda fp: fp.country_id.code == 'GB').foreign_vat

        vat = foreign_vat or self.env.company.vat

        # The VAT sent to HMRC should not include the GB or XI prefix.
        if vat.startswith(('GB', 'XI')):
            vat = vat[2:]

        return vat

    def import_vat_obligations(self):
        today = datetime.date.today()
        res = self.env['hmrc.service']._login()
        if res: # If you can not login, return url for re-login
            return res

        # look for open obligations in the -6 months +6 months range
        obligations = self.retrieve_vat_obligations(
            self._get_vat(),
            (today + relativedelta(months=-6)).strftime('%Y-%m-%d'),
            (today + relativedelta(months=6,leapdays=-1)).strftime('%Y-%m-%d'))

        for new_obligation in obligations:
            obligation = self.env['l10n_uk.vat.obligation'].search([('period_key', '=', new_obligation.get('periodKey')),
                                                                 ('company_id', '=', self.env.company.id)])
            status = 'open' if new_obligation['status'] == 'O' else 'fulfilled'
            if not obligation:
                self.sudo().create({'date_start': new_obligation['start'],
                                    'date_end': new_obligation['end'],
                                    'date_received': new_obligation.get('received'),
                                    'date_due': new_obligation['due'],
                                    'status': status,
                                    'period_key': new_obligation['periodKey'],
                                    'company_id': self.env.company.id,
                                    })
            elif obligation.status != status or obligation.date_received != new_obligation.get('received'):
                obligation.sudo().write({'status': status,
                                         'date_received': new_obligation.get('received')})

    def _fetch_values_from_report(self, lines):
        translation_table = {
            'vatDueSales': 'account_tax_report_line_vat_box1',
            'vatDueAcquisitions': 'account_tax_report_line_vat_box2',
            'totalVatDue': 'account_tax_report_line_vat_box3',
            'vatReclaimedCurrPeriod': 'account_tax_report_line_vat_box4',
            'netVatDue': 'account_tax_report_line_vat_box5',
            'totalValueSalesExVAT': 'account_tax_report_line_exd_vat_box6',
            'totalValuePurchasesExVAT': 'account_tax_report_line_exd_vat_box7',
            'totalValueGoodsSuppliedExVAT': 'account_tax_report_line_exd_vat_box8',
            'totalAcquisitionsExVAT': 'account_tax_report_line_exd_vat_box9',
        }
        reverse_table = {}
        for line_xml_id in translation_table:
            uk_report_id = self.env.ref('l10n_uk.' + translation_table[line_xml_id])
            reverse_table[uk_report_id.id] = line_xml_id

        values = {}
        for line in lines:
            line_id = self.env['account.report']._parse_line_id(line['id'])[-1][-1]
            if reverse_table.get(line_id):
                # Do a get for the no_format as for the totals you have twice the line, without and with amount
                # We cannot pass a negative netVatDue to the API and the amounts of sales/purchases/goodssupplied/ ... must be rounded
                if reverse_table[line_id] == 'netVatDue':
                    values[reverse_table[line_id]] = abs(round(line['columns'][0].get('no_format', 0.0), 2))
                elif reverse_table[line_id] in ('totalValueSalesExVAT', 'totalValuePurchasesExVAT', 'totalValueGoodsSuppliedExVAT', 'totalAcquisitionsExVAT'):
                    values[reverse_table[line_id]] = round(line['columns'][0].get('no_format', 0.0))
                else:
                    values[reverse_table[line_id]] = round(line['columns'][0].get('no_format', 0.0), 2)
        return values

    def action_submit_vat_return(self, data=None):
        self.ensure_one()
        report = self.env.ref('l10n_uk.tax_report')
        options = report.get_options()
        options['date'].update({'date_from': fields.Date.to_string(self.date_start),
                        'date_to': fields.Date.to_string(self.date_end),
                        'filter': 'custom',
                        'mode': 'range'})
        report_values = report._get_lines(options)
        values = self._fetch_values_from_report(report_values)
        vat = self._get_vat()
        res = self.env['hmrc.service']._login()
        if res: # If you can not login, return url for re-login
            return res
        headers = self._get_auth_headers(self.env.user.l10n_uk_hmrc_vat_token, data)

        url = self.env['hmrc.service']._get_endpoint_url('/organisations/vat/%s/returns' % vat)
        data = values.copy()
        data.update({
         'periodKey': self.period_key,
         'finalised': True
        })

        # Need to check with which credentials it needs to be done
        r = requests.post(url, headers=headers, data=json.dumps(data))
        # Need to do something with the result?
        if r.status_code == 201: #Successful post
            response = json.loads(r.content.decode())
            msg = _('Tax return successfully posted:') + Markup(' <br/>')
            msg += Markup('<b>%s : </b>%s<br/>') % (_('Date Processed'), response['processingDate'])
            if response.get('paymentIndicator'):
                msg += Markup('<b>%s : </b>%s<br/>') % (_('Payment Indicator'), response['paymentIndicator'])
            msg += Markup('<b>%s : </b>%s<br/>') % (_('Form Bundle Number'), response['formBundleNumber'])
            if response.get('chargeRefNumber'):
                msg += Markup('<b>%s : </b>%s<br/>') % (_('Charge Ref Number'), response['chargeRefNumber'])
            msg += Markup('<br/>%s<br/>') % _('Sent Values:')
            for sent_key in data:
                if sent_key != 'periodKey':
                    msg += Markup('<b>%s</b>: %s</br>') % (sent_key, data[sent_key])
            self.sudo().message_post(body=msg)
            self.sudo().write({'status': "fulfilled"})

            # Show a confirmation popup.
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'success',
                'message': _("The VAT report has been successfully submitted to HMRC."),
            })
        elif r.status_code == 401:  # auth issue
            _logger.exception("HMRC auth issue : %s", r.content)
            raise UserError(_(
             "Sorry, your credentials were refused by HMRC or your permission grant has expired. You may try to authenticate again."))
        else:  # other issues
            _logger.exception("HMRC other issue : %s", r.content)
            # even 'normal' hmrc errors have a json body. Otherwise will also raise.
            response = json.loads(r.content.decode())
            # Recuperate error message
            if response.get('errors'):
                msgs = ""
                for err in response['errors']:
                    msgs += err.get('message', '')
            else:
                msgs = response.get('message') or response
            raise UserError(_("Sorry, something went wrong: %s", msgs))
