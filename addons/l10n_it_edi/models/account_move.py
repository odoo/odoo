# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode
from datetime import datetime
import logging
from lxml import etree
from markupsafe import escape
import uuid

from odoo import _, api, Command, fields, models
from odoo.addons.base.models.ir_qweb_fields import Markup, nl2br, nl2br_enclose
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_repr, cleanup_xml_node

_logger = logging.getLogger(__name__)


WAITING_STATES = ('being_sent', 'processing', 'forward_attempt')


# -------------------------------------------------------------------------
# XML tool functions
# -------------------------------------------------------------------------

def get_text(tree, xpath, many=False):
    texts = [el.text.strip() for el in tree.xpath(xpath) if el.text]
    return texts if many else texts[0] if texts else ''

def get_float(tree, xpath):
    try:
        return float(get_text(tree, xpath))
    except ValueError:
        return 0.0

def get_date(tree, xpath):
    """ Dates in FatturaPA are ISO 8601 date format, pattern '[-]CCYY-MM-DD[Z|(+|-)hh:mm]' """
    dt = get_datetime(tree, xpath)
    return dt.date() if dt else False

def get_datetime(tree, xpath):
    """ Datetimes in FatturaPA are ISO 8601 date format, pattern '[-]CCYY-MM-DDThh:mm:ss[Z|(+|-)hh:mm]'
        Python 3.7 -> 3.11 doesn't support 'Z'.
    """
    if (datetime_str := get_text(tree, xpath)):
        try:
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return False
    return False


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_edi_state = fields.Selection(
        string="SDI State",
        selection=[
            ('being_sent', 'Being Sent To SdI'),
            ('requires_user_signature', 'Requires user signature'),
            ('processing', 'SdI Processing'),
            ('rejected', 'SdI Rejected'),
            ('forwarded', 'SdI Accepted, Forwarded to Partner'),
            ('forward_failed', 'SdI Accepted, Forward to Partner Failed'),
            ('forward_attempt', 'SdI Accepted, Forwarding to Partner'),
            ('accepted_by_pa_partner', 'SdI Accepted, Accepted by the PA Partner'),
            ('rejected_by_pa_partner', 'SdI Accepted, Rejected by the PA Partner'),
            ('accepted_by_pa_partner_after_expiry', 'SdI Accepted, PA Partner Expired Terms'),
        ],
        copy=False, tracking=True,
        help="This state is updated by default, but you can force the value. ",
    )
    l10n_it_edi_header = fields.Html(
        help='User description of the current state, with hints to make the flow progress',
        readonly=True,
        copy=False,
    )
    l10n_it_edi_transaction = fields.Char(copy=False, string="FatturaPA Transaction")
    l10n_it_edi_attachment_file = fields.Binary(copy=False, attachment=True)
    l10n_it_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="FatturaPA Attachment",
        compute=lambda self: self._compute_linked_attachment_id('l10n_it_edi_attachment_id', 'l10n_it_edi_attachment_file'),
        depends=['l10n_it_edi_attachment_file'],
    )
    l10n_it_edi_is_self_invoice = fields.Boolean(compute="_compute_l10n_it_edi_is_self_invoice")
    l10n_it_stamp_duty = fields.Float(default=0, string="Dati Bollo")
    l10n_it_ddt_id = fields.Many2one('l10n_it.ddt', string='DDT', copy=False)

    l10n_it_origin_document_type = fields.Selection(
        string="Origin Document Type",
        selection=[('purchase_order', 'Purchase Order'), ('contract', 'Contract'), ('agreement', 'Agreement')],
        copy=False)
    l10n_it_origin_document_name = fields.Char(
        string="Origin Document Name",
        copy=False)
    l10n_it_origin_document_date = fields.Date(
        string="Origin Document Date",
        copy=False)
    l10n_it_cig = fields.Char(
        string="CIG",
        copy=False,
        help="Tender Unique Identifier")
    l10n_it_cup = fields.Char(
        string="CUP",
        copy=False,
        help="Public Investment Unique Identifier")
    # Technical field for showing the above fields or not
    l10n_it_partner_pa = fields.Boolean(compute='_compute_l10n_it_partner_pa')

    # -------------------------------------------------------------------------
    # Computes
    # -------------------------------------------------------------------------

    @api.depends('commercial_partner_id.l10n_it_pa_index', 'company_id')
    def _compute_l10n_it_partner_pa(self):
        for move in self:
            move.l10n_it_partner_pa = (move.country_code == 'IT' and move.commercial_partner_id.l10n_it_pa_index and
                                       len(move.commercial_partner_id.l10n_it_pa_index) == 6)

    @api.depends('move_type', 'line_ids.tax_tag_ids')
    def _compute_l10n_it_edi_is_self_invoice(self):
        """
            Italian EDI requires Vendor bills coming from EU countries to be sent as self-invoices.
            We recognize these cases based on the taxes that target the VJ tax grids, which imply
            the use of VAT External Reverse Charge.
        """
        it_tax_report_vj_lines = self.env['account.report.line'].search([
            ('report_id.country_id.code', '=', 'IT'),
            ('code', '=like', 'VJ%'),
        ])
        vj_lines_tags = it_tax_report_vj_lines.expression_ids._get_matching_tags()
        for move in self:
            if not move.is_purchase_document():
                move.l10n_it_edi_is_self_invoice = False
                continue
            invoice_lines_tags = move.line_ids.tax_tag_ids
            ids_intersection = set(invoice_lines_tags.ids) & set(vj_lines_tags.ids)
            move.l10n_it_edi_is_self_invoice = bool(ids_intersection)

    # -------------------------------------------------------------------------
    # Overrides
    # -------------------------------------------------------------------------

    @api.depends('l10n_it_edi_transaction')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            move.show_reset_to_draft_button = not move.l10n_it_edi_transaction and move.show_reset_to_draft_button

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        if file_data['type'] == 'l10n_it_edi':
            return self._l10n_it_edi_import_invoice
        return super()._get_edi_decoder(file_data, new=new)

    def _post(self, soft=True):
        # EXTENDS 'account'
        self.write({'l10n_it_edi_header': False})
        return super()._post(soft)

    # -------------------------------------------------------------------------
    # Business actions
    # -------------------------------------------------------------------------

    def action_l10n_it_edi_send(self):
        """ Checks that the invoice data is coherent.
            Attaches the XML file to the invoice.
            Sends the invoice to the SdI.
        """
        self.ensure_one()

        if (errors := self._l10n_it_edi_export_data_check()):
            message = _("Errors occured while creating the e-invoice file.")
            message += "\n- " + "\n- ".join(errors)
            raise UserError(message)

        attachment_vals = self._l10n_it_edi_get_attachment_values(pdf_values=None)
        self.env['ir.attachment'].create(attachment_vals)
        self.invalidate_recordset(fnames=['l10n_it_edi_attachment_id', 'l10n_it_edi_attachment_file'])
        self.message_post(attachment_ids=self.l10n_it_edi_attachment_id.ids)
        self._l10n_it_edi_send({self: attachment_vals})
        self.is_move_sent = True

    def action_check_l10n_it_edi(self):
        self.ensure_one()
        if not self.l10n_it_edi_transaction and self.l10n_it_edi_state not in WAITING_STATES:
            raise UserError(_("This move is not waiting for updates from the SdI."))
        if self.l10n_it_edi_state == 'being_sent':
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        self._l10n_it_edi_update_send_state()

    def button_draft(self):
        # EXTENDS 'account'
        for move in self:
            move.l10n_it_edi_state = False
        return super().button_draft()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _l10n_it_edi_ready_for_xml_export(self):
        self.ensure_one()
        return (
            self.state == 'posted'
            and self.company_id.account_fiscal_country_id.code == 'IT'
            and self.journal_id.type == 'sale'
            and self.l10n_it_edi_state in (False, 'rejected')
        )

    def _l10n_it_edi_get_line_values(self, reverse_charge_refund=False, is_downpayment=False, convert_to_euros=True):
        """ Returns a list of dictionaries passed to the template for the invoice lines (DettaglioLinee)
        """
        invoice_lines = []
        lines = self.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_note', 'line_section'))
        for num, line in enumerate(lines):
            sign = -1 if line.move_id.is_inbound() else 1
            price_subtotal = (line.balance * sign) if convert_to_euros else line.price_subtotal
            # The price_subtotal should be inverted when the line is a reverse charge refund.
            if reverse_charge_refund:
                price_subtotal = -price_subtotal

            # Unit price
            price_unit = 0
            if line.quantity and line.discount != 100.0:
                price_unit = price_subtotal / ((1 - (line.discount or 0.0) / 100.0) * abs(line.quantity))
            else:
                price_unit = line.price_unit

            description = line.name

            # Down payment lines:
            # If there was a down paid amount that has been deducted from this move,
            # we need to put a reference to the down payment invoice in the DatiFattureCollegate tag
            downpayment_moves = self.env['account.move']
            if not is_downpayment and line.price_subtotal < 0:
                downpayment_moves = line._get_downpayment_lines().mapped("move_id")
                if downpayment_moves:
                    downpayment_moves_description = ', '.join(m.name for m in downpayment_moves)
                    sep = ', ' if description else ''
                    description = f"{description}{sep}{downpayment_moves_description}"

            invoice_lines.append({
                'line': line,
                'line_number': num + 1,
                'description': description or 'NO NAME',
                'unit_price': price_unit,
                'subtotal_price': price_subtotal,
                'vat_tax': line.tax_ids.flatten_taxes_hierarchy().filtered(lambda t: t._l10n_it_filter_kind('vat') and t.amount >= 0),
                'downpayment_moves': downpayment_moves,
                'discount_type': (
                    'SC' if line.discount > 0
                    else 'MG' if line.discount < 0
                    else False
                )
            })
        return invoice_lines

    def _l10n_it_edi_get_tax_values(self, tax_details):
        """ Returns a list of dictionaries passed to the template for the invoice lines (DatiRiepilogo)
        """
        tax_lines = []
        for _tax_name, tax_dict in tax_details['tax_details'].items():
            # The assumption is that the company currency is EUR.
            base_amount = tax_dict['base_amount']
            tax_amount = tax_dict['tax_amount']
            tax = tax_dict['tax']
            tax_rate = tax.amount
            tax_exigibility_code = (
                'S' if tax._l10n_it_is_split_payment()
                else 'D' if tax.tax_exigibility == 'on_payment'
                else 'I' if tax.tax_exigibility == 'on_invoice'
                else False
            )
            expected_base_amount = tax_amount * 100 / tax_rate if tax_rate else False
            tax = tax_dict['tax']
            # Constraints within the edi make local rounding on price included taxes a problem.
            # To solve this there is a <Arrotondamento> or 'rounding' field, such that:
            #   taxable base = sum(taxable base for each unit) + Arrotondamento
            if tax.price_include and tax.amount_type == 'percent':
                if expected_base_amount and float_compare(base_amount, expected_base_amount, 2):
                    tax_dict['rounding'] = base_amount - (tax_amount * 100 / tax_rate)
                    tax_dict['base_amount'] = base_amount - tax_dict['rounding']

            tax_line_dict = {
                'tax': tax,
                'rounding': tax_dict.get('rounding', False),
                'base_amount': tax_dict['base_amount'],
                'tax_amount': tax_dict['tax_amount'],
                'exigibility_code': tax_exigibility_code,
            }
            tax_lines.append(tax_line_dict)
        return tax_lines

    def _l10n_it_edi_filter_tax_details(self, line, tax_values):
        """Filters tax details to only include the positive amounted lines regarding VAT taxes."""
        repartition_line = tax_values['tax_repartition_line']
        return (repartition_line.factor_percent >= 0 and repartition_line.tax_id.amount >= 0)

    def _get_l10n_it_amount_split_payment(self):
        self.ensure_one()
        amount = 0.0
        if self.is_invoice(True):
            for line in [line for line in self.line_ids if line.tax_line_id]:
                if line.tax_line_id._l10n_it_is_split_payment() and line.credit > 0.0:
                    amount += line.credit
        return amount

    def _l10n_it_edi_get_values(self, pdf_values=None):
        self.ensure_one()

        # Flags
        is_self_invoice = self.l10n_it_edi_is_self_invoice
        document_type = self._l10n_it_edi_get_document_type()

        # Represent if the document is a reverse charge refund in a single variable
        reverse_charge = document_type in ['TD17', 'TD18', 'TD19']
        is_downpayment = document_type in ['TD02']
        reverse_charge_refund = self.move_type == 'in_refund' and reverse_charge
        convert_to_euros = self.currency_id.name != 'EUR'

        tax_details = self._prepare_invoice_aggregated_taxes(filter_tax_values_to_apply=self._l10n_it_edi_filter_tax_details)

        company = self.company_id
        partner = self.commercial_partner_id
        sender = company
        buyer = partner if not is_self_invoice else company
        seller = company if not is_self_invoice else partner
        sender_info_values = company.partner_id._l10n_it_edi_get_values()
        buyer_info_values = (partner if not is_self_invoice else company.partner_id)._l10n_it_edi_get_values()
        seller_info_values = (company.partner_id if not is_self_invoice else partner)._l10n_it_edi_get_values()
        representative_info_values = company.l10n_it_tax_representative_partner_id._l10n_it_edi_get_values()

        if self._l10n_it_edi_is_simplified_document_type(document_type):
            formato_trasmissione = "FSM10"
        elif partner._l10n_it_edi_is_public_administration():
            formato_trasmissione = "FPA12"
        else:
            formato_trasmissione = "FPR12"

        # Self-invoices are technically -100%/+100% repartitioned
        # but functionally need to be exported as 100%
        document_total = self.amount_total
        if is_self_invoice:
            document_total += sum([abs(v['tax_amount_currency']) for k, v in tax_details['tax_details'].items()])
            if reverse_charge_refund:
                document_total = -abs(document_total)

        split_payment_amount = self._get_l10n_it_amount_split_payment()
        if split_payment_amount:
            document_total += split_payment_amount

        # Reference line for finding the conversion rate used in the document
        conversion_rate = float_repr(
            abs(self.amount_total / self.amount_total_signed), precision_digits=5,
        ) if convert_to_euros and self.invoice_line_ids else None

        invoice_lines = self._l10n_it_edi_get_line_values(reverse_charge_refund, is_downpayment, convert_to_euros)
        tax_lines = self._l10n_it_edi_get_tax_values(tax_details)

        # Reduce downpayment views to a single recordset
        downpayment_moves = [l.get('downpayment_moves', self.env['account.move']) for l in invoice_lines]
        downpayment_moves = self.browse(move.id for moves in downpayment_moves for move in moves)

        return {
            'record': self,
            'company': company,
            'partner': partner,
            'sender': sender,
            'buyer': buyer,
            'seller': seller,
            'representative': company.l10n_it_tax_representative_partner_id,
            'sender_info': sender_info_values,
            'buyer_info': buyer_info_values,
            'seller_info': seller_info_values,
            'representative_info': representative_info_values,
            'origin_document_type': self.l10n_it_origin_document_type,
            'origin_document_name': self.l10n_it_origin_document_name,
            'origin_document_date': self.l10n_it_origin_document_date,
            'cig': self.l10n_it_cig,
            'cup': self.l10n_it_cup,
            'currency': self.currency_id or self.company_currency_id if not convert_to_euros else self.env.ref('base.EUR'),
            'document_total': document_total,
            'regime_fiscale': company.l10n_it_tax_system if not is_self_invoice else 'RF18',
            'is_self_invoice': is_self_invoice,
            'partner_bank': self.partner_bank_id,
            'formato_trasmissione': formato_trasmissione,
            'document_type': document_type,
            'tax_details': tax_details,
            'downpayment_moves': downpayment_moves,
            'rc_refund': reverse_charge_refund,
            'invoice_lines': invoice_lines,
            'tax_lines': tax_lines,
            'conversion_rate': conversion_rate,
            'balance_multiplicator': -1 if self.is_inbound() else 1,
            'abs': abs,
            'pdf_name': pdf_values['name'] if pdf_values else False,
            'pdf': b64encode(pdf_values['raw']).decode() if pdf_values else False,
        }

    def _l10n_it_edi_services_or_goods(self):
        """
            Services and goods have different tax grids when VAT is Reverse Charged, and they can't
            be mixed in the same invoice, because the TipoDocumento depends on which which kind
            of product is bought and it's unambiguous.
        """
        self.ensure_one()
        scopes = []
        for line in self.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_note', 'line_section')):
            tax_ids_with_tax_scope = line.tax_ids.filtered(lambda x: x.tax_scope)
            if tax_ids_with_tax_scope:
                scopes += tax_ids_with_tax_scope.mapped('tax_scope')
            else:
                scopes.append(line.product_id and line.product_id.type or 'consu')

        if set(scopes) == {'consu', 'service'}:
            return "both"
        return scopes and scopes.pop()

    def _l10n_it_edi_goods_in_italy(self):
        """
            There is a specific TipoDocumento (Document Type TD19) and tax grid (VJ3) for goods
            that are phisically in Italy but are in a VAT deposit, meaning that the goods
            have not passed customs.
        """
        self.ensure_one()
        invoice_lines_tags = self.line_ids.tax_tag_ids
        it_tax_report_vj3_lines = self.env['account.report.line'].search([
            ('report_id.country_id.code', '=', 'IT'),
            ('code', '=', 'VJ3'),
        ])
        vj3_lines_tags = it_tax_report_vj3_lines.expression_ids._get_matching_tags()
        return bool(invoice_lines_tags & vj3_lines_tags)

    def _l10n_it_edi_is_simplified(self):
        """
            Simplified Invoices are a way for the invoice issuer to create an invoice with limited data.
            Example: a consultant goes to the restaurant and wants the invoice instead of the receipt,
            to be able to deduct the expense from his Taxes. The Italian State allows the restaurant
            to issue a Simplified Invoice with the VAT number only, to speed up times, instead of
            requiring the address and other informations about the buyer.
            Only invoices under the threshold of 400 Euroes are allowed, to avoid this tool
            be abused for bigger transactions, that would enable less transparency to tax institutions.
        """
        self.ensure_one()
        template_reference = self.env.ref('l10n_it_edi.account_invoice_it_simplified_FatturaPA_export', raise_if_not_found=False)
        buyer = self.commercial_partner_id
        return bool(
            template_reference
            and not self.l10n_it_edi_is_self_invoice
            and self._l10n_it_edi_export_buyer_data_check()
            and (not buyer.country_id or buyer.country_id.code == 'IT')
            and (buyer.l10n_it_codice_fiscale or (buyer.vat and (buyer.vat[:2].upper() == 'IT' or buyer.vat[:2].isdecimal())))
            and self.amount_total <= 400
        )

    def _l10n_it_edi_features_for_document_type_selection(self):
        """ Returns a dictionary of features to be compared with the TDxx FatturaPA
            document type requirements. """
        partner_values = self.commercial_partner_id._l10n_it_edi_get_values()
        services_or_goods = self._l10n_it_edi_services_or_goods()
        return {
            'move_types': self.move_type,
            'partner_in_eu': partner_values.get('in_eu', False),
            'partner_country_code': partner_values.get('country_code', False),
            'simplified': self._l10n_it_edi_is_simplified(),
            'self_invoice': self.l10n_it_edi_is_self_invoice,
            'downpayment': self._is_downpayment(),
            'services_or_goods': services_or_goods,
            'goods_in_italy': services_or_goods == 'consu' and self._l10n_it_edi_goods_in_italy(),
        }

    def _l10n_it_edi_document_type_mapping(self):
        """ Returns a dictionary with the required features for every TDxx FatturaPA document type """
        return {
            'TD01': {'move_types': ['out_invoice'],
                     'import_type': 'in_invoice',
                     'self_invoice': False,
                     'simplified': False,
                     'downpayment': False},
            'TD02': {'move_types': ['out_invoice'],
                     'import_type': 'in_invoice',
                     'self_invoice': False,
                     'simplified': False,
                     'downpayment': True},
            'TD04': {'move_types': ['out_refund'],
                     'import_type': 'in_refund',
                     'self_invoice': False,
                     'simplified': False},
            'TD07': {'move_types': ['out_invoice'],
                     'import_type': 'in_invoice',
                     'self_invoice': False,
                     'simplified': True},
            'TD08': {'move_types': ['out_refund'],
                     'import_type': 'in_refund',
                     'self_invoice': False,
                     'simplified': True},
            'TD09': {'move_types': ['out_invoice'],
                     'import_type': 'in_invoice',
                     'self_invoice': False,
                     'simplified': True},
            'TD28': {'move_types': ['in_invoice', 'in_refund'],
                     'import_type': 'in_invoice',
                     'simplified': False,
                     'self_invoice': True,
                     'partner_country_code': "SM"},
            'TD17': {'move_types': ['in_invoice', 'in_refund'],
                     'import_type': 'in_invoice',
                     'simplified': False,
                     'self_invoice': True,
                     'services_or_goods': "service"},
            'TD18': {'move_types': ['in_invoice', 'in_refund'],
                     'import_type': 'in_invoice',
                     'simplified': False,
                     'self_invoice': True,
                     'services_or_goods': "consu",
                     'goods_in_italy': False,
                     'partner_in_eu': True},
            'TD19': {'move_types': ['in_invoice', 'in_refund'],
                     'import_type': 'in_invoice',
                     'simplified': False,
                     'self_invoice': True,
                     'services_or_goods': "consu",
                     'goods_in_italy': True},
        }

    def _l10n_it_edi_get_document_type(self):
        """ Compare the features of the invoice to the requirements of each TDxx FatturaPA
            document type until you find a valid one. """
        invoice_features = self._l10n_it_edi_features_for_document_type_selection()
        for code, document_type_features in self._l10n_it_edi_document_type_mapping().items():
            comparisons = []
            for key, invoice_feature in invoice_features.items():
                if key not in document_type_features:
                    continue
                document_type_feature = document_type_features.get(key)
                if isinstance(document_type_feature, list):
                    comparisons.append(invoice_feature in document_type_feature)
                else:
                    comparisons.append(invoice_feature == document_type_feature)
            if all(comparisons):
                return code
        return False

    def _l10n_it_edi_is_simplified_document_type(self, document_type):
        mapping = self._l10n_it_edi_document_type_mapping()
        return mapping.get(document_type, {}).get('simplified', False)

    # -------------------------------------------------------------------------
    # EDI: Import
    # -------------------------------------------------------------------------

    def cron_l10n_it_edi_download_and_update(self):
        """ Crons run with sudo(), with empty recordset. Remember that. """
        retrigger = False
        for proxy_user in self.env['account_edi_proxy_client.user'].search([('proxy_type', '=', 'l10n_it_edi')]):
            proxy_user = proxy_user.with_company(proxy_user.company_id)
            if proxy_user.edi_mode != 'demo':
                moves_to_check = self.search([
                    ('company_id', '=', proxy_user.company_id.id),
                    ('l10n_it_edi_transaction', '!=', False),
                    ('l10n_it_edi_state', 'in', WAITING_STATES)
                ])
                if moves_to_check:
                    moves_to_check._l10n_it_edi_update_send_state()
                retrigger = retrigger or self._l10n_it_edi_download_invoices(proxy_user)

        # Retrigger download if there are still some on the server
        if retrigger:
            _logger.info('Retriggering "Receive invoices from the SdI"...')
            self.env.ref('l10n_it_edi.ir_cron_l10n_it_edi_download_and_update')._trigger()

    def _l10n_it_edi_download_invoices(self, proxy_user):
        """ Check the proxy for incoming invoices for a specified proxy user.
            :return: True if there remain some invoices on the server to be downloaded, False otherwise.
        """
        server_url = proxy_user._get_server_url()

        # Download invoices
        invoices_data = {}
        try:
            invoices_data = proxy_user._make_request(f'{server_url}/api/l10n_it_edi/1/in/RicezioneInvoice',
                params={'recipient_codice_fiscale': proxy_user.company_id.l10n_it_codice_fiscale})
        except AccountEdiProxyError as e:
            _logger.error('Error while receiving invoices from the SdI: %s', e)
            return False

        # Process the downloaded invoices
        processed = self._l10n_it_edi_process_downloads(invoices_data, proxy_user)
        if processed['proxy_acks']:
            try:
                proxy_user._make_request(
                    f'{server_url}/api/l10n_it_edi/1/ack',
                    params={'transaction_ids': processed['proxy_acks']})
            except AccountEdiProxyError as e:
                _logger.error('Error while receiving file from the SdI: %s', e)

        return processed['retrigger']

    def _l10n_it_edi_process_downloads(self, invoices_data, proxy_user):
        """ Every attachment will be committed if stored succesfully.
            Also moves will be committed one by one, even if imported incorrectly.
        """
        proxy_acks = []
        retrigger = False
        moves = self.env['account.move']

        for id_transaction, invoice_data in invoices_data.items():

            # The IAP server has a maximum number of documents it can send.
            # If that maximum is reached, then we search for more
            # by re-triggering the download cron, avoiding the timeout.
            current_num = invoice_data.get('current_num', 0)
            max_num = invoice_data.get('max_num', 0)
            retrigger = retrigger or current_num == max_num > 0

            # `_l10n_it_edi_create_move_from_attachment` will create an empty move
            # then try and fill it with the content imported from the attachment.
            # Should the import fail, thanks to try..except and savepoint,
            # we will anyway end up with an empty `in_invoice` with the attachment posted on it.
            if move := self.with_company(self.company_id)._l10n_it_edi_create_move_with_attachment(
                invoice_data['filename'],
                invoice_data['file'],
                invoice_data['key'],
                proxy_user,
            ):
                self.env.cr.commit()
                moves |= move
                proxy_acks.append(id_transaction)

        # Extend created moves with the related attachments and commit
        for move in moves:
            move._extend_with_attachments(move.l10n_it_edi_attachment_id, new=True)
            self.env.cr.commit()

        return {"retrigger": retrigger, "proxy_acks": proxy_acks}

    def _l10n_it_edi_create_move_with_attachment(self, filename, content, key, proxy_user):
        """ Creates a move and save an incoming file from the SdI as its attachment.

            :param filename:       name of the file to be saved.
            :param content:        encrypted content of the file to be saved.
            :param key:            key to decrypt the file.
            :param proxy_user:     the AccountEdiProxyClientUser to use for decrypting the file
        """

        # Name should be unique, the invoice already exists
        Attachment = self.env['ir.attachment']
        if Attachment.search_count([
            ('name', '=', filename),
            ('res_model', '=', 'account.move'),
            ('res_field', '=', 'l10n_it_edi_attachment_file'),
        ], limit=1):
            _logger.warning('E-invoice already exists: %s', filename)
            return False

        # Decrypt with the server key
        try:
            decrypted_content = proxy_user._decrypt_data(content, key)
        except Exception as e: # noqa: BLE001
            _logger.warning("Cannot decrypt e-invoice: %s, %s", filename, e)
            return False

        # Create the attachment, an empty move, then attach the two and commit
        move = self.create({})
        attachment = Attachment.create({
            'name': filename,
            'raw': decrypted_content,
            'type': 'binary',
            'res_model': 'account.move',
            'res_id': move.id,
            'res_field': 'l10n_it_edi_attachment_file'
        })
        move.with_context(
            account_predictive_bills_disable_prediction=True,
            no_new_invoice=True,
        ).message_post(attachment_ids=attachment.ids)

        return move

    def _l10n_it_edi_search_partner(self, company, vat, codice_fiscale, email):
        for domain in [vat and [('vat', 'ilike', vat)],
                       codice_fiscale and [('l10n_it_codice_fiscale', 'in', ('IT' + codice_fiscale, codice_fiscale))],
                       email and ['|', ('email', '=', email), ('l10n_it_pec_email', '=', email)]]:
            if domain and (partner := self.env['res.partner'].search(
                    domain + self.env['res.partner']._check_company_domain(company), limit=1)):
                return partner
        return self.env['res.partner']

    def _l10n_it_edi_search_tax_for_import(self, company, percentage, extra_domain=None):
        """ Returns the VAT, Withholding or Pension Fund tax that suits the conditions given
            and matches the percentage found in the XML for the company. """
        domain = [
            *self.env['account.tax']._check_company_domain(company),
            ('amount', '=', percentage),
            ('amount_type', '=', 'percent'),
            ('type_tax_use', '=', 'purchase'),
        ] + (extra_domain or [])

        # As we're importing vendor bills, we're excluding Reverse Charge Taxes
        # which have a [100.0, 100.0, -100.0] repartition lines factor_percent distribution.
        # We only allow for taxes that have all positive repartition lines factor_percent distribution.
        taxes = self.env['account.tax'].search(domain).filtered(
            lambda tax: all(rep_line.factor_percent >= 0 for rep_line in tax.invoice_repartition_line_ids))

        return taxes[0] if taxes else taxes

    def _l10n_it_edi_get_extra_info(self, company, document_type, body_tree):
        """ This function is meant to collect other information that has to be inserted on the invoice lines by submodules.
            :return extra_info, messages_to_log"""
        return {'simplified': self.env['account.move']._l10n_it_edi_is_simplified_document_type(document_type)}, []

    def _l10n_it_edi_import_invoice(self, invoice, data, is_new):
        """ Decodes a l10n_it_edi move into an Odoo move.

        :param data:   the dictionary with the content to be imported
                       keys: 'filename', 'content', 'xml_tree', 'type', 'sort_weight'
        :param is_new: whether the move is newly created or to be updated
        :returns:      the imported move
        """
        tree = data['xml_tree']
        company = self.company_id

        # For unsupported document types, just assume in_invoice, and log that the type is unsupported
        document_type = get_text(tree, '//DatiGeneraliDocumento/TipoDocumento')
        move_type = self._l10n_it_edi_document_type_mapping().get(document_type, {}).get('import_type')
        if not move_type:
            move_type = "in_invoice"
            _logger.info('Document type not managed: %s. Invoice type is set by default.', document_type)

        self.move_type = move_type

        # Collect extra info from the XML that may be used by submodules to further put information on the invoice lines
        extra_info, message_to_log = self._l10n_it_edi_get_extra_info(company, document_type, tree)

        # Partner
        vat = get_text(tree, '//CedentePrestatore//IdCodice')
        codice_fiscale = get_text(tree, '//CedentePrestatore//CodiceFiscale')
        email = get_text(tree, '//DatiTrasmissione//Email')
        if partner := self._l10n_it_edi_search_partner(company, vat, codice_fiscale, email):
            self.partner_id = partner
        else:
            message = Markup("<br/>").join((
                _("Vendor not found, useful informations from XML file:"),
                self._compose_info_message(tree, '//CedentePrestatore')
            ))
            message_to_log.append(message)

        # Numbering attributed by the transmitter
        if progressive_id := get_text(tree, '//ProgressivoInvio'):
            self.payment_reference = progressive_id

        # Document Number
        if number := get_text(tree, './/DatiGeneraliDocumento//Numero'):
            self.ref = number

        # Currency
        if currency_str := get_text(tree, './/DatiGeneraliDocumento/Divisa'):
            currency = self.env.ref('base.%s' % currency_str.upper(), raise_if_not_found=False)
            if currency != self.env.company.currency_id and currency.active:
                self.currency_id = currency

        # Date
        if document_date := get_date(tree, './/DatiGeneraliDocumento/Data'):
            self.invoice_date = document_date
        else:
            message_to_log.append(_("Document date invalid in XML file: %s", document_date))

        # Stamp Duty
        if stamp_duty := get_text(tree, './/DatiGeneraliDocumento/DatiBollo/ImportoBollo'):
            self.l10n_it_stamp_duty = float(stamp_duty)

        # Comment
        for narration in get_text(tree, './/DatiGeneraliDocumento//Causale', many=True):
            self.narration = '%s%s<br/>' % (self.narration or '', narration)

        # Informations relative to the purchase order, the contract, the agreement,
        # the reception phase or invoices previously transmitted
        # <2.1.2> - <2.1.6>
        for document_type in ['DatiOrdineAcquisto', 'DatiContratto', 'DatiConvenzione', 'DatiRicezione', 'DatiFattureCollegate']:
            for element in tree.xpath('.//DatiGenerali/' + document_type):
                message = Markup("{} {}<br/>{}").format(document_type, _("from XML file:"), self._compose_info_message(element, '.'))
                message_to_log.append(message)

        #  Dati DDT. <2.1.8>
        if elements := tree.xpath('.//DatiGenerali/DatiDDT'):
            message = Markup("<br/>").join((
                _("Transport informations from XML file:"),
                self._compose_info_message(tree, './/DatiGenerali/DatiDDT')
            ))
            message_to_log.append(message)

        # Due date. <2.4.2.5>
        if due_date := get_date(tree, './/DatiPagamento/DettaglioPagamento/DataScadenzaPagamento'):
            self.invoice_date_due = fields.Date.to_string(due_date)
        else:
            message_to_log.append(_("Payment due date invalid in XML file: %s", str(due_date)))

        # Information related to the purchase order <2.1.2>
        if (po_refs := get_text(tree, '//DatiGenerali/DatiOrdineAcquisto/IdDocumento', many=True)):
            self.invoice_origin = ", ".join(po_refs)

        # Total amount. <2.4.2.6>
        if amount_total := sum([float(x) for x in get_text(tree, './/ImportoPagamento', many=True) if x]):
            message_to_log.append(_("Total amount from the XML File: %s", amount_total))

        # Bank account. <2.4.2.13>
        if self.move_type not in ('out_invoice', 'in_refund'):
            if acc_number := get_text(tree, './/DatiPagamento/DettaglioPagamento/IBAN'):
                if self.partner_id and self.partner_id.commercial_partner_id:
                    bank = self.env['res.partner.bank'].search([
                        ('acc_number', '=', acc_number),
                        ('partner_id', '=', self.partner_id.commercial_partner_id.id),
                        ('company_id', 'in', [self.company_id.id, False])
                    ], order='company_id', limit=1)
                else:
                    bank = self.env['res.partner.bank'].search([
                        ('acc_number', '=', acc_number),
                        ('company_id', 'in', [self.company_id.id, False])
                    ], order='company_id', limit=1)
                if bank:
                    self.partner_bank_id = bank
                else:
                    message = Markup("<br/>").join((
                        _("Bank account not found, useful informations from XML file:"),
                        self._compose_info_message(tree, [
                            './/DatiPagamento//Beneficiario',
                            './/DatiPagamento//IstitutoFinanziario',
                            './/DatiPagamento//IBAN',
                            './/DatiPagamento//ABI',
                            './/DatiPagamento//CAB',
                            './/DatiPagamento//BIC',
                            './/DatiPagamento//ModalitaPagamento'
                        ])
                    ))
                    message_to_log.append(message)
        elif elements := tree.xpath('.//DatiPagamento/DettaglioPagamento'):
            message = Markup("<br/>").join((
                _("Bank account not found, useful informations from XML file:"),
                self._compose_info_message(tree, './/DatiPagamento')
            ))
            message_to_log.append(message)

        # Invoice lines. <2.2.1>
        tag_name = './/DettaglioLinee' if not extra_info['simplified'] else './/DatiBeniServizi'
        for element in tree.xpath(tag_name):
            move_line = self.invoice_line_ids.create({
                'move_id': self.id,
                'tax_ids': [fields.Command.clear()]})
            if move_line:
                message_to_log += self._l10n_it_edi_import_line(element, move_line, extra_info)

        # Global discount summarized in 1 amount
        if discount_elements := tree.xpath('.//DatiGeneraliDocumento/ScontoMaggiorazione'):
            taxable_amount = float(self.tax_totals['amount_untaxed'])
            discounted_amount = taxable_amount
            for discount_element in discount_elements:
                discount_sign = 1
                if (discount_type := discount_element.xpath('.//Tipo')) and discount_type[0].text == 'MG':
                    discount_sign = -1
                if discount_amount := get_text(discount_element, './/Importo'):
                    discounted_amount -= discount_sign * float(discount_amount)
                    continue
                if discount_percentage := get_text(discount_element, './/Percentuale'):
                    discounted_amount *= 1 - discount_sign * float(discount_percentage) / 100

            general_discount = discounted_amount - taxable_amount
            sequence = len(elements) + 1

            self.invoice_line_ids = [Command.create({
                'sequence': sequence,
                'name': 'SCONTO' if general_discount < 0 else 'MAGGIORAZIONE',
                'price_unit': general_discount,
            })]

        for element in tree.xpath('.//Allegati'):
            attachment_64 = self.env['ir.attachment'].create({
                'name': get_text(element, './/NomeAttachment'),
                'datas': str.encode(get_text(element, './/Attachment')),
                'type': 'binary',
                'res_model': 'account.move',
                'res_id': self.id,
            })

            # no_new_invoice to prevent from looping on the.message_post that would create a new invoice without it
            self.with_context(no_new_invoice=True).sudo().message_post(
                body=(_("Attachment from XML")),
                attachment_ids=[attachment_64.id],
            )

        for message in message_to_log:
            self.sudo().message_post(body=message)
        return self

    def _l10n_it_edi_import_line(self, element, move_line, extra_info=None):
        extra_info = extra_info or {}
        company = move_line.company_id
        partner = move_line.partner_id
        message_to_log = []
        predict_enabled = self.env['ir.module.module'].search([('name', '=', 'account_accountant'), ('state', '=', 'installed')])

        # Sequence.
        line_elements = element.xpath('.//NumeroLinea')
        if line_elements:
            move_line.sequence = int(line_elements[0].text)

        # Name.
        move_line.name = " ".join(get_text(element, './/Descrizione').split())

        # Product.
        if elements_code := element.xpath('.//CodiceArticolo'):
            for element_code in elements_code:
                type_code = element_code.xpath('.//CodiceTipo')[0]
                code = element_code.xpath('.//CodiceValore')[0]
                product = self.env['product.product'].search([('barcode', '=', code.text)])
                if (product and type_code.text == 'EAN'):
                    move_line.product_id = product
                    break
                if partner:
                    product_supplier = self.env['product.supplierinfo'].search([('partner_id', '=', partner.id), ('product_code', '=', code.text)], limit=2)
                    if product_supplier and len(product_supplier) == 1 and product_supplier.product_id:
                        move_line.product_id = product_supplier.product_id
                        break
            if not move_line.product_id:
                for element_code in elements_code:
                    code = element_code.xpath('.//CodiceValore')[0]
                    product = self.env['product.product'].search([('default_code', '=', code.text)], limit=2)
                    if product and len(product) == 1:
                        move_line.product_id = product
                        break

        # If no product is found, try to find a product that may be fitting
        if predict_enabled and not move_line.product_id:
            fitting_product = move_line._predict_product()
            if fitting_product:
                name = move_line.name
                move_line.product_id = fitting_product
                move_line.name = name

        if predict_enabled:
            # Fitting account for the line
            fitting_account = move_line._predict_account()
            if fitting_account:
                move_line.account_id = fitting_account

        # Quantity.
        move_line.quantity = float(get_text(element, './/Quantita') or '1')

        # Taxes
        percentage = None
        if not extra_info['simplified']:
            percentage = get_float(element, './/AliquotaIVA')
            if price_unit := get_float(element, './/PrezzoUnitario'):
                move_line.price_unit = price_unit
        elif amount := get_float(element, './/Importo'):
            percentage = get_float(element, './/Aliquota')
            if not percentage and (tax_amount := get_float(element, './/Imposta')):
                percentage = round(tax_amount / (amount - tax_amount) * 100)
            move_line.price_unit = amount / (1 + percentage / 100)

        move_line.tax_ids = []
        if percentage is not None:
            l10n_it_exempt_reason = get_text(element, './/Natura') or False
            conditions = [('l10n_it_exempt_reason', '=', l10n_it_exempt_reason)]
            if tax := self._l10n_it_edi_search_tax_for_import(company, percentage, conditions):
                move_line.tax_ids += tax
            else:
                message = Markup("<br/>").join((
                    _("Tax not found for line with description '%s'", move_line.name),
                    self._compose_info_message(element, '.')
                ))
                message_to_log.append(message)

        # If no taxes were found, try to find taxes that may be fitting
        if predict_enabled and not move_line.tax_ids:
            fitting_taxes = move_line._predict_taxes()
            if fitting_taxes:
                move_line.tax_ids = [Command.set(fitting_taxes)]

        # Discounts
        if elements := element.xpath('.//ScontoMaggiorazione'):
            element = elements[0]
            # Special case of only 1 percentage discount
            if len(elements) == 1:
                if discount_percentage := get_float(element, './/Percentuale'):
                    discount_type = get_text(element, './/Tipo')
                    discount_sign = -1 if discount_type == 'MG' else 1
                    move_line.discount = discount_sign * discount_percentage
            # Discounts in cascade summarized in 1 percentage
            else:
                total = get_float(element, './/PrezzoTotale')
                discount = 100 - (100 * total) / (move_line.quantity * move_line.price_unit)
                move_line.discount = discount

        return message_to_log

    def _l10n_it_edi_format_errors(self, header, errors):
        return Markup('{}<ul class="mb-0">{}</ul>').format(
            nl2br_enclose(header, 'span') if header else '',
            Markup().join(nl2br_enclose(' '.join(error.split()), 'li') for error in errors)
        )

    def _compose_info_message(self, tree, tags):
        result = ""
        for tag in tags if isinstance(tags, list) else [tags]:
            for el in tree.xpath(tag):
                result += self._l10n_it_edi_format_errors("", [f'{subel.tag}: {subel.text}' for subel in el.iter()])
        return result

    # -------------------------------------------------------------------------
    # EDI: Export
    # -------------------------------------------------------------------------

    def _l10n_it_edi_export_data_check(self):
        errors = self._l10n_it_edi_base_export_data_check()
        if not self._l10n_it_edi_is_simplified():
            errors += self._l10n_it_edi_export_buyer_data_check()
        return errors

    def _l10n_it_edi_format_export_data_errors(self):
        messages = (
            self._l10n_it_edi_format_errors(move.name + ":" if len(self) > 1 else False, move_warnings)
            for move in self if (move_warnings := move._l10n_it_edi_export_data_check())
        )
        return Markup("<br>").join(messages) or False

    def _l10n_it_edi_base_export_data_check(self):
        errors = []
        seller = self.company_id
        buyer = self.commercial_partner_id
        is_self_invoice = self.l10n_it_edi_is_self_invoice
        if is_self_invoice:
            seller, buyer = buyer, seller

        # <1.1.1.1>
        if not seller.country_id:
            errors.append(_("%s must have a country", seller.display_name))

        # <1.1.1.2>
        if not self.company_id.vat:
            errors.append(_("%s must have a VAT number", seller.display_name))
        if seller.vat and len(seller.vat) > 30:
            errors.append(_("The maximum length for VAT number is 30. %s have a VAT number too long: %s.", seller.display_name, seller.vat))

        # <1.2.1.2>
        if not is_self_invoice and not seller.l10n_it_codice_fiscale:
            errors.append(_("%s must have a codice fiscale number", seller.display_name))

        # <1.2.1.8>
        if not is_self_invoice and not seller.l10n_it_tax_system:
            errors.append(_("The seller's company must have a tax system."))

        # <1.2.2>
        if not seller.street and not seller.street2:
            errors.append(_("%s must have a street.", seller.display_name))
        if not seller.zip:
            errors.append(_("%s must have a post code.", seller.display_name))
        elif len(seller.zip) != 5 and seller.country_id.code == 'IT':
            errors.append(_("%s must have a post code of length 5.", seller.display_name))
        if not seller.city:
            errors.append(_("%s must have a city.", seller.display_name))
        if not seller.country_id:
            errors.append(_("%s must have a country.", seller.display_name))

        if not is_self_invoice and seller.l10n_it_has_tax_representative and not seller.l10n_it_tax_representative_partner_id.vat:
            errors.append(_("Tax representative partner %s of %s must have a tax number.", seller.l10n_it_tax_representative_partner_id.display_name, seller.display_name))

        # <1.4.1>
        if not buyer.vat and not buyer.l10n_it_codice_fiscale and buyer.country_id.code == 'IT':
            errors.append(_("The buyer, %s, or his company must have a VAT number and/or a tax code (Codice Fiscale).", buyer.display_name))

        if is_self_invoice and self._l10n_it_edi_services_or_goods() == 'both':
            errors.append(_("Cannot apply Reverse Charge to a bill which contains both services and goods."))

        if is_self_invoice and not buyer.partner_id.l10n_it_pa_index:
            errors.append(_("Vendor bills sent as self-invoices to the SdI require a valid PA Index (Codice Destinatario) on the company's contact."))

        for tax_line in self.line_ids.filtered(lambda line: line.tax_line_id):
            if not tax_line.tax_line_id.l10n_it_exempt_reason and tax_line.tax_line_id.amount == 0:
                errors.append(_("%s has an amount of 0.0, you must indicate the kind of exoneration.", tax_line.name))

        if self.l10n_it_partner_pa:
            if not self.l10n_it_origin_document_type:
                errors.append(_("This invoice targets the Public Administration, please fill out"
                                " Origin Document Type field in the Electronic Invoicing tab."))
            if self.l10n_it_origin_document_date and self.l10n_it_origin_document_date > fields.Date.today():
                errors.append(_("The Origin Document Date cannot be in the future."))

        errors += self._l10n_it_edi_export_taxes_data_check()

        return errors

    def _l10n_it_edi_export_taxes_data_check(self):
        """
            Can be overridden by submodules like l10n_it_edi_withholding, which also allows for withholding and pension_fund taxes.
        """
        errors = []
        for invoice_line in self.invoice_line_ids.filtered(lambda x: x.display_type == 'product'):
            all_taxes = invoice_line.tax_ids.flatten_taxes_hierarchy()
            vat_taxes = all_taxes.filtered(lambda t: t.amount_type == 'percent' and t.amount >= 0)
            if len(vat_taxes) != 1:
                errors.append(_("In line %s, you must select one and only one VAT tax.", invoice_line.name))
        return errors

    def _l10n_it_edi_export_buyer_data_check(self):
        errors = []
        buyer = self.commercial_partner_id

        # <1.4.2>
        if not buyer.street and not buyer.street2:
            errors.append(_("%s must have a street.", buyer.display_name))
        if not buyer.country_id:
            errors.append(_("%s must have a country.", buyer.display_name))
        if not buyer.zip:
            errors.append(_("%s must have a post code.", buyer.display_name))
        elif len(buyer.zip) != 5 and buyer.country_id.code == 'IT':
            errors.append(_("%s must have a post code of length 5.", buyer.display_name))
        if not buyer.city:
            errors.append(_("%s must have a city.", buyer.display_name))

        for tax_line in self.line_ids.filtered(lambda line: line.tax_line_id):
            if not tax_line.tax_line_id.l10n_it_exempt_reason and tax_line.tax_line_id.amount == 0:
                errors.append(_("%s has an amount of 0.0, you must indicate the kind of exoneration.", tax_line.name))

        return errors

    def _l10n_it_edi_get_formatters(self):
        def format_alphanumeric(text, maxlen=None):
            if not text:
                return False
            text = text.encode('latin-1', 'replace').decode('latin-1')
            if maxlen and maxlen > 0:
                text = text[:maxlen]
            elif maxlen and maxlen < 0:
                text = text[maxlen:]
            return text

        def format_date(dt):
            # Format the date in the italian standard.
            dt = dt or datetime.now()
            return dt.strftime('%Y-%m-%d')

        def format_monetary(number, currency):
            # Format the monetary values to avoid trailing decimals (e.g. 90.85000000000001).
            return float_repr(number, min(2, currency.decimal_places))

        def format_numbers(number):
            #format number to str with between 2 and 8 decimals (event if it's .00)
            number_splited = str(number).split('.')
            if len(number_splited) == 1:
                return "%.02f" % number

            cents = number_splited[1]
            if len(cents) > 8:
                return "%.08f" % number
            return float_repr(number, max(2, len(cents)))

        def format_numbers_two(number):
            #format number to str with 2 (event if it's .00)
            return "%.02f" % number

        def format_phone(number):
            if not number:
                return False
            number = number.replace(' ', '').replace('/', '').replace('.', '')
            if len(number) > 4 and len(number) < 13:
                return format_alphanumeric(number)
            return False

        def format_address(street, street2, maxlen=60):
            street, street2 = street or '', street2 or ''
            if street and len(street) >= maxlen:
                street2 = ''
            sep = ' ' if street and street2 else ''
            return format_alphanumeric(f"{street}{sep}{street2}", maxlen)

        return {
            'format_date': format_date,
            'format_monetary': format_monetary,
            'format_numbers': format_numbers,
            'format_numbers_two': format_numbers_two,
            'format_phone': format_phone,
            'format_alphanumeric': format_alphanumeric,
            'format_address': format_address,
        }

    def _l10n_it_edi_render_xml(self, pdf_values=None):
        ''' Create the xml file content.
            :return:    The XML content as bytestring.
        '''
        qweb_template_name = (
            'l10n_it_edi.account_invoice_it_FatturaPA_export' if not self._l10n_it_edi_is_simplified()
            else 'l10n_it_edi.account_invoice_it_simplified_FatturaPA_export')
        xml_content = self.env['ir.qweb']._render(qweb_template_name, {
            **self._l10n_it_edi_get_values(pdf_values),
            **self._l10n_it_edi_get_formatters()})
        xml_node = cleanup_xml_node(xml_content, remove_blank_nodes=False)
        return etree.tostring(xml_node, xml_declaration=True, encoding='UTF-8')

    def _l10n_it_edi_get_attachment_values(self, pdf_values=None):
        self.ensure_one()
        return {
            'name': self._l10n_it_edi_generate_filename(),
            'type': 'binary',
            'mimetype': 'application/xml',
            'description': _('IT EDI e-move: %s', self.move_type),
            'company_id': self.company_id.id,
            'res_id': self.id,
            'res_model': self._name,
            'res_field': 'l10n_it_edi_attachment_file',
            'raw': self._l10n_it_edi_render_xml(pdf_values=pdf_values),
        }

    def _l10n_it_edi_generate_filename(self):
        '''Returns a name conform to the Fattura pa Specifications:
           See ES documentation 2.2
        '''
        a = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        # Each company should have its own filename sequence. If it does not exist, create it
        n = self.env['ir.sequence'].with_company(self.company_id).next_by_code('l10n_it_edi.fattura_filename')
        if not n:
            # The offset is used to avoid conflicts with existing filenames
            offset = 62 ** 4
            sequence = self.env['ir.sequence'].sudo().create({
                'name': 'FatturaPA Filename Sequence',
                'code': 'l10n_it_edi.fattura_filename',
                'company_id': self.company_id.id,
                'number_next': offset,
            })
            n = sequence._next()
        # The n is returned as a string, but we require an int
        n = int(''.join(filter(lambda c: c.isdecimal(), n)))

        progressive_number = ""
        while n:
            (n, m) = divmod(n, len(a))
            progressive_number = a[m] + progressive_number

        return '%(country_code)s%(codice)s_%(progressive_number)s.xml' % {
            'country_code': self.company_id.country_id.code,
            'codice': self.company_id.partner_id._l10n_it_edi_normalized_codice_fiscale(),
            'progressive_number': progressive_number.zfill(5),
        }

    def _l10n_it_edi_send(self, attachments_vals):
        files_to_upload = []
        filename_move = {}

        # Setup moves for sending
        for move in self:
            attachment_vals = attachments_vals[move]
            filename = attachment_vals['name']
            content = b64encode(attachment_vals['raw']).decode()
            move.l10n_it_edi_header = False
            if move.commercial_partner_id._l10n_it_edi_is_public_administration():
                move.l10n_it_edi_state = 'requires_user_signature'
                move.l10n_it_edi_transaction = False
                move.sudo().message_post(body=nl2br(escape(_(
                    "Sending invoices to Public Administration partners is not supported.\n"
                    "The IT EDI XML file is generated, please sign the document and upload it "
                    "through the 'Fatture e Corrispettivi' portal of the Tax Agency."
                ))))
            else:
                move.l10n_it_edi_state = 'being_sent'
                files_to_upload.append({'filename': filename, 'xml': content})
                filename_move[filename] = move

        # Upload files
        try:
            results = self._l10n_it_edi_upload(files_to_upload)
        except AccountEdiProxyError as e:
            messages_to_log = []
            for filename in filename_move:
                unsent_move = filename_move[filename]
                unsent_move.l10n_it_edi_state = False
                text_message = _("Error uploading the e-invoice file %s.\n%s", filename, e.message)
                html_message = nl2br(escape(text_message))
                unsent_move.l10n_it_edi_header = text_message
                unsent_move.sudo().message_post(body=html_message)
                messages_to_log.append(text_message)
            raise UserError("\n".join(messages_to_log)) from e

        # Handle results
        for filename, vals in results.items():
            sent_move = filename_move[filename]
            if 'error' in vals:
                sent_move.l10n_it_edi_state = False
                sent_move.l10n_it_edi_transaction = False
                message = nl2br(escape(_("Error uploading the e-invoice file %s.\n%s", filename, vals['error'])))
            else:
                is_demo = vals['id_transaction'] == 'demo'
                sent_move.l10n_it_edi_state = 'processing'
                sent_move.l10n_it_edi_transaction = vals['id_transaction']
                message = (
                    _("We are simulating the sending of the e-invoice file %s, as we are in demo mode.", filename)
                    if is_demo else _("The e-invoice file %s was sent to the SdI for processing.", filename))
            sent_move.l10n_it_edi_header = message
            sent_move.sudo().message_post(body=message)

    def _l10n_it_edi_upload(self, files):
        '''Upload files to the SdI.

        :param files:    A list of dictionary {filename, base64_xml}.
        :returns:        A dictionary.
        * message:       Message from fatturapa.
        * transactionId: The fatturapa ID of this request.
        * error:         An eventual error.
        '''
        if not files:
            return {}
        proxy_user = self.company_id.l10n_it_edi_proxy_user_id
        proxy_user.ensure_one()
        if proxy_user.edi_mode == 'demo':
            return {file_data['filename']: {'id_transaction': 'demo'} for file_data in files}

        ERRORS = {'EI01': _('Attached file is empty'),
                  'EI02': _('Service momentarily unavailable'),
                  'EI03': _('Unauthorized user')}

        server_url = proxy_user._get_server_url()
        results = proxy_user._make_request(
            f'{server_url}/api/l10n_it_edi/1/out/SdiRiceviFile',
            params={'files': files})

        for filename, vals in results.items():
            if 'error' in vals:
                results[filename]['error'] = ERRORS.get(vals.get('error'), _("Unknown error"))

        return results

    # -------------------------------------------------------------------------
    # EDI: Update notifications
    # -------------------------------------------------------------------------

    def _l10n_it_edi_update_send_state(self):
        ''' Check if the current invoices have been processed by the SdI. '''
        proxy_user = self.company_id.l10n_it_edi_proxy_user_id
        if proxy_user.edi_mode == 'demo':
            for move in self:
                filename = move.l10n_it_edi_attachment_id and move.l10n_it_edi_attachment_id.name or '???'
                self._l10n_it_edi_write_send_state(
                    transformed_notification={
                        'l10n_it_edi_state': 'forwarded',
                        'l10n_it_edi_transaction': f'demo_{uuid.uuid4()}',
                        'send_ack_to_edi_proxy': False,
                        'date': fields.Date.today(),
                        'filename': filename},
                    message=_("The e-invoice file %s has been sent in Demo EDI mode.", filename))
            return

        server_url = proxy_user._get_server_url()
        try:
            notifications = proxy_user._make_request(
                f'{server_url}/api/l10n_it_edi/1/in/TrasmissioneFatture',
                params={'ids_transaction': self.mapped("l10n_it_edi_transaction")})
        except AccountEdiProxyError as pe:
            raise UserError(_("An error occurred while downloading updates from the Proxy Server: (%s) %s", pe.code, pe.message)) from pe

        for _id_transaction, notification in notifications.items():
            encrypted_update_content = notification.get('file')
            encryption_key = notification.get('key')
            if (encrypted_update_content and encryption_key):
                notification['xml_content'] = proxy_user._decrypt_data(encrypted_update_content, encryption_key)

        acks = {'transaction_ids': [], 'states': []}
        for move in self:
            notification = notifications[move.l10n_it_edi_transaction]
            parsed_notification = move._l10n_it_edi_parse_notification(notification)
            transformed_notification = move._l10n_it_edi_transform_notification(parsed_notification)
            message = move._l10n_it_edi_get_message(transformed_notification)
            move._l10n_it_edi_write_send_state(transformed_notification, message)
            if (
                transformed_notification.get('send_ack_to_edi_proxy')
                and (id_transaction_to_ack := transformed_notification.get('l10n_it_edi_transaction'))
                and (ack_state := transformed_notification.get('l10n_it_edi_state'))
            ):
                acks['transaction_ids'].append(id_transaction_to_ack)
                acks['states'].append(ack_state)

        if acks:
            transaction_ids = acks['transaction_ids']
            states = acks['states']
            try:
                proxy_user._make_request(
                    f'{server_url}/api/l10n_it_edi/1/ack',
                    params={'transaction_ids': transaction_ids, 'states': states})
            except AccountEdiProxyError as pe:
                raise UserError(_("An error occurred while downloading updates from the Proxy Server: (%s) %s", pe.code, pe.message)) from pe

    def _l10n_it_edi_parse_notification(self, notification):
        sdi_state = notification.get('state', '')
        if not (xml_content := notification.get('xml_content')):
            return {'sdi_state': sdi_state}

        decrypted_update_content = etree.fromstring(xml_content)
        outcome = get_text(decrypted_update_content, './/Esito')
        date_arrival = get_datetime(decrypted_update_content, './/DataOraRicezione') or fields.Date.today()
        errors = [(
            get_text(error_element, '//Codice'),
            get_text(error_element, '//Descrizione'),
        ) for error_element in decrypted_update_content.xpath('//Errore')]
        filename = get_text(decrypted_update_content, './/NomeFile')

        return {
            'sdi_state': sdi_state,
            'errors': errors,
            'outcome': outcome,
            'date': date_arrival,
            'filename': filename,
        }

    def _l10n_it_edi_transform_notification(self, parsed_notification):
        """ Reads the notification XML coming from the EDI Proxy Server
            Recovers information about the new state.
            Computes whether the EDI Proxy Server is to be acked,
            and whether the id_transaction has to be reset.
        """
        self.ensure_one()
        state_map = {
            'not_found': False,
            'awaiting_outcome': 'processing',
            'notificaScarto': 'rejected',
            'ricevutaConsegna': 'forwarded',
            'forward_attempt': 'forward_attempt',
            'notificaMancataConsegna': 'forward_failed',
            ('notificaEsito', 'EC01'): 'accepted_by_pa_partner',
            ('notificaEsito', 'EC02'): 'rejected_by_pa_partner',
            'notificaDecorrenzaTermini': 'accepted_by_pa_partner_after_expiry',
        }
        sdi_state = parsed_notification['sdi_state']
        filename = parsed_notification.get('filename')
        errors = parsed_notification.get('errors', [])
        date = parsed_notification.get('date', fields.Date.today())
        if not filename and self.l10n_it_edi_attachment_id:
            filename = self.l10n_it_edi_attachment_id.name
        outcome = parsed_notification.get('outcome', False)
        if not outcome:
            new_state = state_map.get(sdi_state, False)
        else:
            new_state = state_map.get((sdi_state, outcome), False)

        parsed_notification.update({
            'l10n_it_edi_state': new_state,
            'l10n_it_edi_transaction': False if new_state in (False, 'rejected') else self.l10n_it_edi_transaction,
            'send_ack_to_edi_proxy': bool(new_state),
            'date': date,
            'errors': errors,
            'filename': filename,
        })
        return parsed_notification

    def _l10n_it_edi_write_send_state(self, transformed_notification, message):
        """ Update the record with the data coming from the IAP server.
            Eventually post the message.
            Commit the transaction.
        """
        self.ensure_one()
        old_state = self.l10n_it_edi_state
        new_state = transformed_notification['l10n_it_edi_state']
        self.write({
            'l10n_it_edi_state': new_state,
            'l10n_it_edi_transaction': transformed_notification['l10n_it_edi_transaction'],
            'l10n_it_edi_header': message or False,
        })

        if message and old_state != new_state:
            self.with_context(no_new_invoice=True).sudo().message_post(body=message)

        if new_state == 'rejected':
            self.l10n_it_edi_attachment_file = False

        self.env.cr.commit()

    def _l10n_it_edi_get_message(self, transformed_notification):
        """ The status change will be notified in the chatter of the move.
            Compute the message from the notification information coming from the EDI Proxy Server
        """
        self.ensure_one()
        partner = self.commercial_partner_id
        partner_name = partner.display_name
        filename = transformed_notification['filename']
        new_state = transformed_notification['l10n_it_edi_state']
        if new_state == 'rejected':
            DUPLICATE_MOVE = '00404'
            DUPLICATE_FILENAME = '00002'
            error_descriptions = []
            for error_code, error_description in transformed_notification['errors']:
                error_description_copy = error_description
                if error_code == DUPLICATE_MOVE:
                    error_description_copy = _(
                        "The e-invoice file %s is duplicated.\n"
                        "Original message from the SdI: %s",
                        filename, error_description_copy)
                elif error_code == DUPLICATE_FILENAME:
                    error_description_copy = _(
                        "The e-invoice filename %s is duplicated. Please check the FatturaPA Filename sequence.\n"
                        "Original message from the SdI: %s",
                        filename, error_description_copy)
                error_descriptions.append(error_description_copy)

            return self._l10n_it_edi_format_errors(_('The e-invoice has been refused by the SdI.'), error_descriptions)

        elif partner._l10n_it_edi_is_public_administration():
            pa_specific_map = {
                'forwarded': nl2br(escape(_(
                    "The e-invoice file %s was succesfully sent to the SdI.\n"
                    "%s has 15 days to accept or reject it.",
                    filename, partner_name))),
                'forward_attempt': nl2br(escape(_(
                    "The e-invoice file %s can't be forward to %s (Public Administration) by the SdI at the moment.\n"
                    "It will try again for 10 days, after which it will be considered accepted, but "
                    "you will still have to send it by post or e-mail.",
                    filename, partner_name))),
                'accepted_by_pa_partner_after_expiry': nl2br(escape(_(
                    "The e-invoice file %s is succesfully sent to the SdI. The invoice is now considered fiscally relevant.\n"
                    "The %s (Public Administration) had 15 days to either accept or refused this document,"
                    "but since they did not reply, it's now considered accepted.",
                    filename, partner_name))),
                'rejected_by_pa_partner': nl2br(escape(_(
                    "The e-invoice file %s has been refused by %s (Public Administration).\n"
                    "You have 5 days from now to issue a full refund for this invoice, "
                    "then contact the PA partner to create a new one according to their "
                    "requests and submit it.",
                    filename, partner_name))),
                'accepted_by_pa_partner': _(
                    "The e-invoice file %s has been accepted by %s (Public Administration), a payment will be issued soon",
                    filename, partner_name),
            }
            if pa_specific_message := pa_specific_map.get(new_state):
                return pa_specific_message

        new_state_messages_map = {
            False: _(
                "The e-invoice file %s has not been found on the EDI Proxy server.", filename),
            'processing': nl2br(escape(_(
                "The e-invoice file %s was sent to the SdI for validation.\n"
                "It is not yet considered accepted, please wait further notifications.",
                filename))),
            'forwarded': _(
                "The e-invoice file %s was accepted and succesfully forwarded it to %s by the SdI.",
                filename, partner_name),
            'forward_attempt': nl2br(escape(_(
                "The e-invoice file %s has been accepted by the SdI.\n"
                "The SdI is trying to forward it to %s.\n"
                "It will try for up to 2 days, after which you'll eventually "
                "need to send it the invoice to the partner by post or e-mail.",
                filename, partner_name))),
            'forward_failed': nl2br(escape(_(
                "The e-invoice file %s couldn't be forwarded to %s.\n"
                "Please remember to send it via post or e-mail.",
                filename, partner_name)))
        }
        return new_state_messages_map.get(new_state)
