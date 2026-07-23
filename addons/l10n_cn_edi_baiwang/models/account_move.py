# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

from .baiwang_client import BaiwangClient
from odoo.addons.phone_validation.tools.phone_validation import phone_format

INVOICE_TYPE_CODES = [
    ('01', '01 Digital Special Invoice (全电专票)'),
    ('02', '02 Digital General Invoice (全电普票)'),
]

RED_FORM_TYPES = [
    ('01', '01 Invoice Error (开票有误)'),
    ('02', '02 Sales Return (销货退回)'),
    ('03', '03 Service Termination (服务中止)'),
    ('04', '04 Sales Discount (销售折让)'),
]

BAIWANG_STATES = [
    ('not_sent', 'Not Sent'),
    ('sent', 'Sent'),
    ('issued', 'Issued'),
    ('failed', 'Failed'),
]


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_cn_baiwang_state = fields.Selection(
        selection=BAIWANG_STATES,
        default='not_sent',
        string="Baiwang Status",
        copy=False,
    )
    l10n_cn_baiwang_invoice_type_code = fields.Selection(
        selection=INVOICE_TYPE_CODES,
        string="Fapiao Type",
        default='02',
        required=True,
        help="Type of e-Fapiao to issue: '01' for special (专票) or '02' for general (普票).",
    )
    l10n_cn_baiwang_invoice_no = fields.Char(string="Fapiao No.", copy=False)
    l10n_cn_baiwang_invoice_date = fields.Datetime(string="Fapiao Date", copy=False)
    l10n_cn_baiwang_serial_no = fields.Char(string="Serial No", copy=False, readonly=True, help="Unique request serial number for idempotency")
    l10n_cn_baiwang_qr_code = fields.Char(string="Invoice QR Code", copy=False, readonly=True)
    l10n_cn_baiwang_red_form_type = fields.Selection(
        selection=RED_FORM_TYPES,
        string="Red Form Reason",
        compute="_compute_l10n_cn_baiwang_red_form_type",
        store=True,
        readonly=False,
    )
    l10n_cn_edi_document_ids = fields.One2many(
        'l10n_cn_edi.document',
        'move_id',
        string="Baiwang EDI Documents",
    )

    # Computed
    l10n_cn_baiwang_is_needed = fields.Boolean(compute='_compute_l10n_cn_baiwang_is_needed')
    l10n_cn_baiwang_red_form_required = fields.Boolean(
        compute='_compute_l10n_cn_baiwang_red_form_required',
    )
    l10n_cn_baiwang_date_consistency_warning = fields.Char(
        string="Date Consistency Warning",
        compute='_compute_l10n_cn_baiwang_date_consistency_warning',
    )

    l10n_cn_buyer_bank_id = fields.Many2one(
        comodel_name='res.partner.bank',
        string="Customer Bank Account",
        compute='_compute_l10n_cn_buyer_bank_id',
        store=True,
        readonly=False,
        domain="[('partner_id', '=', partner_id)]",
        help="The customer's bank account to be printed on the Chinese Baiwang E-Fapiao.",
    )
    l10n_cn_baiwang_red_form_uuid = fields.Char(
        string="Red Form UUID",
        compute='_compute_l10n_cn_baiwang_latest_edi_data',
        compute_sudo=True,
    )
    l10n_cn_baiwang_red_form_number = fields.Char(
        string="Red Form Number",
        compute='_compute_l10n_cn_baiwang_latest_edi_data',
        compute_sudo=True,
    )
    l10n_cn_baiwang_red_form_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('red_form_pending', 'Red Form Pending'),
            ('red_form_confirmed', 'Red Form Confirmed'),
            ('failed', 'Failed'),
        ],
        string="Red Form Status",
        compute='_compute_l10n_cn_baiwang_latest_edi_data',
        compute_sudo=True,
    )
    l10n_cn_baiwang_red_form_amount_total = fields.Float(
        string="Inbound Credit Price",
        compute='_compute_l10n_cn_baiwang_latest_edi_data',
        compute_sudo=True,
    )
    l10n_cn_baiwang_red_form_amount_tax = fields.Float(
        string="Inbound Credit Tax",
        compute='_compute_l10n_cn_baiwang_latest_edi_data',
        compute_sudo=True,
    )

    @api.depends('l10n_cn_baiwang_red_form_required', 'l10n_cn_baiwang_red_form_status')
    def _compute_hide_post_button(self):
        super()._compute_hide_post_button()
        for move in self:
            if move.l10n_cn_baiwang_red_form_required and move.l10n_cn_baiwang_red_form_status != 'red_form_confirmed':
                move.hide_post_button = True

    def button_cancel(self):
        for move in self:
            if move.l10n_cn_baiwang_state in ('sent', 'issued'):
                raise UserError(self.env._("You cannot cancel a document that is pending or already issued in Baiwang."))
        return super().button_cancel()

    def button_draft(self):
        if any(move.l10n_cn_baiwang_state in ('sent', 'issued') for move in self):
            raise UserError(self.env._(
                "You cannot reset this invoice to draft because it has already been sent to Baiwang. "
                "You must issue a Red Form (Credit Note) to reverse it.",
            ))
        return super().button_draft()

    def action_cancel_baiwang_red_form(self):
        """Cancel a pending Red Form request."""
        for move in self:
            latest_doc = move.l10n_cn_edi_document_ids.sorted('create_date', reverse=True)[:1]
            if not latest_doc or latest_doc.state != 'red_form_pending':
                continue
            client = BaiwangClient(move.company_id)
            try:
                client.operate_red_confirmation(
                    red_confirm_uuid=latest_doc.baiwang_uuid,
                    red_confirm_no=latest_doc.baiwang_red_form_number,
                    confirm_type='03',  # Revoke
                )
            except UserError as e:
                raise UserError(self.env._("Failed to revoke Red Form on Baiwang: %s", e))
            latest_doc.write({
                'state': 'failed',
                'error_message': self.env._("Revoked and cancelled by user."),
            })
            move.write({'l10n_cn_baiwang_red_form_type': False})
            move.message_post(body=self.env._("Red Form request revoked on Baiwang and cancelled by user. You may request a new one."))

    # ─── Computed Methods ───────────────────────────────────────────────

    @api.depends('country_code', 'move_type', 'state', 'l10n_cn_baiwang_state')
    def _compute_l10n_cn_baiwang_is_needed(self):
        for move in self:
            move.l10n_cn_baiwang_is_needed = (
                move.country_code == 'CN'
                and move.move_type in ('out_invoice', 'out_refund')
                and move.state == 'posted'
                and move.l10n_cn_baiwang_state not in ('issued', 'sent')
            )

    @api.depends('country_code', 'move_type', 'state', 'reversed_entry_id.l10n_cn_baiwang_invoice_no')
    def _compute_l10n_cn_baiwang_red_form_required(self):
        for move in self:
            move.l10n_cn_baiwang_red_form_required = bool(
                move.country_code == 'CN'
                and move.move_type == 'out_refund'
                and move.state == 'draft'
                and move.reversed_entry_id
                and move.reversed_entry_id.l10n_cn_baiwang_invoice_no,
            )

    @api.depends('invoice_date', 'l10n_cn_baiwang_invoice_date', 'l10n_cn_baiwang_invoice_no', 'state', 'move_type')
    def _compute_l10n_cn_baiwang_date_consistency_warning(self):
        warning_msg = self.env._(
            "Invoice Date is different from Fapiao Date. Please be aware of the consistency between E-fapiao Date and Odoo Invoice Date.",
        )
        for move in self:
            move.l10n_cn_baiwang_date_consistency_warning = False
            if (
                move.move_type == 'out_refund'
                and move.state == 'draft'
                and move.l10n_cn_baiwang_invoice_no
                and move.invoice_date
                and move.l10n_cn_baiwang_invoice_date
            ):
                fapiao_date = False
                if hasattr(move.l10n_cn_baiwang_invoice_date, 'date'):
                    fapiao_date = move.l10n_cn_baiwang_invoice_date.date()
                elif isinstance(move.l10n_cn_baiwang_invoice_date, str):
                    clean_str = move.l10n_cn_baiwang_invoice_date.replace('-', '')[:8]
                    if len(clean_str) == 8 and clean_str.isdigit():
                        fapiao_date = fields.Date.to_date(f"{clean_str[:4]}-{clean_str[4:6]}-{clean_str[6:8]}")

                if fapiao_date and move.invoice_date != fapiao_date:
                    move.l10n_cn_baiwang_date_consistency_warning = warning_msg

    @api.depends('partner_id')
    def _compute_l10n_cn_buyer_bank_id(self):
        for move in self:
            if move.partner_id and move.partner_id.bank_ids:
                move.l10n_cn_buyer_bank_id = move.partner_id.bank_ids[0]
            else:
                move.l10n_cn_buyer_bank_id = False

    # ─── Blue Invoice Issuance ──────────────────────────────────────────

    def _l10n_cn_baiwang_issue_invoice(self):
        """Issue a blue (positive) e-Fapiao via Baiwang for customer invoices."""
        self.ensure_one()
        company = self.company_id
        if company.l10n_cn_baiwang_subscription_status != 'authorized':
            raise UserError(self.env._("Baiwang is not authorized. Please go to Settings."))
        client = BaiwangClient(company)
        try:
            client.ensure_connection()
        except UserError as e:
            return str(e)
        serial_no = self.l10n_cn_baiwang_serial_no or f"OURBLUE_{self.id}_{fields.Datetime.now():%Y%m%d%H%M%S}"
        self.l10n_cn_baiwang_serial_no = serial_no
        invoice_data = self._l10n_cn_baiwang_prepare_invoice_data(serial_no)
        try:
            result = client.issue_invoice(invoice_data)
        except UserError as e:
            # Avoid marking as failed for connectivity/precondition errors; user can retry.
            return str(e)
        except (TypeError, ValueError) as e:
            error_msg = str(e)
            self.write({'l10n_cn_baiwang_state': 'failed'})
            self.message_post(body=error_msg)
            return error_msg

        if result.get('success'):
            success_list = result.get('response', {}).get('success', [])
            if success_list:
                invoice_resp = success_list[0]
                raw_date = invoice_resp.get('invoiceDate')
                invoice_date = (datetime.strptime(raw_date, '%Y%m%d%H%M%S') - timedelta(hours=8)) if raw_date else False
                self.write({
                    'l10n_cn_baiwang_state': 'issued',
                    'l10n_cn_baiwang_invoice_no': invoice_resp.get('invoiceNo'),
                    'l10n_cn_baiwang_invoice_date': invoice_date,
                    'l10n_cn_baiwang_qr_code': invoice_resp.get('invoiceQrCode'),
                })
                self.message_post(body=self.env._(
                    "E-Fapiao issued successfully. Invoice No: %(no)s",
                    no=invoice_resp.get('invoiceNo'),
                ))
                return None
            # Success response but no data
            fail_list = result.get('response', {}).get('fail', [])
            if fail_list:
                error_msg = fail_list[0].get('failCause', 'Unknown error')
            else:
                error_msg = self.env._("Unexpected response format from Baiwang")
        else:
            err = result.get('errorResponse', {})
            error_msg = f"[{err.get('subCode', err.get('code', ''))}] {err.get('subMessage', err.get('message', 'Unknown error'))}"

        self.write({'l10n_cn_baiwang_state': 'failed'})
        self.message_post(body=error_msg)
        return error_msg

    def _l10n_cn_baiwang_prepare_invoice_data(self, serial_no: str) -> dict:
        """Map Odoo invoice data to Baiwang invoice.issue request format."""
        self.ensure_one()
        # Calculate totals (always tax-exclusive)
        total_price = sum(
            line.price_subtotal
            for line in self.invoice_line_ids
            if line.display_type == 'product'
        )
        total_tax = self.amount_tax
        total_price_tax = self.amount_total
        invoice_data = {
            'invoiceType': '0',  # 0=blue (positive), 1=red (negative)
            'invoiceTypeCode': self.l10n_cn_baiwang_invoice_type_code or '02',
            'priceTaxMark': '0',  # 0=prices exclude tax
            'invoiceListMark': '0',  # 0=no list attachment
            'taxationMethod': '0',  # 0=general taxation
            'serialNo': serial_no,
            'buyerName': self.partner_id.name or '',
            'buyerTaxNo': self.partner_id.vat or '',
            'invoiceTotalPrice': round(total_price, 2),
            'invoiceTotalTax': round(total_tax, 2),
            'invoiceTotalPriceTax': round(total_price_tax, 2),
            'invoiceDetailsList': self._l10n_cn_baiwang_prepare_lines(),
        }
        if self.partner_id.street:
            buyer_address = ' '.join(filter(None, [
                self.partner_id.street,
                self.partner_id.street2,
                self.partner_id.city,
            ]))
            invoice_data['buyerAddress'] = buyer_address
        if self.narration:
            invoice_data['remark'] = str(self.narration)
        if self.partner_id.phone:
            partner = self.partner_id
            formatted_phone = phone_format(
                partner.phone,
                partner.country_id.code,
                partner.country_id.phone_code,
                force_format='E164',
                raise_exception=False,
            ) or ''

            # If phonenumbers successfully parsed it as a Chinese number, it will start with +86
            if formatted_phone.startswith('+86'):
                invoice_data['buyerPhone'] = formatted_phone[3:]
            else:
                remark = invoice_data.get('remark', '')
                invoice_data['remark'] = f"{remark} | Phone: {partner.phone}".strip(' |')
        if self.partner_id.email:
            invoice_data['buyerEmail'] = self.partner_id.email
        if self.l10n_cn_buyer_bank_id:
            # Fapiao prints these on a single line ("开户行及账号").
            # Baiwang API silently overwrote buyerBankName with buyerBankAccount because it expects the combined string there.
            invoice_data['buyerBankName'] = f"{self.l10n_cn_buyer_bank_id.bank_name or ''} {self.l10n_cn_buyer_bank_id.account_number or ''}".strip()
        invoice_data['drawer'] = self.env.user.name
        invoice_data['buyerNaturalPerson'] = 'Y' if not self.partner_id.vat else 'N'
        return invoice_data

    def _l10n_cn_baiwang_prepare_lines(self) -> list:
        """Map Odoo invoice lines to Baiwang invoiceDetailsList format with proportional discount splitting."""
        product_lines = self.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        positive_lines = product_lines.filtered(lambda l: l.price_subtotal >= 0)
        negative_lines = product_lines.filtered(lambda l: l.price_subtotal < 0)
        total_discount_price = sum(negative_lines.mapped('price_subtotal'))
        total_discount_tax = sum((l.price_total - l.price_subtotal) for l in negative_lines)
        total_positive_price = sum(positive_lines.mapped('price_subtotal'))
        lines = []
        goods_line_no = 1
        rem_disc_price = total_discount_price
        rem_disc_tax = total_discount_tax
        for i, pos_line in enumerate(positive_lines):
            if not pos_line.l10n_cn_tax_category_id:
                raise UserError(self.env._("Missing Tax Category Code on line: %s", pos_line.name))
            pos_price = round(pos_line.price_subtotal, 2)
            pos_tax = round(pos_line.price_total - pos_line.price_subtotal, 2)
            tax_rate = round(pos_tax / pos_price, 2) if pos_price else 0.0
            line_disc_price = 0.0
            line_disc_tax = 0.0
            if total_discount_price < 0 and total_positive_price > 0:
                if i == len(positive_lines) - 1:
                    line_disc_price = round(rem_disc_price, 2)
                    line_disc_tax = round(rem_disc_tax, 2)
                else:
                    ratio = pos_price / total_positive_price
                    line_disc_price = round(total_discount_price * ratio, 2)
                    line_disc_tax = round(total_discount_tax * ratio, 2)
                    rem_disc_price -= line_disc_price
                    rem_disc_tax -= line_disc_tax
            if pos_line.discount:
                factor = pos_line.discount / 100.0
                gross_price = round(pos_price / (1.0 - factor), 2)
                gross_tax = round(pos_tax / (1.0 - factor), 2)
                line_disc_price += (pos_price - gross_price)
                line_disc_tax += (pos_tax - gross_tax)
                pos_price = gross_price
                pos_tax = gross_tax
            is_discounted = line_disc_price < 0
            line_data = {
                'goodsLineNo': goods_line_no,
                'invoiceLineNature': '2' if is_discounted else '0',
                'goodsName': (pos_line.name or pos_line.product_id.name or '').replace('\n', ' ')[:100],
                'goodsCode': pos_line.l10n_cn_tax_category_id.code,
                'goodsTaxRate': abs(tax_rate),
                'goodsTotalPrice': pos_price,
                'goodsTotalTax': pos_tax,
                'preferentialMarkFlag': '0',
            }
            if pos_line.quantity:
                line_data['goodsQuantity'] = str(pos_line.quantity)
                line_data['goodsPrice'] = str(round(pos_price / pos_line.quantity, 8))
            elif pos_line.price_unit:
                line_data['goodsPrice'] = str(round(pos_line.price_unit, 8))
            if pos_line.product_uom_id:
                line_data['goodsUnit'] = pos_line.product_uom_id.name
            lines.append(line_data)
            goods_line_no += 1
            if is_discounted:
                lines.append({
                    'goodsLineNo': goods_line_no,
                    'invoiceLineNature': '1',
                    'goodsName': line_data['goodsName'],
                    'goodsCode': line_data['goodsCode'],
                    'goodsTaxRate': abs(tax_rate),
                    'goodsTotalPrice': round(line_disc_price, 2),
                    'goodsTotalTax': round(line_disc_tax, 2),
                    'preferentialMarkFlag': '0',
                })
                goods_line_no += 1
        return lines

    # ─── Red Form (Credit Note) ────────────────────────────────────────

    def action_request_baiwang_red_form(self):
        """Triggered by user on a posted Credit Note to request a Red Form confirmation."""
        self.ensure_one()
        if self.move_type != 'out_refund':
            raise UserError(self.env._("Red Form can only be requested for Credit Notes."))
        if self.state != 'draft':
            raise UserError(self.env._("Credit Note must be in draft before requesting a Red Form."))
        if not self.l10n_cn_baiwang_red_form_type:
            raise UserError(self.env._("Please select a Red Form Reason before requesting."))
        if self.l10n_cn_baiwang_state in ('sent', 'issued'):
            raise UserError(self.env._("Cannot request a Red Form for an invoice in 'sent' or 'issued' state."))

        company = self.company_id
        client = BaiwangClient(company)
        client.ensure_connection()
        original_move = self.reversed_entry_id
        if not original_move or not original_move.l10n_cn_baiwang_invoice_no:
            raise UserError(self.env._("Cannot find the normal invoice number. Ensure this credit note was created from a posted Baiwang invoice."))
        edi_doc = self.env['l10n_cn_edi.document'].create({
            'move_id': self.id,
            'state': 'draft',
        })
        serial_no = f"OURRED_{self.id}_{fields.Datetime.now():%Y%m%d%H%M%S}"
        red_form_data = self._l10n_cn_baiwang_prepare_red_form_data(original_move, serial_no)
        try:
            result = client.add_red_confirmation(red_form_data)
        except UserError as e:
            error_msg = str(e)
            edi_doc.write({'state': 'failed', 'error_message': error_msg})
            self.write({'l10n_cn_baiwang_state': 'failed'})
            self.message_post(body=self.env._("Network or Proxy error: %s", error_msg))
            return

        if result.get('success'):
            resp_list = result.get('response', [])
            if resp_list:
                resp = resp_list[0]
                confirm_state = resp.get('confirmState')

                edi_doc.write({
                    'baiwang_uuid': resp.get('redConfirmUuid'),
                    'baiwang_red_form_number': resp.get('redConfirmNo'),
                    'baiwang_confirm_state': confirm_state,
                    'state': 'red_form_confirmed' if confirm_state in ('01', '04') else 'red_form_pending',
                })

                if confirm_state in ('01', '04'):
                    vals = {'l10n_cn_baiwang_state': 'issued'}
                    if resp.get('redInvoiceNo'):
                        vals['l10n_cn_baiwang_invoice_no'] = resp['redInvoiceNo']

                    raw_date = resp.get('redInvoiceDate')
                    if raw_date and len(raw_date) >= 14:
                        vals['l10n_cn_baiwang_invoice_date'] = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]} {raw_date[8:10]}:{raw_date[10:12]}:{raw_date[12:14]}"
                    else:
                        # If Baiwang omits redInvoiceDate, fall back to current time.
                        vals['l10n_cn_baiwang_invoice_date'] = fields.Datetime.now()

                    self.write(vals)
                    self.message_post(body=self.env._("Red Form confirmed (auto-approved). No: %s", resp.get('redConfirmNo')))
                    self.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=self.env._("Red Form has been approved and Red Fapiao has been issued, Please confirm Credit Note in Odoo accordingly"),
                    )
        else:
            err = result.get('errorResponse', {}) if result else {}
            sub_code = err.get('subCode', err.get('code', 'UnknownCode'))
            sub_msg = err.get('subMessage', err.get('message', 'Unknown Error occurred during submission'))
            error_msg = f"[{sub_code}] {sub_msg}"

            edi_doc.write({'state': 'failed', 'error_message': error_msg})
            self.write({'l10n_cn_baiwang_state': 'failed'})
            self.message_post(body=self.env._("Baiwang Red Form rejection: %s", error_msg))

    def _l10n_cn_baiwang_prepare_red_form_data(self, original_move, serial_no: str) -> dict:
        """Build red letter confirmation form payload from credit note + normal invoice."""
        self.ensure_one()
        total_price = -abs(sum(
            line.price_subtotal for line in self.invoice_line_ids if line.display_type == 'product'
        ))
        total_tax = -abs(self.amount_tax)
        orig_date = original_move.l10n_cn_baiwang_invoice_date.strftime('%Y-%m-%d %H:%M:%S') if original_move.l10n_cn_baiwang_invoice_date else (f"{original_move.invoice_date} 00:00:00" if original_move.invoice_date else "")
        orig_total_price = sum(
            line.price_subtotal for line in original_move.invoice_line_ids if line.display_type == 'product'
        )
        orig_total_tax = original_move.amount_tax
        orig_type = original_move.l10n_cn_baiwang_invoice_type_code or '02'
        origin_invoice_type = '01' if orig_type in ('01', '004', '028') else '02'
        raw_phone = getattr(original_move.partner_id, 'mobile', None) or original_move.partner_id.phone or ''
        clean_phone = ''.join(c for c in raw_phone if c.isdigit())
        valid_phone = clean_phone if clean_phone and clean_phone[0] in ('0', '1') and 10 <= len(clean_phone) <= 12 else ''
        return {
            'redConfirmSerialNo': serial_no,
            'entryIdentity': '01',  # 01=seller side
            'sellerTaxNo': self.company_id.vat,
            'sellerTaxName': self.company_id.name,
            'buyerTaxName': self.partner_id.name or '',
            'buyerTaxNo': self.partner_id.vat or '',
            'originInvoiceIsPaper': 'N',
            'originalInvoiceNo': original_move.l10n_cn_baiwang_invoice_no,
            'originInvoiceDate': orig_date,
            'originInvoiceTotalPrice': round(orig_total_price, 2),
            'originInvoiceTotalTax': round(orig_total_tax, 2),
            'originInvoiceType': origin_invoice_type,
            'invoiceTotalPrice': round(total_price, 2),
            'invoiceTotalTax': round(total_tax, 2),
            'redInvoiceLabel': self.l10n_cn_baiwang_red_form_type or '01',
            'invoiceSource': '2',  # 2=digital platform (全电)
            'priceTaxMark': '0',
            'autoIssueSwitch': 'Y',  # Auto-issue red invoice on confirmation
            'deliverFlag': '0',
            'redInvoiceIsPaper': 'N',
            'redConfirmDetailReqEntityList': self._l10n_cn_baiwang_prepare_red_form_lines(),
            # Optional fields
            'originalPaperInvoiceCode': '',
            'originalPaperInvoiceNo': '',
            'orgCode': '',
            'accessPlatformNo': '',
            'taxUserName': '',
            'drawer': '',
            'drawerCredentialsType': '',
            'drawerCredentialsNo': '',
            'buyerEmail': self.partner_id.email or '',
            'buyerPhone': valid_phone,
            'originInvoiceSetCode': '',
            'ext': {},
        }

    def _l10n_cn_baiwang_prepare_red_form_lines(self) -> list:
        """Build Red Form lines by netting discounts into products and preserving original indices."""
        # 1. Get the standard proportional lines (Products > 0, Discounts < 0)
        blue_lines = self._l10n_cn_baiwang_prepare_lines()
        collapsed_lines = []
        for line in blue_lines:
            if line.get('invoiceLineNature') == '1':  # discount line
                if collapsed_lines:
                    parent = collapsed_lines[-1]
                    parent['goodsTotalPrice'] = round(parent['goodsTotalPrice'] + line['goodsTotalPrice'], 2)
                    parent['goodsTotalTax'] = round(parent['goodsTotalTax'] + line['goodsTotalTax'], 2)
                    parent['invoiceLineNature'] = '0'
            else:
                new_line = line.copy()
                new_line['originalInvoiceDetailNo'] = new_line['goodsLineNo']
                collapsed_lines.append(new_line)

        for line in collapsed_lines:
            # ALL financial amounts must be negative on a Red Form
            line['goodsTotalPrice'] = -abs(line['goodsTotalPrice'])
            line['goodsTotalTax'] = -abs(line['goodsTotalTax'])
            if 'goodsQuantity' in line:
                line['goodsQuantity'] = str(-abs(float(line['goodsQuantity'])))
            # Clean out keys not used by the Red Form schema
            line.pop('goodsSimpleName', None)
            line['projectName'] = line['goodsName'][:50]

        return collapsed_lines

    # ─── Lifecycle Guards ───────────────────────────────────────────────

    @api.ondelete(at_uninstall=False)
    def _unlink_except_pending_red_forms(self):
        """Prevent deletion while a red form request is pending."""
        for move in self:
            if move.l10n_cn_edi_document_ids.filtered(lambda d: d.state == 'red_form_pending'):
                raise UserError(self.env._(
                    "You cannot delete this record because a Red Form Request is "
                    "currently pending on the Baiwang platform.\n\n"
                    "Please revoke the Red Form first.",
                ))

    def action_approve_inbound_red_form(self):
        """Approve a Red Form initiated by the buyer."""
        self.ensure_one()
        latest_doc = self.l10n_cn_edi_document_ids.filtered(lambda d: d.state == 'red_form_pending')[:1]
        if not latest_doc:
            return
        if not latest_doc.baiwang_uuid.startswith('mock-'):  # TODO: remove when going to production
            client = BaiwangClient(self.company_id)
            try:
                client.operate_red_confirmation(latest_doc.baiwang_uuid, latest_doc.baiwang_red_form_number, '01')
            except UserError as e:
                raise UserError(self.env._("Failed to approve Red Form on Baiwang: %s", e))
        latest_doc.write({'state': 'red_form_confirmed', 'baiwang_confirm_state': '01'})
        self.message_post(body=self.env._("Inbound Red Form approved. Please draft a Credit Note."))

    def action_reject_inbound_red_form(self):
        """Reject a Red Form initiated by the buyer."""
        self.ensure_one()
        latest_doc = self.l10n_cn_edi_document_ids.filtered(lambda d: d.state == 'red_form_pending')[:1]
        if not latest_doc:
            return
        if not latest_doc.baiwang_uuid.startswith('mock-'):  # TODO: remove when going to production
            client = BaiwangClient(self.company_id)
            try:
                client.operate_red_confirmation(latest_doc.baiwang_uuid, latest_doc.baiwang_red_form_number, '02')  # 02=Deny
            except UserError as e:
                raise UserError(self.env._("Failed to reject Red Form on Baiwang: %s", e))
        latest_doc.write({'state': 'failed', 'error_message': self.env._("Rejected by user.")})
        self.message_post(body=self.env._("Inbound Red Form %s rejected.", latest_doc.baiwang_red_form_number))

    @api.depends('l10n_cn_edi_document_ids.baiwang_red_form_type')
    def _compute_l10n_cn_baiwang_red_form_type(self):
        for move in self:
            latest_doc = move.l10n_cn_edi_document_ids.sorted('create_date', reverse=True)[:1]
            if latest_doc and latest_doc.baiwang_red_form_type:
                move.l10n_cn_baiwang_red_form_type = latest_doc.baiwang_red_form_type

    @api.depends(
        'l10n_cn_edi_document_ids.state',
        'l10n_cn_edi_document_ids.baiwang_uuid',
        'l10n_cn_edi_document_ids.baiwang_red_form_number',
        'l10n_cn_edi_document_ids.baiwang_red_form_amount_total',
        'l10n_cn_edi_document_ids.baiwang_red_form_amount_tax',
    )
    def _compute_l10n_cn_baiwang_latest_edi_data(self):
        for move in self:
            latest = move.l10n_cn_edi_document_ids.sorted('create_date', reverse=True)[:1]
            move.l10n_cn_baiwang_red_form_uuid = latest.baiwang_uuid or False
            move.l10n_cn_baiwang_red_form_number = latest.baiwang_red_form_number or False
            move.l10n_cn_baiwang_red_form_status = latest.state or False
            move.l10n_cn_baiwang_red_form_amount_total = latest.baiwang_red_form_amount_total or 0.0
            move.l10n_cn_baiwang_red_form_amount_tax = latest.baiwang_red_form_amount_tax or 0.0

    def action_fetch_inbound_red_form_details(self):
        """Manually fetch and dump the red form line details into the chatter."""
        for move in self:
            latest_doc = move.l10n_cn_edi_document_ids.filtered(lambda d: d.state == 'red_form_pending')[:1]
            if not latest_doc:
                continue
            # TODO: remove when going to production
            if latest_doc.baiwang_uuid.startswith('mock-'):
                move.message_post(body=self.env._("Cannot fetch details for mock records."))
                continue
            client = BaiwangClient(move.company_id)
            try:
                res = client.query_red_form_detail(latest_doc.baiwang_uuid)
            except UserError as e:
                move.message_post(body=self.env._("Failed to fetch details: %s", e))
                continue
            details = res[0].get('electricInvoiceDetails', []) if isinstance(res, list) and res else []
            if not details:
                move.message_post(body=self.env._("No extra line details found on Baiwang."))
                continue
            msg = "<b>Red Form Line Details from Baiwang:</b><ul>"
            for line in details:
                name = line.get('goodsName', 'Unknown Item')
                qty = line.get('goodsQuantity', 'N/A')
                price = line.get('goodsTotalPrice', '0.00')
                tax = line.get('goodsTotalTax', '0.00')
                msg += f"<li>{name} — Qty: {qty} | Price: {price} | Tax: {tax}</li>"
            msg += "</ul>"
            move.message_post(body=msg)

    def _reverse_moves(self, default_values_list=None, cancel=False):
        """Pass the Baiwang Red Fapiao number and reason to the Credit Note."""
        reversals = super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)
        for move, reversal in zip(self, reversals):
            if move.move_type == 'in_invoice' and move.l10n_cn_baiwang_red_form_status in ('red_form_pending', 'red_form_confirmed'):
                doc = move.l10n_cn_edi_document_ids.filtered(lambda d: d.baiwang_uuid == move.l10n_cn_baiwang_red_form_uuid)[:1]
                if doc and doc.baiwang_red_invoice_no:
                    reversal.write({
                        'l10n_cn_baiwang_invoice_no': doc.baiwang_red_invoice_no,
                        'l10n_cn_baiwang_state': 'issued',
                        'l10n_cn_baiwang_red_form_type': doc.baiwang_red_form_type,
                    })
        return reversals
