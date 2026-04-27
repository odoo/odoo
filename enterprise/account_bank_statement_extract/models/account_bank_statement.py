from odoo import api, fields, models, Command, _
from odoo.addons.iap.tools import iap_tools

OCR_VERSION = 100


class AccountBankStatement(models.Model):
    _name = 'account.bank.statement'
    _inherit = ['extract.mixin', 'account.bank.statement']

    @api.depends('line_ids')
    def _compute_is_in_extractable_state(self):
        self.is_in_extractable_state = not self.line_ids

    def _compute_journal_id(self):
        if self.line_ids:
            super()._compute_journal_id()

    def _get_ocr_option_can_extract(self):
        ocr_option = self.env.company.extract_bank_statement_digitalization_mode
        return ocr_option and ocr_option != 'no_send'

    def _get_ocr_module_name(self):
        return 'account_bank_statement_extract'

    def _get_user_infos(self):
        user_infos = super()._get_user_infos()
        user_infos['journal_type'] = self.journal_id.type
        return user_infos

    def _contact_iap_extract(self, pathinfo, params):
        params['version'] = OCR_VERSION
        params['account_token'] = self._get_iap_account().account_token
        endpoint = self.env['ir.config_parameter'].sudo().get_param('iap_extract_endpoint', 'https://extract.api.odoo.com')
        return iap_tools.iap_jsonrpc(endpoint + '/api/extract/bank_statement/1/' + pathinfo, params=params)

    def _fill_document_with_results(self, ocr_results):
        self.ensure_one()
        balance_start_ocr = self._get_ocr_selected_value(ocr_results, 'balance_start', 0.0)
        balance_end_ocr = self._get_ocr_selected_value(ocr_results, 'balance_end', 0.0)
        date_ocr = self._get_ocr_selected_value(ocr_results, 'date', "")
        lines_ocr = ocr_results.get('bank_statement_lines', [])

        self.balance_start = balance_start_ocr
        self.balance_end = balance_end_ocr
        self.date = date_ocr
        self._compute_name()
        self.line_ids = [Command.create({
            'amount': line['amount'],
            'date': line['date'],
            'journal_id': self.journal_id.id,
            'payment_ref': line['description'],
        }) for line in lines_ocr]

        odoobot = self.env.ref('base.partner_root')
        self.message_post(
            body=_("Statement and transactions have been updated using Artificial Intelligence."),
            author_id=odoobot.id
        )

        self.env.ref('account_accountant.auto_reconcile_bank_statement_line')._trigger()

    def _message_set_main_attachment_id(self, attachments, force=False, filter_xml=True):
        res = super()._message_set_main_attachment_id(attachments, force=force, filter_xml=filter_xml)
        self._autosend_for_digitization()
        return res

    def _autosend_for_digitization(self):
        if self.env.company.extract_bank_statement_digitalization_mode == 'auto_send':
            self.filtered('extract_can_show_send_button')._send_batch_for_digitization()
