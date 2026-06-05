# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from .baiwang_client import BaiwangClient

_logger = logging.getLogger(__name__)

INVOICE_TYPE_CODES = [
    ('01', '01 Digital Special Invoice (全电专票)'),
    ('02', '02 Digital General Invoice (全电普票)'),
]

RED_FORM_TYPES = [
    ('01', '01 Billing Error (开票有误)'),
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

    # Blue invoice fields
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
    l10n_cn_baiwang_invoice_no = fields.Char(string="Baiwang Fapiao Number", copy=False, readonly=True)
    l10n_cn_baiwang_invoice_date = fields.Char(string="Fapiao Date", copy=False, readonly=True)
    l10n_cn_baiwang_serial_no = fields.Char(string="Serial No", copy=False, readonly=True, help="Unique request serial number for idempotency")
    l10n_cn_baiwang_qr_code = fields.Char(string="Invoice QR Code", copy=False, readonly=True)
    l10n_cn_baiwang_error_message = fields.Text(string="Baiwang Error", copy=False, readonly=True)

    # Red form fields (for credit notes)
    l10n_cn_baiwang_red_form_type = fields.Selection(
        selection=RED_FORM_TYPES,
        string="Red Form Reason",
    )
    l10n_cn_baiwang_original_invoice_id = fields.Many2one(
        'account.move',
        string="Original Invoice",
        help="The original blue invoice being reversed",
    )

    # EDI document tracking
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
        string="Buyer Bank Account",
        compute='_compute_l10n_cn_buyer_bank_id',
        store=True,
        readonly=False,
        domain="[('partner_id', '=', partner_id)]",
        help="The customer's bank account to be printed on the Chinese Baiwang E-Fapiao."
    )
    l10n_cn_baiwang_red_form_uuid = fields.Char(
        string="Red Form UUID", 
        compute='_compute_l10n_cn_baiwang_latest_edi_data'
    )
    l10n_cn_baiwang_red_form_number = fields.Char(
        string="Red Form Number", 
        compute='_compute_l10n_cn_baiwang_latest_edi_data'
    )
    l10n_cn_baiwang_red_form_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('red_form_pending', 'Red Form Pending'),
            ('red_form_confirmed', 'Red Form Confirmed'),
            ('failed', 'Failed'),
        ],
        string="Red Form Status",
        compute='_compute_l10n_cn_baiwang_latest_edi_data'
    )

    # ─── Computed Methods ───────────────────────────────────────────────

    @api.depends(
        'l10n_cn_edi_document_ids.state', 
        'l10n_cn_edi_document_ids.baiwang_uuid', 
        'l10n_cn_edi_document_ids.baiwang_red_form_number'
    )
    def _compute_l10n_cn_baiwang_latest_edi_data(self):
        for move in self:
            if move.l10n_cn_edi_document_ids:
                # Safely sort and grab the most recently created tracking document
                latest = move.l10n_cn_edi_document_ids.sorted('create_date', reverse=True)[0]
                move.l10n_cn_baiwang_red_form_uuid = latest.baiwang_uuid
                move.l10n_cn_baiwang_red_form_number = latest.baiwang_red_form_number
                move.l10n_cn_baiwang_red_form_status = latest.state
            else:
                move.l10n_cn_baiwang_red_form_uuid = False
                move.l10n_cn_baiwang_red_form_number = False
                move.l10n_cn_baiwang_red_form_status = False

    @api.depends('country_code', 'move_type', 'state', 'l10n_cn_baiwang_state')
    def _compute_l10n_cn_baiwang_is_needed(self):
        for move in self:
            move.l10n_cn_baiwang_is_needed = (
                move.country_code == 'CN'
                and move.move_type in ('out_invoice', 'out_refund')
                and move.state == 'posted'
                and move.l10n_cn_baiwang_state not in ('issued', 'sent')
            )

    @api.depends(
        'country_code',
        'move_type',
        'state',
        'l10n_cn_baiwang_original_invoice_id.l10n_cn_baiwang_invoice_no',
        'reversed_entry_id.l10n_cn_baiwang_invoice_no',
    )
    def _compute_l10n_cn_baiwang_red_form_required(self):
        for move in self:
            original_move = move.l10n_cn_baiwang_original_invoice_id or move.reversed_entry_id
            move.l10n_cn_baiwang_red_form_required = bool(
                move.country_code == 'CN'
                and move.move_type == 'out_refund'
                and move.state == 'draft'
                and original_move
                and original_move.l10n_cn_baiwang_invoice_no,
            )

    @api.depends('invoice_date', 'l10n_cn_baiwang_invoice_date', 'l10n_cn_baiwang_invoice_no')
    def _compute_l10n_cn_baiwang_date_consistency_warning(self):
        warning_msg = self.env._(
            "Invoice Date is different from Fapiao Date. Please be aware of the consistency between E-fapiao Date and Odoo Invoice Date.",
        )
        for move in self:
            move.l10n_cn_baiwang_date_consistency_warning = False
            if (
                move.move_type != 'out_invoice'
                or not move.l10n_cn_baiwang_invoice_no
                or not move.invoice_date
                or not move.l10n_cn_baiwang_invoice_date
                or len(move.l10n_cn_baiwang_invoice_date) < 8
            ):
                continue
            fapiao_yyyymmdd = move.l10n_cn_baiwang_invoice_date[:8]
            if move.invoice_date.strftime('%Y%m%d') != fapiao_yyyymmdd:
                move.l10n_cn_baiwang_date_consistency_warning = warning_msg

    def _l10n_cn_baiwang_generate_serial_no(self, prefix: str) -> str:
        """Generate a stable, human-readable request serial to send to Baiwang."""
        self.ensure_one()
        timestamp = fields.Datetime.now().strftime('%Y%m%d%H%M%S')
        return f"{prefix}_{self.id}_{timestamp}"

    @api.depends('partner_id')
    def _compute_l10n_cn_buyer_bank_id(self):
        for move in self:
            if move.partner_id and move.partner_id.bank_ids:
                move.l10n_cn_buyer_bank_id = move.partner_id.bank_ids[0]
            else:
                move.l10n_cn_buyer_bank_id = False

    # ─── Blue Invoice Issuance ──────────────────────────────────────────

    def _l10n_cn_baiwang_issue_invoice(self):
        """
        Issue a blue (positive) e-Fapiao via Baiwang for customer invoices.
        Returns error message string or None on success.
        """
        self.ensure_one()
        company = self.company_id

        if company.l10n_cn_baiwang_subscription_status != 'authorized':
            raise UserError(self.env._("Baiwang is not authorized. Please go to Settings."))

        client = BaiwangClient(company)

        # Fail fast if endpoint is not reachable before mutating invoice state/serial.
        try:
            client.ensure_connection()
        except UserError as e:
            return str(e)

        serial_no = self.l10n_cn_baiwang_serial_no or self._l10n_cn_baiwang_generate_serial_no('BLUE')

        # Generate unique serial number (idempotent per invoice)
        self.l10n_cn_baiwang_serial_no = serial_no

        # Build invoice payload
        invoice_data = self._l10n_cn_baiwang_prepare_invoice_data(serial_no)

        try:
            result = client.issue_invoice(invoice_data)
        except UserError as e:
            # Avoid marking as failed for connectivity/precondition errors; user can retry.
            return str(e)
        except (TypeError, ValueError) as e:
            error_msg = str(e)
            self.write({
                'l10n_cn_baiwang_state': 'failed',
                'l10n_cn_baiwang_error_message': error_msg,
            })
            return error_msg

        if result.get('success'):
            # Parse successful response
            success_list = result.get('response', {}).get('success', [])
            if success_list:
                invoice_resp = success_list[0]
                self.write({
                    'l10n_cn_baiwang_state': 'issued',
                    'l10n_cn_baiwang_invoice_no': invoice_resp.get('invoiceNo'),
                    'l10n_cn_baiwang_invoice_date': invoice_resp.get('invoiceDate'),
                    'l10n_cn_baiwang_qr_code': invoice_resp.get('invoiceQrCode'),
                    'l10n_cn_baiwang_error_message': False,
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

        self.write({
            'l10n_cn_baiwang_state': 'failed',
            'l10n_cn_baiwang_error_message': error_msg,
        })
        return error_msg

    def _l10n_cn_baiwang_prepare_invoice_data(self, serial_no: str) -> dict:
        """Map Odoo invoice data to Baiwang invoice.issue request format."""
        self.ensure_one()

        # Calculate totals (tax-exclusive)
        total_price = sum(
            line.price_subtotal
            for line in self.invoice_line_ids
            if not line.display_type
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

        # Add buyer address/bank info if available
        if self.partner_id.street:
            buyer_address = ' '.join(filter(None, [
                self.partner_id.street,
                self.partner_id.street2,
                self.partner_id.city,
            ]))
            invoice_data['buyerAddress'] = buyer_address
        if self.partner_id.phone:
            invoice_data['buyerPhone'] = self.partner_id.phone

        return invoice_data

    def _l10n_cn_baiwang_prepare_lines(self) -> list:
        """Map Odoo invoice lines to Baiwang invoiceDetailsList format."""
        lines = []
        for index, line in enumerate(
            self.invoice_line_ids.filtered(lambda l: not l.display_type),
            start=1,
        ):
            # Get tax rate from the line's tax
            tax_rate = 0.0
            if line.tax_ids:
                # Use the first tax percentage (Baiwang expects decimal: 0.13, 0.09, 0.06, etc.)
                tax_rate = line.tax_ids[0].amount / 100

            line_data = {
                'goodsLineNo': index,
                'invoiceLineNature': '0',  # 0=normal line
                'goodsName': line.product_id.name or line.name or '',
                'goodsCode': line.product_id.l10n_cn_tax_category_id.code or '1010101070000000000',
                'goodsTaxRate': tax_rate,
                'goodsTotalPrice': round(line.price_subtotal, 2),
                'goodsTotalTax': round(line.price_total - line.price_subtotal, 2),
                'preferentialMarkFlag': '0',  # 0=no preferential policy
            }

            # Optional fields
            if line.quantity:
                line_data['goodsQuantity'] = str(line.quantity)
            if line.price_unit:
                line_data['goodsPrice'] = str(round(line.price_unit, 8))
            if line.product_uom_id:
                line_data['goodsUnit'] = line.product_uom_id.name

            lines.append(line_data)
        return lines

    # ─── Red Form (Credit Note) ────────────────────────────────────────

    def action_request_baiwang_red_form(self):
        """
        Triggered by user on a posted Credit Note to request a Red Form confirmation.
        This is step 1 of the red invoice workflow.
        """
        self.ensure_one()

        if self.move_type != 'out_refund':
            raise UserError(self.env._("Red Form can only be requested for Credit Notes."))
        if self.state != 'draft':
            raise UserError(self.env._("Credit Note must be in draft before requesting a Red Form."))
        if not self.l10n_cn_baiwang_red_form_type:
            raise UserError(self.env._("Please select a Red Form Reason before requesting."))

        company = self.company_id
        if not company.l10n_cn_baiwang_app_key:
            raise UserError(self.env._("Baiwang API credentials are not configured. Please go to Settings > Invoicing > China Electronic Invoicing (Baiwang)."))

        client = BaiwangClient(company)
        client.ensure_connection()

        # Find original blue invoice
        original_move = self.l10n_cn_baiwang_original_invoice_id or self.reversed_entry_id
        if not original_move or not original_move.l10n_cn_baiwang_invoice_no:
            raise UserError(self.env._(
                "Cannot find the original invoice number. Please link the original invoice "
                "or ensure it was issued via Baiwang first.",
            ))

        # Create EDI document record to track this request
        edi_doc = self.env['l10n_cn_edi.document'].create({
            'move_id': self.id,
            'state': 'draft',
        })

        # Build red confirmation payload
        serial_no = self._l10n_cn_baiwang_generate_serial_no('RED')
        red_form_data = self._l10n_cn_baiwang_prepare_red_form_data(
            original_move, serial_no,
        )

        try:
            result = client.add_red_confirmation(red_form_data)
        except UserError as e:
            edi_doc.write({'state': 'failed', 'error_message': str(e)})
            raise UserError(self.env._("Network error: %s", str(e)))

        if result.get('success'):
            resp_list = result.get('response', [])
            if resp_list:
                resp = resp_list[0]
                edi_doc.write({
                    'baiwang_uuid': resp.get('redConfirmUuid'),
                    'baiwang_red_form_number': resp.get('redConfirmNo'),
                    'baiwang_confirm_state': resp.get('confirmState'),
                    'state': 'red_form_confirmed' if resp.get('confirmState') in ('01', '04') else 'red_form_pending',
                })
                self.l10n_cn_baiwang_state = 'sent'
                self.l10n_cn_baiwang_error_message = False

                confirm_state = resp.get('confirmState')
                if confirm_state in ('01', '04'):
                    self.message_post(body=self.env._(
                        "Red Form confirmed (auto-approved). No: %(no)s",
                        no=resp.get('redConfirmNo'),
                    ))
                else:
                    self.message_post(body=self.env._(
                        "Red Form submitted. Waiting for counterpart confirmation. UUID: %(uuid)s",
                        uuid=resp.get('redConfirmUuid'),
                    ))
                return
        else:
            err = result.get('errorResponse', {}) if result else {}
            error_msg = f"[{err.get('subCode', err.get('code', ''))}] {err.get('subMessage', err.get('message', 'Unknown'))}"
            edi_doc.write({'state': 'failed', 'error_message': error_msg})
            self.write({
                'l10n_cn_baiwang_state': 'failed',
                'l10n_cn_baiwang_error_message': error_msg,
            })
            raise UserError(self.env._("Baiwang Red Form failed: %s", error_msg))

    def _l10n_cn_baiwang_prepare_red_form_data(self, original_move, serial_no: str) -> dict:
        """Build red letter confirmation form payload from credit note + original invoice."""
        self.ensure_one()

        # Calculate negative amounts for red form
        total_price = -abs(sum(
            line.price_subtotal for line in self.invoice_line_ids if not line.display_type
        ))
        total_tax = -abs(self.amount_tax)

        # Format original invoice date
        orig_date = original_move.l10n_cn_baiwang_invoice_date or ''
        if orig_date and len(orig_date) >= 14:
            # Convert from YYYYMMDDHHmmss to YYYY-MM-DD HH:mm:ss
            orig_date = f"{orig_date[:4]}-{orig_date[4:6]}-{orig_date[6:8]} {orig_date[8:10]}:{orig_date[10:12]}:{orig_date[12:14]}"
        elif original_move.invoice_date:
            orig_date = f"{original_move.invoice_date} 00:00:00"

        # Original invoice totals
        orig_total_price = sum(
            line.price_subtotal for line in original_move.invoice_line_ids if not line.display_type
        )
        orig_total_tax = original_move.amount_tax

        # Determine invoice type code
        orig_type = original_move.l10n_cn_baiwang_invoice_type_code or '02'
        origin_invoice_type = '01' if orig_type in ('01', '004', '028') else '02'

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
            'redConfirmDetailReqEntityList': self._l10n_cn_baiwang_prepare_red_form_lines(original_move),
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
            'buyerPhone': self.partner_id.phone or '',
            'originInvoiceSetCode': '',
            'ext': {},
        }

    def _l10n_cn_baiwang_prepare_red_form_lines(self, original_move) -> list:
        """Build red form detail lines (negative amounts) from credit note lines."""
        lines = []
        for index, line in enumerate(
            self.invoice_line_ids.filtered(lambda l: not l.display_type),
            start=1,
        ):
            tax_rate = 0.0
            if line.tax_ids:
                tax_rate = line.tax_ids[0].amount / 100

            line_data = {
                'originalInvoiceDetailNo': index,
                'goodsLineNo': index,
                'goodsCode': line.product_id.l10n_cn_tax_category_id.code or '1010101070000000000',
                'goodsName': line.product_id.name or line.name or '',
                'goodsSimpleName': '',
                'projectName': line.product_id.name or line.name or '',
                'goodsTaxRate': tax_rate,
                'goodsTotalPrice': round(-abs(line.price_subtotal), 2),
                'goodsTotalTax': round(-abs(line.price_total - line.price_subtotal), 2),
                'goodsQuantity': str(-abs(line.quantity)),
                'goodsPrice': str(round(line.price_unit, 8)),
                'goodsUnit': line.product_uom_id.name if line.product_uom_id else '',
            }
            lines.append(line_data)
        return lines

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
