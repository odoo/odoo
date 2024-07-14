# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo.addons.iap.tools import iap_tools
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import is_html_empty

import time


OCR_VERSION = 132


class HrExpense(models.Model):
    _name = 'hr.expense'
    _inherit = ['extract.mixin', 'hr.expense']
    # We want to see the records that are just processed by OCR at the top of the list
    _order = "extract_state_processed desc, date desc, id desc"

    sample = fields.Boolean(help='Expenses created from sample receipt')

    def _needs_product_price_computation(self):
        # OVERRIDES 'hr_expense'
        self.ensure_one()
        is_extracted = self.extract_state in {'waiting_validation', 'to_validate', 'done'} and self.is_editable
        return self.product_has_cost and not is_extracted

    @api.depends('state')
    def _compute_is_in_extractable_state(self):
        for expense in self:
            expense.is_in_extractable_state = expense.state == 'draft' and not expense.sheet_id

    @api.model
    def _contact_iap_extract(self, pathinfo, params):
        params['version'] = OCR_VERSION
        params['account_token'] = self._get_iap_account().account_token
        endpoint = self.env['ir.config_parameter'].sudo().get_param('iap_extract_endpoint', 'https://extract.api.odoo.com')
        return iap_tools.iap_jsonrpc(endpoint + '/api/extract/expense/2/' + pathinfo, params=params)

    def _autosend_for_digitization(self):
        if self.env.company.expense_extract_show_ocr_option_selection == 'auto_send':
            self.filtered('extract_can_show_send_button')._send_batch_for_digitization()

    def _message_set_main_attachment_id(self, attachment_ids):
        super()._message_set_main_attachment_id(attachment_ids)
        self._autosend_for_digitization()

    def _get_validation(self, field):
        text_to_send = {}
        if field == "total":
            text_to_send["content"] = self.price_unit
        elif field == "date":
            text_to_send["content"] = str(self.date) if self.date else False
        elif field == "description":
            text_to_send["content"] = self.name
        elif field == "currency":
            text_to_send["content"] = self.currency_id.name
        return text_to_send

    def action_submit_expenses(self, **kwargs):
        res = super().action_submit_expenses(**kwargs)
        self._validate_ocr()
        return res

    def _fill_document_with_results(self, ocr_results, force_write=False):
        if ocr_results is not None:
            description_ocr = self._get_ocr_selected_value(ocr_results, 'description', "")
            total_ocr = self._get_ocr_selected_value(ocr_results, 'total', 0.0)
            date_ocr = self._get_ocr_selected_value(ocr_results, 'date', "")
            currency_ocr = self._get_ocr_selected_value(ocr_results, 'currency', "")

            self.state = 'draft'
            if description_ocr and not self.name or self.name == self.message_main_attachment_id.name.split('.')[0]:
                predicted_product_id = self._predict_product(description_ocr, category=True)
                if predicted_product_id:
                    self.product_id = predicted_product_id if predicted_product_id else self.product_id
                    self.total_amount_currency = total_ocr
            self.name = description_ocr
            # We need to set the name after the product change as changing the product may change the name
            self.predicted_category = description_ocr

            context_create_date = fields.Date.context_today(self, self.create_date)
            if date_ocr and not self.date or self.date == context_create_date:
                self.date = date_ocr

            if total_ocr and not self.total_amount_currency:
                self.total_amount_currency = total_ocr

            if currency_ocr and (not self.currency_id or self.currency_id == self.env.company.currency_id):
                for comparison in ['=ilike', 'ilike']:
                    possible_currencies = self.env["res.currency"].search([
                        '|', '|',
                        ('currency_unit_label', comparison, currency_ocr),
                        ('name', comparison, currency_ocr),
                        ('symbol', comparison, currency_ocr),
                    ])
                    if len(possible_currencies) == 1:
                        self.currency_id = possible_currencies
                        break

    @api.model
    def get_empty_list_help(self, help_message):
        if self.env.user.has_group('hr_expense.group_hr_expense_manager'):
            expenses = self.search_count([
                ('employee_id', 'in', self.env.user.employee_ids.ids),
                ('state', 'in', ['draft', 'reported', 'approved', 'done', 'refused'])
            ])
            if is_html_empty(help_message):
                help_message = Markup(_("""
<p class="o_view_nocontent_expense_receipt">
    <h2 class="d-none d-md-block">
        Drag and drop files to create expenses
    </h2>
    <p>
        Or
    </p>
    <h2 class="d-none d-md-block">
        Did you try the mobile app?
    </h2>
</p>
<p>Snap pictures of your receipts and let Odoo<br/> automatically create expenses for you.</p>
<p class="d-none d-md-block">
    <a href="https://apps.apple.com/be/app/odoo/id1272543640" target="_blank" class="o_expense_mobile_app">
        <img alt="Apple App Store" class="img img-fluid h-100 o_expense_apple_store" src="/hr_expense/static/img/app_store.png"/>
    </a>
    <a href="https://play.google.com/store/apps/details?id=com.odoo.mobile" target="_blank" class="o_expense_mobile_app">
        <img alt="Google Play Store" class="img img-fluid h-100 o_expense_google_store" src="/hr_expense/static/img/play_store.png"/>
    </a>
</p>"""))
            # add hint for extract if not already present and user might now have already used it
            extract_txt = _("Try Sample Receipt")
            if not expenses and extract_txt not in help_message:
                action_id = self.env.ref('hr_expense_extract.action_expense_sample_receipt').id
                help_message += Markup(
                    """<p><a type="action" name="%(action_id)s" class="btn btn-primary text-white">%(extract_txt)s</a></p>"""
                ) % {
                    'action_id': action_id,
                    'extract_txt': extract_txt,
                }

        return super().get_empty_list_help(help_message)

    def _get_ocr_module_name(self):
        return 'hr_expense_extract'

    def _get_ocr_option_can_extract(self):
        ocr_option = self.env.company.expense_extract_show_ocr_option_selection
        return ocr_option and ocr_option != 'no_send'

    def _get_validation_fields(self):
        return ['total', 'date', 'description', 'currency']

    def _get_user_error_invalid_state_message(self):
        return _("You cannot send a expense that is not in draft state!")

    def _upload_to_extract_success_callback(self):
        super()._upload_to_extract_success_callback()
        if 'isMobile' in self.env.context and self.env.context['isMobile']:
            for record in self:
                timer = 0
                while record.extract_state != 'waiting_validation' and timer < 10:
                    timer += 1
                    time.sleep(1)
                    record._check_ocr_status()


class HrExpenseSheet(models.Model):
    _inherit = ['hr.expense.sheet']

    def _is_expense_sample(self):
        samples = set(self.mapped('expense_line_ids.sample'))
        if len(samples) > 1:
            raise UserError(_("You can't mix sample expenses and regular ones"))
        return samples and samples.pop() # True / False

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted_or_paid(self):
        super(HrExpenseSheet, self.filtered(lambda exp: not exp._is_expense_sample()))._unlink_except_posted_or_paid()

    def action_register_payment(self):
        if self._is_expense_sample():
            # using the real wizard is not possible as it check
            # lots of stuffs on the account.move.line
            action = self.env['ir.actions.actions']._for_xml_id('hr_expense_extract.action_expense_sample_register')
            action['context'] = {'active_id': self.id}
            return action

        return super().action_register_payment()

    def action_sheet_move_create(self):
        if self._is_expense_sample():
            self.set_to_posted()
            if self.payment_mode == 'company_account':
                self.set_to_paid()
            return

        return super().action_sheet_move_create()
