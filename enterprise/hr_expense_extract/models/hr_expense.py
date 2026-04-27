# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo.addons.iap.tools import iap_tools
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import is_html_empty
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

import time


OCR_VERSION = 133


class HrExpense(models.Model):
    _name = 'hr.expense'
    _inherit = ['extract.mixin', 'hr.expense']
    # We want to see the records that are just processed by OCR at the top of the list
    _order = "extract_state_processed desc, date desc, id desc"

    sample = fields.Boolean(help='Expenses created from sample receipt')

    @api.depends('state')
    def _compute_is_in_extractable_state(self):
        for expense in self:
            expense.is_in_extractable_state = expense.state == 'draft' and not expense.sheet_id

    @api.depends('extract_state', 'state')
    def _compute_extract_state_processed(self):
        # Overrides 'iap_extract'
        for expense in self:
            expense.extract_state_processed = expense.extract_state == 'waiting_extraction' and expense.state == 'draft'

    @api.model
    def _contact_iap_extract(self, pathinfo, params):
        params['version'] = OCR_VERSION
        params['account_token'] = self._get_iap_account().account_token
        endpoint = self.env['ir.config_parameter'].sudo().get_param('iap_extract_endpoint', 'https://extract.api.odoo.com')
        return iap_tools.iap_jsonrpc(endpoint + '/api/extract/expense/2/' + pathinfo, params=params)

    def _autosend_for_digitization(self):
        if self.env.company.expense_extract_show_ocr_option_selection == 'auto_send':
            self.filtered('extract_can_show_send_button')._send_batch_for_digitization()

    def _message_set_main_attachment_id(self, attachments, force=False, filter_xml=True):
        super()._message_set_main_attachment_id(attachments, force=force, filter_xml=filter_xml)
        if not self.sample:
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

    def _fill_document_with_results(self, ocr_results):
        if ocr_results is not None:
            vals = {'state': 'draft'}

            description_ocr = self._get_ocr_selected_value(ocr_results, 'description', "")
            total_ocr = self._get_ocr_selected_value(ocr_results, 'total', 0.0)
            date_ocr = self._get_ocr_selected_value(ocr_results, 'date', fields.Date.context_today(self).strftime(DEFAULT_SERVER_DATE_FORMAT))
            currency_ocr = self._get_ocr_selected_value(ocr_results, 'currency', self.env.company.currency_id.name)

            if description_ocr and not self.name or self.name == '.'.join(self.message_main_attachment_id.name.split('.')[:-1]):
                predicted_product_id = self._predict_product(description_ocr)
                if predicted_product_id:
                    vals['product_id'] = predicted_product_id or self.product_id.id
                vals['name'] = description_ocr

            context_create_date = fields.Date.context_today(self, self.create_date)
            if not self.date or self.date == context_create_date:
                vals['date'] = date_ocr

            product_id = vals.get('product_id', self.product_id.id)
            product_price = product_id and self.env['product.product'].with_company(self.company_id).browse(product_id).standard_price
            if product_price:
                vals['price_unit'] = product_price
                vals['total_amount_currency'] = product_price
                vals['total_amount'] = product_price
            else:
                vals['total_amount_currency'] = total_ocr
                vals['quantity'] = 1  # Always the case for expense that are not using a flat rate
                vals['price_unit'] = total_ocr
                current_currency = self.currency_id
                if not self.currency_id or self.currency_id == self.env.company.currency_id:
                    for comparison in ['=ilike', 'ilike']:
                        matched_currency = self.env["res.currency"].with_context(active_test=False).search([
                            '|', '|',
                            ('currency_unit_label', comparison, currency_ocr),
                            ('name', comparison, currency_ocr),
                            ('symbol', comparison, currency_ocr),
                        ])
                        if len(matched_currency) == 1:
                            current_currency = matched_currency

                vals['currency_id'] = current_currency.id
                if current_currency and current_currency != self.company_currency_id:
                    vals['total_amount'] = current_currency._convert(
                        total_ocr,
                        self.company_currency_id,
                        company=self.company_id,
                        date=vals.get('date', self.date),
                    )
                else:
                    vals['total_amount'] = total_ocr

            self.write(vals)

    @api.model
    def get_empty_list_help(self, help_message):
        if self.env.user.has_group('base.group_user'):
            expenses = self.search_count([
                ('employee_id', 'in', self.env.user.employee_ids.ids),
                ('state', 'in', ['draft', 'reported', 'approved', 'done', 'refused'])
            ])
            if is_html_empty(help_message):
                help_message = Markup("""
                    <p class="o_view_nocontent_expense_receipt">
                        <div class="o_view_pink_overlay">
                            <p class="o_view_nocontent_expense_receipt_image"/>
                            <h2 class="d-md-block">
                                {title}
                            </h2>
                        </div>
                    </p>""").format(title=_("Upload or drop an expense receipt"))
            # add hint for extract if not already present and user might now have already used it
            extract_txt = _("try a sample receipt")
            if not expenses and extract_txt not in help_message:
                action_id = self.env.ref('hr_expense_extract.action_expense_sample_receipt').id
                help_message += Markup(
                    "<p class='text-muted mt-4'>Or <a type='action' name='%(action_id)s' class='o_select_sample'>%(extract_txt)s</a></p>"
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

    def _do_approve(self):
        # If we're dealing with sample expenses (demo data) then we should NEVER create any account.move
        if self._is_expense_sample():
            sheets_to_approve = self.filtered(lambda s: s.state in {'submit', 'draft'})
            for sheet in sheets_to_approve:
                sheet.write(
                    {
                        'approval_state': 'approve',
                        'user_id': sheet.user_id.id or self.env.user.id,
                        'approval_date': fields.Date.context_today(sheet),
                    }
                )
            self.activity_update()
            return
        return super()._do_approve()

    def action_sheet_move_post(self):
        if self._is_expense_sample():
            self.set_to_posted()
            if self.payment_mode == 'company_account':
                self.set_to_paid()
            return

        return super().action_sheet_move_post()


class HrExpenseSplit(models.TransientModel):
    _inherit = ['hr.expense.split']

    def _get_values(self):
        self.ensure_one()
        vals = super()._get_values()
        vals['extract_state'] = 'done'  # Marking the state as done will disable the OCR on the split expenses
        return vals
