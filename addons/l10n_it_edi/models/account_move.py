# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode
from datetime import datetime
import logging
from lxml import etree
import uuid

from odoo import _, api, Command, fields, models, modules
from odoo.addons.base.models.ir_qweb_fields import Markup, nl2br, nl2br_enclose
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_repr, cleanup_xml_node, float_is_zero

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
    if datetime_str := get_text(tree, xpath):
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
    l10n_it_stamp_duty = fields.Float(string="Dati Bollo")
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
            partner = move.commercial_partner_id
            move.l10n_it_partner_pa = partner and (partner._l10n_it_edi_is_public_administration() or len(partner.l10n_it_pa_index or '') == 7)

    @api.depends('move_type', 'line_ids.tax_tag_ids')
    def _compute_l10n_it_edi_is_self_invoice(self):
        """
            Italian EDI requires Vendor bills coming from EU countries to be sent as self-invoices.
            We recognize these cases based on the taxes that target the VJ tax grids, which imply
            the use of VAT External Reverse Charge.
        """
        purchases = self.filtered(lambda m: m.is_purchase_document())
        others = self - purchases
        for move in others:
            move.l10n_it_edi_is_self_invoice = False
        if purchases:
            it_tax_report_vj_lines = self.env['account.report.line'].sudo().search([
                ('report_id.country_id.code', '=', 'IT'),
                ('code', '=like', 'VJ%')
            ])
            vj_lines_tags = it_tax_report_vj_lines.expression_ids._get_matching_tags()
            for move in purchases:
                invoice_lines_tags = move.line_ids.tax_tag_ids
                ids_intersection = set(invoice_lines_tags.ids) & set(vj_lines_tags.ids)
                move.l10n_it_edi_is_self_invoice = bool(ids_intersection)

    def _l10n_it_edi_exempt_reason_tag_mapping(self):
        return {
            "N3.2": "VJ3",
            "N3.3": "VJ1",
            "N6.1": "VJ6",
            "N6.2": "VJ7",
            "N6.3": "VJ12",
            "N6.4": "VJ13",
            "N6.5": "VJ14",
            "N6.6": "VJ15",
            "N6.7": "VJ16",
            "N6.8": "VJ17",
        }

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
        self.with_context(skip_is_manually_modified=True).write({'l10n_it_edi_header': False})
        return super()._post(soft)

    def _extend_with_attachments(self, attachments, new=False):
        result = False
        # Prediction is an enterprise feature.
        if self._is_prediction_enabled():
            # Italy needs a custom order in prediction, since prediction generally deduces taxes
            # from products, while in Italian EDI, taxes are generally explicited in the XML file
            # while the product may not be labelled exactly the same as in the database
            l10n_it_attachments = attachments.filtered(lambda rec: rec._is_l10n_it_edi_import_file())
            if l10n_it_attachments:
                attachments = attachments - l10n_it_attachments
                result = super(AccountMove, self.with_context(disable_onchange_name_predictive=True))._extend_with_attachments(l10n_it_attachments, new)
        return result or super()._extend_with_attachments(attachments, new)

    # -------------------------------------------------------------------------
    # Business actions
    # -------------------------------------------------------------------------

    def action_l10n_it_edi_send(self):
        """ Checks that the invoice data is coherent.
            Attaches the XML file to the invoice.
            Sends the invoice to the SdI.
        """
        self.ensure_one()

        if errors := self._l10n_it_edi_export_data_check():
            messages = []
            for error_key, error_data in errors.items():
                message = error_data['message']
                split = error_key.split("_")
                if len(split) > 3 and (model_id := {
                    'partner': 'res.partner',
                    'move': 'account.move',
                    'company': 'res.company'
                }.get(split[3], None)):
                    if action := error_data.get('action'):
                        if 'res_id' in action:
                            record_ids = [action['res_id']]
                        else:
                            record_ids = action['domain'][0][2]
                        records = self.env[model_id].browse(record_ids)
                        message = f"{message} - {', '.join(records.mapped('display_name'))}"
                messages.append(nl2br(message))

            # Update the vendor bill's header with the warning messages,
            # and force reload the view to make sure the header is loaded
            self.l10n_it_edi_header = Markup('<br/>').join(messages)
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

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

    def _get_invoice_legal_documents(self, filetype, allow_fallback=False):
        # EXTENDS 'account'
        if filetype == 'fatturapa':
            if fatturapa_attachment := self.l10n_it_edi_attachment_id:
                return {
                    'filename': fatturapa_attachment.name,
                    'filetype': 'xml',
                    'content': fatturapa_attachment.raw,
                }
        return super()._get_invoice_legal_documents(filetype, allow_fallback=allow_fallback)

    def get_extra_print_items(self):
        # EXTENDS 'account' - add possibility to download all FatturaPA XML files
        print_items = super().get_extra_print_items()
        if self.l10n_it_edi_attachment_id:
            print_items.append({
                'key': 'download_xml_fatturapa',
                'description': _('XML FatturaPA'),
                **self.action_invoice_download_fatturapa(),
            })
        return print_items

    def action_invoice_download_fatturapa(self):
        if invoices_with_fatturapa := self.filtered('l10n_it_edi_attachment_id'):
            return {
                'type': 'ir.actions.act_url',
                'url': f'/account/download_invoice_documents/{",".join(map(str, invoices_with_fatturapa.ids))}/fatturapa',
                'target': 'download',
            }
        return False

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

    def _l10n_it_edi_add_base_lines_xml_values(self, base_lines_aggregated_values, is_downpayment):
        self.ensure_one()
        quantita_pd = min(self.env['account.move.line']._fields['quantity'].get_digits(self.env)[1], 8)
        for index, (base_line, aggregated_values) in enumerate(base_lines_aggregated_values, start=1):
            line = base_line['record']
            tax_details = base_line['tax_details']
            discount = base_line['discount']
            quantity = base_line['quantity']
            price_subtotal = base_line['price_subtotal'] = tax_details['raw_total_excluded_currency']
            it_values = base_line['it_values'] = {}

            # Description.
            # Down payment lines:
            # If there was a down paid amount that has been deducted from this move,
            # we need to put a reference to the down payment invoice in the DatiFattureCollegate tag
            description = line.name
            if not is_downpayment and price_subtotal < 0:
                downpayment_moves = line._get_downpayment_lines().move_id
                if downpayment_moves:
                    downpayment_moves_description = ', '.join(downpayment_moves.mapped('name'))
                    sep = ', ' if description else ''
                    description = f"{description}{sep}{downpayment_moves_description}"
            description = description or "NO NAME"

            # Price unit.
            if quantity:
                it_values['prezzo_unitario'] = base_line['gross_price_subtotal'] / quantity
            else:
                it_values['prezzo_unitario'] = 0.0

            # Discount.
            discount_list = it_values['sconto_maggiorazione_list'] = []
            delta_discount = base_line.get('discount_amount', 0.0) - base_line.get('discount_amount_before_dispatching', 0.0)
            if discount:
                discount_list.append({
                    'tipo': 'SC' if discount > 0 else 'MG',
                    'percentuale': abs(discount),
                    'importo': None,
                })
            if not base_line['currency_id'].is_zero(delta_discount):
                discount_list.append({
                    'tipo': 'SC',
                    'percentuale': None,
                    'importo': abs(delta_discount / (quantity or 1.0)),
                })

            # Tax rates.
            rates = it_values['aliquota_iva_list'] = []
            for values in aggregated_values.values():
                grouping_key = values['grouping_key']
                if not grouping_key or grouping_key['skip']:
                    continue

                rates.append(grouping_key['tax_amount_field'] if grouping_key['tax_amount_type_field'] == 'percent' else 0.0)

            # Tax exempt reason.
            vat_tax = base_line['tax_ids'].flatten_taxes_hierarchy().filtered(lambda t: t._l10n_it_filter_kind('vat') and t.amount >= 0)[:1]
            it_values['natura'] = vat_tax.l10n_it_exempt_reason or None

            # Other data.
            other_data_list = it_values['altri_dati_gestionali_list'] = []
            if base_line['currency_id'] != self.company_currency_id:
                other_data_list.extend([
                    {
                        'tipo_dato': 'DIVISA',
                        'riferimento_testo': base_line['currency_id'].name,
                        'riferimento_numero': tax_details['raw_total_excluded_currency'],
                        'riferimento_data': None,
                    },
                    {
                        'tipo_dato': 'CAMBIO',
                        'riferimento_testo': None,
                        'riferimento_numero': base_line['rate'],
                        'riferimento_data': self.invoice_date,
                    },
                ])

            it_values.update({
                'numero_linea': index,
                'descrizione': description,
                'prezzo_totale': tax_details['raw_total_excluded'],
                'quantita': quantity,
                'quantita_pd': quantita_pd,
                'ritenuta': None,
            })

    def _l10n_it_edi_get_tax_lines_xml_values(self, base_lines_aggregated_values, values_per_grouping_key):
        self.ensure_one()
        tax_lines = []
        for values in values_per_grouping_key.values():
            grouping_key = values['grouping_key']
            if not grouping_key or grouping_key['skip']:
                continue

            rounding = values['base_amount']
            for _base_line, aggregated_values in base_lines_aggregated_values:
                if grouping_key in aggregated_values:
                    rounding -= aggregated_values[grouping_key]['raw_base_amount']
            if float_is_zero(rounding, precision_digits=8):
                rounding = None

            tax_lines.append({
                'aliquota_iva': grouping_key['tax_amount_field'],
                'natura': grouping_key['l10n_it_exempt_reason'],
                'arrotondamento': rounding,
                'imponibile_importo': values['base_amount'],
                'imposta': values['tax_amount'],
                'esigibilita_iva': grouping_key['tax_exigibility_code'],
                'riferimento_normativo': grouping_key['l10n_it_law_reference'],
            })
        return tax_lines

    @api.model
    def _l10n_it_edi_is_neg_split_payment(self, tax_data):
        tax = tax_data['tax']
        return (
            tax.amount < 0.0
            and tax_data['group']
            and any(child_tax._l10n_it_is_split_payment() for child_tax in tax_data['group'].children_tax_ids)
        )

    @api.model
    def _l10n_it_edi_grouping_function_base_lines(self, base_line, tax_data):
        tax = tax_data['tax']
        return {
            'tax_amount_field': -23.0 if tax.amount == -11.5 else tax.amount,
            'tax_amount_type_field': tax.amount_type,
            'skip': tax_data['is_reverse_charge'] or self._l10n_it_edi_is_neg_split_payment(tax_data),
        }

    @api.model
    def _l10n_it_edi_grouping_function_tax_lines(self, base_line, tax_data):
        tax = tax_data['tax']

        if tax._l10n_it_is_split_payment():
            tax_exigibility_code = 'S'
        elif tax.tax_exigibility == 'on_payment':
            tax_exigibility_code = 'D'
        elif tax.tax_exigibility == 'on_invoice':
            tax_exigibility_code = 'I'
        else:
            tax_exigibility_code = None

        return {
            'tax_amount_field': -23.0 if tax.amount == -11.5 else tax.amount,
            'l10n_it_exempt_reason': tax.l10n_it_exempt_reason,
            'l10n_it_law_reference': tax.l10n_it_law_reference,
            'tax_exigibility_code': tax_exigibility_code,
            'tax_amount_type_field': tax.amount_type,
            'skip': tax_data['is_reverse_charge'] or self._l10n_it_edi_is_neg_split_payment(tax_data),
        }

    @api.model
    def _l10n_it_edi_grouping_function_total(self, base_line, tax_data):
        skip = tax_data['is_reverse_charge'] or self._l10n_it_edi_is_neg_split_payment(tax_data)
        return not skip

    def _l10n_it_edi_get_values(self, pdf_values=None):
        self.ensure_one()

        # Flags
        is_self_invoice = self.l10n_it_edi_is_self_invoice
        document_type = self._l10n_it_edi_get_document_type()

        # Represent if the document is a reverse charge refund in a single variable
        reverse_charge = document_type in ['TD16', 'TD17', 'TD18', 'TD19']
        is_downpayment = document_type in ['TD02']
        reverse_charge_refund = self.move_type == 'in_refund' and reverse_charge
        convert_to_euros = self.currency_id.name != 'EUR'

        # Base lines.
        base_amls = self.line_ids.filtered(lambda x: x.display_type == 'product')
        base_lines = [self._prepare_product_base_line_for_taxes_computation(x) for x in base_amls]
        tax_amls = self.line_ids.filtered(lambda x: x.display_type == 'tax')
        tax_lines = [self._prepare_tax_line_for_taxes_computation(x) for x in tax_amls]

        if reverse_charge_refund:
            for base_line in base_lines:
                base_line['price_unit'] *= -1

        AccountTax = self.env['account.tax']
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)

        downpayment_lines = []
        # Prepare for '_dispatch_negative_lines'
        for base_line in base_lines:
            tax_details = base_line['tax_details']
            discount = base_line['discount']
            price_unit = base_line['price_unit']
            quantity = base_line['quantity']
            price_subtotal = base_line['price_subtotal'] = tax_details['raw_total_excluded_currency']

            if discount == 100.0:
                gross_price_subtotal_before_discount = price_unit * quantity
            else:
                gross_price_subtotal_before_discount = price_subtotal / (1 - discount / 100.0)

            base_line['gross_price_subtotal'] = gross_price_subtotal_before_discount
            base_line['discount_amount_before_dispatching'] = gross_price_subtotal_before_discount - price_subtotal

            # The tax "23% Ritenuta Agenti e Rappresentanti" is not supported because it's supposed to be a tax of 23% based on
            # 50% of the base amount. It's currently implemented as a -11.5% tax. So on 1000, it gives an amount of -115.
            # We need to fix the base amount from 1000 to 500.0.
            for tax_data in tax_details['taxes_data']:
                tax = tax_data['tax']
                tax_data['_tax_amount'] = tax.amount
                if tax.amount == -11.5:
                    tax_data['_tax_amount'] = -23.0
                    tax_data['raw_base_amount'] *= 0.5
                    tax_data['raw_base_amount_currency'] *= 0.5

            if not is_downpayment:
                # Negative lines linked to down payment should stay negative
                line = base_line['record']
                if line.price_subtotal < 0 and line._get_downpayment_lines():
                    downpayment_lines.append(base_line)
                    base_lines.remove(base_line)

            if float_compare(quantity, 0, 2) < 0:
                # Negative quantity is refused by SDI, so we invert quantity and price_unit to keep the price_subtotal
                base_line.update({
                    'quantity': -quantity,
                    'price_unit': -price_unit,
                })

        dispatched_results = self.env['account.tax']._dispatch_negative_lines(base_lines)
        base_lines = dispatched_results['result_lines'] + dispatched_results['orphan_negative_lines'] + downpayment_lines
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id, tax_lines=tax_lines)
        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, self._l10n_it_edi_grouping_function_base_lines)
        self._l10n_it_edi_add_base_lines_xml_values(base_lines_aggregated_values, is_downpayment)
        base_lines = sorted(base_lines, key=lambda base_line: base_line['it_values']['numero_linea'])

        # Tax lines.
        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, self._l10n_it_edi_grouping_function_tax_lines)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        tax_lines = self._l10n_it_edi_get_tax_lines_xml_values(base_lines_aggregated_values, values_per_grouping_key)

        # Total of the document.
        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, self._l10n_it_edi_grouping_function_total)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        importo_totale_documento = 0.0
        for values in values_per_grouping_key.values():
            grouping_key = values['grouping_key']
            if grouping_key is False:
                continue
            importo_totale_documento += values['base_amount_currency']
            importo_totale_documento += values['tax_amount_currency']

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

        # Reference line for finding the conversion rate used in the document
        conversion_rate = float_repr(
            abs(self.amount_total / self.amount_total_signed), precision_digits=5,
        ) if convert_to_euros and self.invoice_line_ids else None

        # Reduce downpayment views to a single recordset
        downpayment_moves = self.invoice_line_ids._get_downpayment_lines().move_id

        return {
            'record': self,
            'base_lines': base_lines,
            'tax_lines': tax_lines,
            'importo_totale_documento': importo_totale_documento,
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
            'regime_fiscale': company.l10n_it_tax_system if not is_self_invoice else 'RF18',
            'is_self_invoice': is_self_invoice,
            'partner_bank': self.partner_bank_id,
            'formato_trasmissione': formato_trasmissione,
            'document_type': document_type,
            'payment_method': 'MP05',
            'downpayment_moves': downpayment_moves,
            'reconciled_moves': self._get_reconciled_invoices(),
            'rc_refund': reverse_charge_refund,
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
                scopes.append(line.product_id and line.product_id.type == 'service' and 'service' or 'consu')

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
        checks = ['partner_address_missing', 'partner_vat_codice_fiscale_missing']
        return bool(
            template_reference
            and not self.l10n_it_edi_is_self_invoice
            and list(buyer._l10n_it_edi_export_check(checks).keys()) == ['l10n_it_edi_partner_address_missing']
            and (not buyer.country_id or buyer.country_id.code == 'IT')
            and (buyer.l10n_it_codice_fiscale or (buyer.vat and (buyer.vat[:2].upper() == 'IT' or buyer.vat[:2].isdecimal())))
            and self.amount_total <= 400
        )

    def _l10n_it_edi_is_professional_fees(self):
        """
            This function returns a boolean value based on the comparison of the lines values with a product.
            If one line has the tag for professional fee then we return True
        """
        self.ensure_one()
        professional_fee_tag = self.env.ref('l10n_it_edi.l10n_it_edi_professional_fees_tag', raise_if_not_found=False)
        if not professional_fee_tag:
            return False

        return any(
            professional_fee_tag.id in line.account_id.tag_ids.ids
            for line in self.invoice_line_ids
            if line.display_type not in ('line_note', 'line_section')
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
            'tax_tags': {tag for tag in self.line_ids.tax_tag_ids.mapped(lambda x: (x.name or '').upper().replace("+", "").replace("-", "")) if tag},
            'downpayment': self._is_downpayment(),
            'services_or_goods': services_or_goods,
            'goods_in_italy': services_or_goods == 'consu' and self._l10n_it_edi_goods_in_italy(),
            'professional_fees': self._l10n_it_edi_is_professional_fees(),
        }

    def _l10n_it_edi_document_type_mapping(self):
        """ Returns a dictionary with the required features for every TDxx FatturaPA document type """
        return {
            'TD01': {'move_types': ['out_invoice'],
                     'import_type': 'in_invoice',
                     'self_invoice': False,
                     'simplified': False,
                     'downpayment': False,
                     'professional_fees': False},
            'TD02': {'move_types': ['out_invoice'],
                     'import_type': 'in_invoice',
                     'self_invoice': False,
                     'simplified': False,
                     'downpayment': True,
                     'professional_fees': False},
            'TD03': {'move_types': ['out_invoice'],
                     'import_type': 'in_invoice',
                     'self_invoice': False,
                     'simplified': False,
                     'downpayment': True,
                     'professional_fees': True},
            'TD04': {'move_types': ['out_refund'],
                     'import_type': 'in_refund',
                     'self_invoice': False,
                     'simplified': False},
            'TD05': {'move_types': ['out_refund'],
                     'import_type': 'in_refund',
                     'self_invoice': False,
                     'simplified': False},
            'TD06': {'move_types': ['out_invoice'],
                     'import_type': 'in_invoice',
                     'self_invoice': False,
                     'simplified': False,
                     'downpayment': False,
                     'professional_fees': True},
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
            'TD16': {'move_types': ['in_invoice', 'in_refund'],
                     'import_type': 'in_invoice',
                     'simplified': False,
                     'self_invoice': True,
                     'tax_tags': {'VJ6', 'VJ7', 'VJ8', 'VJ12', 'VJ13', 'VJ14', 'VJ15', 'VJ16', 'VJ17'}},
            'TD17': {'move_types': ['in_invoice', 'in_refund'],
                     'import_type': 'in_invoice',
                     'simplified': False,
                     'self_invoice': True,
                     'services_or_goods': "service",
                     'tax_tags': {'VJ3'}},
            'TD18': {'move_types': ['in_invoice', 'in_refund'],
                     'import_type': 'in_invoice',
                     'simplified': False,
                     'self_invoice': True,
                     'services_or_goods': "consu",
                     'goods_in_italy': False,
                     'partner_in_eu': True,
                     'tax_tags': {'VJ9'}},
            'TD19': {'move_types': ['in_invoice', 'in_refund'],
                     'import_type': 'in_invoice',
                     'simplified': False,
                     'self_invoice': True,
                     'services_or_goods': "consu",
                     'goods_in_italy': True,
                     'tax_tags': {'VJ3'}},
        }

    def _l10n_it_edi_get_document_type(self):
        """ Compare the features of the invoice to the requirements of each Document Type (TDxx)
        FatturaPA until you find a valid one. """

        def compare(actual_values, expected_values):
            """ Compare a single entry from the invoice features with the one of the document_type """
            if isinstance(expected_values, set | list | tuple):
                # i.e. When we compare actual tax_tags from the invoice with expected tags, we see if there is at least one in common
                if isinstance(actual_values, set):
                    return actual_values & set(expected_values)
                # i.e. When we compare the move_type with the available ones, these can be more than one
                return actual_values in expected_values
            # We compare other features directly, one on one
            return actual_values == expected_values

        invoice_features = self._l10n_it_edi_features_for_document_type_selection()
        for document_type_code, document_type_features in self._l10n_it_edi_document_type_mapping().items():
            # By using a generator instead of a list, we can avoid some comparisons
            if all(compare(invoice_values, document_type_features[k]) for k, invoice_values in invoice_features.items() if k in document_type_features):
                return document_type_code
        return False

    def _l10n_it_edi_is_simplified_document_type(self, document_type):
        mapping = self._l10n_it_edi_document_type_mapping()
        return mapping.get(document_type, {}).get('simplified', False)

    @api.model
    def _l10n_it_buyer_seller_info(self):
        return {
            'buyer': {
                'role': 'buyer',
                'section_xpath': '//CessionarioCommittente',
                'vat_xpath': '//CessionarioCommittente//IdCodice',
                'codice_fiscale_xpath': '//CessionarioCommittente//CodiceFiscale',
                'type_tax_use_domain': [('type_tax_use', '=', 'purchase')],
            },
            'seller': {
                'role': 'seller',
                'section_xpath': '//CedentePrestatore',
                'vat_xpath': '//CedentePrestatore//IdCodice',
                'codice_fiscale_xpath': '//CedentePrestatore//CodiceFiscale',
                'type_tax_use_domain': [('type_tax_use', '=', 'sale')],
            },
        }

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
            if move := self.with_company(proxy_user.company_id)._l10n_it_edi_create_move_with_attachment(
                invoice_data['filename'],
                invoice_data['file'],
                invoice_data['key'],
                proxy_user,
            ):

                if not modules.module.current_test:
                    self.env.cr.commit()
                moves |= move
            proxy_acks.append(id_transaction)

        # Extend created moves with the related attachments and commit
        for move in moves:
            move._extend_with_attachments(move.l10n_it_edi_attachment_id, new=True)
            if not modules.module.current_test:
                self.env.cr.commit()

        return {"retrigger": retrigger, "proxy_acks": proxy_acks}

    def _l10n_it_edi_create_move_with_attachment(self, filename, content, key, proxy_user):
        """ Creates a move and save an incoming file from the SdI as its attachment.

            :param filename:       name of the file to be saved.
            :param content:        encrypted content of the file to be saved.
            :param key:            key to decrypt the file.
            :param proxy_user:     the AccountEdiProxyClientUser to use for decrypting the file
        """

        # Name should be unique per company, the invoice already exists
        Attachment = self.env['ir.attachment'].sudo().with_company(proxy_user.company_id)
        if Attachment.search_count([
            ('name', '=', filename),
            ('res_model', '=', 'account.move'),
            ('res_field', '=', 'l10n_it_edi_attachment_file'),
            ('company_id', '=', proxy_user.company_id.id),
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
        move = self.with_company(proxy_user.company_id).create({})
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

    def _l10n_it_edi_search_tax_for_import(self, company, percentage, extra_domain=None, l10n_it_exempt_reason=None):
        """ Returns the VAT, Withholding or Pension Fund tax that suits the conditions given
            and matches the percentage found in the XML for the company. """

        # The tax "23% Ritenuta Agenti e Rappresentanti" is not supported because it's supposed to be a tax of 23% based on
        # 50% of the base amount. It's currently implemented as a -11.5% tax. So on 1000, it gives an amount of -115.
        # We need to fix the base amount from 1000 to 500.0.
        if percentage == -23.0:
            percentage = -11.5

        domain = [
            *self.env['account.tax']._check_company_domain(company),
            ('amount_type', '=', 'percent'),
        ] + (extra_domain or [])

        # We suppose we're importing a file that comes in as a customer invoice where the sale tax will be 0%.
        # To retrieve the correct purchase tax, we examine the sale tax's l10n_it_exempt_reason.
        # We determine whether the l10n_it_exempt_reason is specific to reverse charge.
        reversed_tax_tag = self._l10n_it_edi_exempt_reason_tag_mapping().get(l10n_it_exempt_reason, '')
        if not reversed_tax_tag:
            # Normal VAT taxes have a known percentage and generally have all positive repartition lines
            domain += [('amount', '=', percentage), ('l10n_it_exempt_reason', '=', l10n_it_exempt_reason)]
            taxes = self.env['account.tax'].search(domain).filtered(
                lambda tax: all(rep_line.factor_percent >= 0 for rep_line in tax.invoice_repartition_line_ids))
        else:
            # In case of reverse charge, the purchase tax has a negative repartition line.
            domain += [('invoice_repartition_line_ids.tag_ids.name', '=', f'+{reversed_tax_tag.lower()}')]
            taxes = self.env['account.tax'].search(domain, order="amount desc").filtered(
                lambda tax: any(rep_line.factor_percent < 0 for rep_line in tax.invoice_repartition_line_ids))

        return taxes[0] if taxes else taxes

    def _l10n_it_edi_get_extra_info(self, company, document_type, body_tree, incoming=True):
        """ This function is meant to collect other information that has to be inserted on the invoice lines by submodules.
            :return extra_info, messages_to_log"""
        return {
            'simplified': self.env['account.move']._l10n_it_edi_is_simplified_document_type(document_type),
            'type_tax_use_domain': [('type_tax_use', '=', 'purchase' if incoming else 'sale')],
        }, []

    def _l10n_it_edi_import_invoice(self, invoice, data, is_new):
        """ Decodes a l10n_it_edi move into an Odoo move.

        :param data:   the dictionary with the content to be imported
                       keys: 'filename', 'content', 'xml_tree', 'type', 'sort_weight'
        :param is_new: whether the move is newly created or to be updated
        :returns:      the imported move
        """
        with self._get_edi_creation() as self:
            buyer_seller_info = self._l10n_it_buyer_seller_info()

            tree = data['xml_tree']
            company = self.company_id

            # There are 2 cases:
            # - cron:
            #     * Move direction (incoming / outgoing) flexible (no 'default_move_type')
            #     * I.e. used for import from tax agency
            # - "Upload" button (invoices / bills view)
            #     * Fixed move direction; the button sets the 'default_move_type'
            default_move_type = self.env.context.get('default_move_type')
            if default_move_type is None:
                incoming_possibilities = [True, False]
            elif default_move_type in invoice.get_purchase_types(include_receipts=True):
                incoming_possibilities = [True]
            elif default_move_type in invoice.get_sale_types(include_receipts=True):
                incoming_possibilities = [False]
            else:
                _logger.warning("Cannot handle default_move_type '%s'.", default_move_type)
                return

            for incoming in incoming_possibilities:
                company_role, partner_role = ('buyer', 'seller') if incoming else ('seller', 'buyer')
                company_info = buyer_seller_info[company_role]
                vat = get_text(tree, company_info['vat_xpath'])
                if vat and vat .casefold() in (company.vat or '').casefold():
                    break
                codice_fiscale = get_text(tree, company_info['codice_fiscale_xpath'])
                if codice_fiscale and codice_fiscale.casefold() in (company.l10n_it_codice_fiscale or '').casefold():
                    break
            else:
                invoice.message_post(body=_("Your company's VAT number and Fiscal Code haven't been found in the buyer and/or seller sections inside the document."))
                return

            # For unsupported document types, just assume in_invoice, and log that the type is unsupported
            document_type = get_text(tree, '//DatiGeneraliDocumento/TipoDocumento')
            move_type = self._l10n_it_edi_document_type_mapping().get(document_type, {}).get('import_type')
            if not move_type:
                move_type = "in_invoice"
                _logger.info('Document type not managed: %s. Invoice type is set by default.', document_type)
            if not incoming and move_type.startswith('in_'):
                move_type = 'out' + move_type[2:]

            self.move_type = move_type

            if self.name and self.name != '/':
                # the journal might've changed, so we need to recompute the name in case it was set (first entry in journal)
                self.name = False
                self._compute_name()

            # Collect extra info from the XML that may be used by submodules to further put information on the invoice lines
            extra_info, message_to_log = self._l10n_it_edi_get_extra_info(company, document_type, tree, incoming=incoming)

            # Partner
            partner_info = buyer_seller_info[partner_role]
            vat = get_text(tree, partner_info['vat_xpath'])
            codice_fiscale = get_text(tree, partner_info['codice_fiscale_xpath'])
            email = get_text(tree, '//DatiTrasmissione//Email') if partner_info['role'] == 'seller' else ''
            if partner := self._l10n_it_edi_search_partner(company, vat, codice_fiscale, email):
                self.partner_id = partner
            else:
                message = Markup("<br/>").join((
                    _("Partner not found, useful informations from XML file:"),
                    self._compose_info_message(tree, partner_info['section_xpath'])
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
            if amount_total := sum(float(x) for x in get_text(tree, './/ImportoPagamento', many=True) if x):
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
                taxable_amount = float(self.tax_totals['base_amount_currency'])
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

    @api.model
    def _is_prediction_enabled(self):
        return self.env['ir.module.module'].search([('name', '=', 'account_accountant'), ('state', '=', 'installed')])

    def _l10n_it_edi_import_line(self, element, move_line, extra_info=None):
        extra_info = extra_info or {}
        company = move_line.company_id
        partner = move_line.partner_id
        message_to_log = []
        predict_enabled = self._is_prediction_enabled()

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
            l10n_it_exempt_reason = get_text(element, './/Natura').upper() or False
            extra_domain = extra_info.get('type_tax_use_domain', [('type_tax_use', '=', 'purchase')])
            if tax := self._l10n_it_edi_search_tax_for_import(company, percentage, extra_domain, l10n_it_exempt_reason=l10n_it_exempt_reason):
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
            # Special case of only 1 percentage discount
            if len(elements) == 1:
                element = elements[0]
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
        """ This function checks the Settings, Company, Partners, Moves involved in the
            sending activity and returns an errors dictionary ready for the
            actionable_errors widget to display. """

        companies = self.mapped("company_id")
        companies_partners = companies.mapped("partner_id")
        moves_full = self.filtered(lambda m: not m._l10n_it_edi_is_simplified())
        moves_simplified = self.filtered(lambda m: m._l10n_it_edi_is_simplified())

        full = moves_full.mapped("commercial_partner_id").filtered(lambda p: p not in companies_partners)
        simplified = moves_simplified.mapped("commercial_partner_id").filtered(lambda p: p not in companies_partners | full)
        representatives = companies.mapped("l10n_it_tax_representative_partner_id").filtered(lambda p: p not in companies_partners | simplified | full)

        return {
            **companies._l10n_it_edi_export_check(),
            **full._l10n_it_edi_export_check(['partner_address_missing']),
            **simplified._l10n_it_edi_export_check(['partner_country_missing']),
            **(simplified | full)._l10n_it_edi_export_check(['partner_vat_codice_fiscale_missing']),
            **representatives._l10n_it_edi_export_check(['partner_vat_missing']),
            **self._l10n_it_edi_base_export_check(),
            **self._l10n_it_edi_export_taxes_check(),
        }

    def _l10n_it_edi_base_export_check(self):
        def build_error(message, records):
            return {
                'message': message,
                **({
                    'action_text': _("View invoice(s)"),
                    'action': records._get_records_action(name=_("Invoice(s) to check")),
                } if len(self) > 1 else {})
            }

        errors = {}
        if moves := self.filtered(lambda move: move.l10n_it_edi_is_self_invoice and move._l10n_it_edi_services_or_goods() == 'both'):
            errors['l10n_it_edi_move_rc_mixed_product_types'] = build_error(
                message=_("Cannot apply Reverse Charge to bills which contains both services and goods."),
                records=moves)

        if pa_moves := self.filtered(lambda move: move.commercial_partner_id._l10n_it_edi_is_public_administration()):
            if moves := pa_moves.filtered(lambda move: not move.l10n_it_origin_document_type):
                message = _("Partner(s) belongs to the Public Administration, please fill out Origin Document Type field in the Electronic Invoicing tab.")
                errors['move_missing_origin_document'] = build_error(message=message, records=moves)
            if moves := pa_moves.filtered(lambda move: move.l10n_it_origin_document_date and move.l10n_it_origin_document_date > fields.Date.today()):
                message = _("The Origin Document Date cannot be in the future.")
                errors['l10n_it_edi_move_future_origin_document_date'] = build_error(message=message, records=moves)
        if pa_moves := self.filtered(lambda move: len(move.commercial_partner_id.l10n_it_pa_index or '') == 7):
            if moves := pa_moves.filtered(lambda move: not move.l10n_it_origin_document_type and move.l10n_it_cig and move.l10n_it_cup):
                message = _("CIG/CUP fields of partner(s) are present, please fill out Origin Document Type field in the Electronic Invoicing tab.")
                errors['move_missing_origin_document_field'] = build_error(message=message, records=moves)
        return errors

    def _l10n_it_edi_export_taxes_check(self):
        if move_lines := self.mapped("invoice_line_ids").filtered(lambda line:
            line.display_type == 'product'
            and len(line.tax_ids.flatten_taxes_hierarchy()._l10n_it_filter_kind('vat')) != 1
        ):
            return {
                'l10n_it_edi_move_only_one_vat_tax_per_line': {
                    'message': _("Invoices must have exactly one VAT tax set per line."),
                    **({
                        'action_text': _("View invoice(s)"),
                        'action': move_lines.mapped("move_id")._get_records_action(name=_("Check taxes on invoice lines")),
                    } if len(self) > 1 else {})
                }}
        return {}

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

        def format_float(amount, precision):
            if amount is None or amount is False:
                return None
            # Avoid things like -0.0, see: https://stackoverflow.com/a/11010869
            return '%.*f' % (precision, amount if not float_is_zero(amount, precision_digits=precision) else 0.0)

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
            'format_float': format_float,
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
                move.sudo().message_post(body=nl2br(_(
                    "Sending invoices to Public Administration partners is not supported.\n"
                    "The IT EDI XML file is generated, please sign the document and upload it "
                    "through the 'Fatture e Corrispettivi' portal of the Tax Agency."
                )))
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
                text_message = _("Error uploading the e-invoice file %(file)s.\n%(error)s", file=filename, error=e.message)
                html_message = nl2br(text_message)
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
                message = nl2br(_("Error uploading the e-invoice file %(file)s.\n%(error)s", file=filename, error=vals['error']))
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
            raise UserError(_("An error occurred while downloading updates from the Proxy Server: (%(code)s) %(message)s", code=pe.code, message=pe.message)) from pe

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
                raise UserError(_("An error occurred while downloading updates from the Proxy Server: (%(code)s) %(message)s", code=pe.code, message=pe.message)) from pe

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
                        "The e-invoice file %(file)s is duplicated.\n"
                        "Original message from the SdI: %(message)s",
                        file=filename, message=error_description_copy)
                elif error_code == DUPLICATE_FILENAME:
                    error_description_copy = _(
                        "The e-invoice filename %(file)s is duplicated. Please check the FatturaPA Filename sequence.\n"
                        "Original message from the SdI: %(message)s",
                        file=filename, message=error_description_copy)
                error_descriptions.append(error_description_copy)

            return self._l10n_it_edi_format_errors(_('The e-invoice has been refused by the SdI.'), error_descriptions)

        elif partner._l10n_it_edi_is_public_administration():
            pa_specific_map = {
                'forwarded': nl2br(_(
                    "The e-invoice file %(file)s was succesfully sent to the SdI.\n"
                    "%(partner)s has 15 days to accept or reject it.",
                    file=filename, partner=partner_name)),
                'forward_attempt': nl2br(_(
                    "The e-invoice file %(file)s can't be forward to %(partner)s (Public Administration) by the SdI at the moment.\n"
                    "It will try again for 10 days, after which it will be considered accepted, but "
                    "you will still have to send it by post or e-mail.",
                    file=filename, partner=partner_name)),
                'accepted_by_pa_partner_after_expiry': nl2br(_(
                    "The e-invoice file %(file)s is succesfully sent to the SdI. The invoice is now considered fiscally relevant.\n"
                    "The %(partner)s (Public Administration) had 15 days to either accept or refused this document,"
                    "but since they did not reply, it's now considered accepted.",
                    file=filename, partner=partner_name)),
                'rejected_by_pa_partner': nl2br(_(
                    "The e-invoice file %(file)s has been refused by %(partner)s (Public Administration).\n"
                    "You have 5 days from now to issue a full refund for this invoice, "
                    "then contact the PA partner to create a new one according to their "
                    "requests and submit it.",
                    file=filename, partner=partner_name)),
                'accepted_by_pa_partner': _(
                    "The e-invoice file %(file)s has been accepted by %(partner)s (Public Administration), a payment will be issued soon",
                    file=filename, partner=partner_name),
            }
            if pa_specific_message := pa_specific_map.get(new_state):
                return pa_specific_message

        new_state_messages_map = {
            False: _(
                "The e-invoice file %s has not been found on the EDI Proxy server.", filename),
            'processing': nl2br(_(
                "The e-invoice file %s was sent to the SdI for validation.\n"
                "It is not yet considered accepted, please wait further notifications.",
                filename)),
            'forwarded': _(
                "The e-invoice file %(file)s was accepted and succesfully forwarded it to %(partner)s by the SdI.",
                file=filename, partner=partner_name),
            'forward_attempt': nl2br(_(
                "The e-invoice file %(file)s has been accepted by the SdI.\n"
                "The SdI is trying to forward it to %(partner)s.\n"
                "It will try for up to 2 days, after which you'll eventually "
                "need to send it the invoice to the partner by post or e-mail.",
                file=filename, partner=partner_name)),
            'forward_failed': nl2br(_(
                "The e-invoice file %(file)s couldn't be forwarded to %(partner)s.\n"
                "Please remember to send it via post or e-mail.",
                file=filename, partner=partner_name))
        }
        return new_state_messages_map.get(new_state)
