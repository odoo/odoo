# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from lxml import etree
from markupsafe import escape
import uuid

from odoo import _, api, fields, models
from odoo.tools import float_compare, float_repr
from odoo.exceptions import UserError
from odoo.addons.base.models.ir_qweb_fields import nl2br
from odoo.addons.l10n_it_edi.tools.xml_utils import get_text, get_datetime, format_errors

_logger = logging.getLogger(__name__)


WAITING_STATES = ['processing', 'forward_attempt_failed']


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_edi_state = fields.Selection([
        ('being_sent', 'Being Sent To SdI'),
        ('requires_user_signature', 'Requires user signature'),
        ('processing', 'SdI Processing'),
        ('rejected', 'SdI Rejected'),
        ('forwarded', 'SdI Accepted, Forwarded to Partner'),
        ('forward_failed', 'SdI Accepted, Forward to Partner Failed'),
        ('forward_attempt_failed', 'SdI Accepted, Forward Attempt Failed'),
        ('accepted_by_pa_partner', 'SdI Accepted, Accepted by the PA Partner'),
        ('rejected_by_pa_partner', 'SdI Accepted, Rejected by the PA Partner'),
        ('accepted_by_pa_partner_after_expiry', 'SdI Accepted, PA Partner Expired Terms'),
    ], copy=False, tracking=True, readonly=True)
    l10n_it_edi_header = fields.Html(
        help='User description of the current state, with hints to make the flow progress',
        readonly=True,
        copy=False)
    l10n_it_edi_transaction = fields.Char(copy=False, string="FatturaPA Transaction")
    l10n_it_edi_attachment_file = fields.Binary(copy=False, attachment=True)
    l10n_it_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="FatturaPA Attachment",
        compute=lambda self: self._compute_linked_attachment_id('l10n_it_edi_attachment_id', 'l10n_it_edi_attachment_file'),
        depends=['l10n_it_edi_attachment_file']
    )
    l10n_it_stamp_duty = fields.Float(default=0, string="Dati Bollo", readonly=True, states={'draft': [('readonly', False)]})
    l10n_it_ddt_id = fields.Many2one('l10n_it.ddt', string='DDT', readonly=True, states={'draft': [('readonly', False)]}, copy=False)

    @api.depends('move_type', 'is_move_sent', 'state', 'line_ids.tax_tag_ids')
    def _compute_display_send_and_print_button(self):
        super()._compute_display_send_and_print_button()
        for move in self:
            move.display_send_and_print_button |= (
                move.state == 'posted'
                and not move.is_move_sent
                and move._l10n_it_edi_is_self_invoice()
            )

    def action_check_l10n_it_edi(self):
        self.ensure_one()
        if not self.l10n_it_edi_transaction and self.l10n_it_edi_state not in WAITING_STATES:
            raise UserError(_("This move is not waiting for updates from the SdI."))
        self.company_id.account_edi_proxy_client_ids.filtered(
            lambda x: x.proxy_type == "l10n_it_edi")._l10n_it_edi_update(self, interactive=True)

    @api.depends('l10n_it_edi_transaction')
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        for move in self.filtered(lambda m: m.l10n_it_edi_transaction):
            move.show_reset_to_draft_button = False

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        if file_data['type'] == 'l10n_it_edi':
            return self.env['l10n_it_edi.import']._l10n_it_edi_import
        return super()._get_edi_decoder(file_data, new=new)

    def _l10n_it_edi_get_line_values(self, reverse_charge_refund=False, is_downpayment=False, convert_to_euros=True):
        """ Returns a list of dictionaries passed to the template for the invoice lines (DettaglioLinee)
        """
        invoice_lines = []
        lines = self.invoice_line_ids.filtered(lambda l: not l.display_type in ('line_note', 'line_section'))
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
                    downpayment_moves_description = ', '.join([m.name for m in downpayment_moves])
                    sep = ', ' if description else ''
                    description = f"{description}{sep}{downpayment_moves_description}"

            invoice_lines.append({
                'line': line,
                'line_number': num + 1,
                'description': description or 'NO NAME',
                'unit_price': price_unit,
                'subtotal_price': price_subtotal,
                'vat_tax': line.tax_ids._l10n_it_filter_kind('vat'),
                'downpayment_moves': downpayment_moves,
                'discount_type': (
                    'SC' if line.discount > 0
                    else 'MG' if line.discount < 0
                    else False)
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
            tax_rate = tax_dict['tax'].amount
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
            }
            tax_lines.append(tax_line_dict)
        return tax_lines

    def _l10n_it_edi_filter_tax_details(self, line, tax_values):
        """Filters tax details to only include the positive amounted lines regarding VAT taxes."""
        repartition_line = tax_values['tax_repartition_line']
        return (repartition_line.factor_percent >= 0 and repartition_line.tax_id.amount >= 0)

    def _l10n_it_edi_get_values(self):
        self.ensure_one()

        # Flags
        is_self_invoice = self._l10n_it_edi_is_self_invoice()
        document_type = self._l10n_it_edi_get_document_type()

        # Represent if the document is a reverse charge refund in a single variable
        reverse_charge = document_type in ['TD17', 'TD18', 'TD19']
        is_downpayment = document_type in ['TD02']
        reverse_charge_refund = self.move_type == 'in_refund' and reverse_charge
        convert_to_euros = self.currency_id.name != 'EUR'

        tax_details = self._prepare_edi_tax_details(filter_to_apply=self._l10n_it_edi_filter_tax_details)

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
        elif partner._is_pa():
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

        # Reference line for finding the conversion rate used in the document
        conversion_line = self.invoice_line_ids.sorted(lambda l: abs(l.balance), reverse=True)[0] if self.invoice_line_ids else None
        conversion_rate = float_repr(
            abs(conversion_line.balance / conversion_line.amount_currency), precision_digits=5,
        ) if convert_to_euros and conversion_line else None

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

        if set(scopes) == set(['consu', 'service']):
            return "both"
        return scopes and scopes.pop()

    def _l10n_it_edi_is_self_invoice(self):
        """
            Italian EDI requires Vendor bills coming from EU countries to be sent as self-invoices.
            We recognize these cases based on the taxes that target the VJ tax grids, which imply
            the use of VAT External Reverse Charge.
        """
        self.ensure_one()
        if not self.is_purchase_document():
            return False

        invoice_lines_tags = self.line_ids.tax_tag_ids
        it_tax_report_vj_lines = self.env['account.report.line'].search([
            ('report_id.country_id.code', '=', 'IT'),
            ('code', 'like', 'VJ%'),
        ])
        vj_lines_tags = it_tax_report_vj_lines.expression_ids._get_matching_tags()
        ids_intersection = set(invoice_lines_tags.ids) & set(vj_lines_tags.ids)
        return bool(ids_intersection)

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

    def _l10n_it_edi_export_data_check(self):
        errors = self._l10n_it_edi_base_export_data_check()
        if not self._l10n_it_edi_is_simplified():
            errors += self._l10n_it_edi_export_buyer_data_check()
        return errors

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
        template_reference = self.env.ref('l10n_it_edi.account_invoice_it_simplified_FatturaPA_export', raise_if_not_found=False)
        buyer = self.commercial_partner_id
        return all([
            template_reference,
            not self._l10n_it_edi_is_self_invoice(),
            self._l10n_it_edi_export_buyer_data_check(),
            not buyer.country_id or buyer.country_id.code == 'IT',
            buyer.l10n_it_codice_fiscale or (buyer.vat and (buyer.vat[:2].upper() == 'IT' or buyer.vat[:2].isdecimal())),
            self.amount_total <= 400,
        ])

    def _l10n_it_edi_base_export_data_check(self):
        errors = []
        seller = self.company_id
        buyer = self.commercial_partner_id
        is_self_invoice = self._l10n_it_edi_is_self_invoice()
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
            if not tax_line.tax_line_id.l10n_it_kind_exoneration and tax_line.tax_line_id.amount == 0:
                errors.append(_("%s has an amount of 0.0, you must indicate the kind of exoneration.", tax_line.name))

        errors += self._l10n_it_edi_export_taxes_data_check()

        return errors

    def _l10n_it_edi_export_taxes_data_check(self):
        """
            Can be overridden by submodules like l10n_it_edi_withholding, which also allows for withholding and pension_fund taxes.
        """
        errors = []
        for invoice_line in self.invoice_line_ids.filtered(lambda x: not x.display_type):
            if len(invoice_line.tax_ids) != 1:
                errors.append(_("In line %s, you must select one and only one tax.", invoice_line.name))
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
            if not tax_line.tax_line_id.l10n_it_kind_exoneration and tax_line.tax_line_id.amount == 0:
                errors.append(_("%s has an amount of 0.0, you must indicate the kind of exoneration.", tax_line.name))

        return errors

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
            'self_invoice': self._l10n_it_edi_is_self_invoice(),
            'downpayment': self._is_downpayment(),
            'services_or_goods': services_or_goods,
            'goods_in_italy': services_or_goods == 'consu' and self._l10n_it_edi_goods_in_italy(),
        }

    def _l10n_it_edi_document_type_mapping(self):
        """ Returns a dictionary with the required features for every TDxx FatturaPA document type """
        return {
            'TD01': dict(move_types=['out_invoice'], import_type='in_invoice', self_invoice=False, simplified=False, downpayment=False),
            'TD02': dict(move_types=['out_invoice'], import_type='in_invoice', self_invoice=False, simplified=False, downpayment=True),
            'TD04': dict(move_types=['out_refund'], import_type='in_refund', self_invoice=False, simplified=False),
            'TD07': dict(move_types=['out_invoice'], import_type='in_invoice', self_invoice=False, simplified=True),
            'TD08': dict(move_types=['out_refund'], import_type='in_refund', self_invoice=False, simplified=True),
            'TD09': dict(move_types=['out_invoice'], import_type='in_invoice', self_invoice=False, simplified=True),
            'TD28': dict(move_types=['in_invoice', 'in_refund'], import_type='in_invoice', simplified=False, self_invoice=True, partner_country_code="SM"),
            'TD17': dict(move_types=['in_invoice', 'in_refund'], import_type='in_invoice', simplified=False, self_invoice=True, services_or_goods="service"),
            'TD18': dict(move_types=['in_invoice', 'in_refund'], import_type='in_invoice', simplified=False, self_invoice=True, services_or_goods="consu", goods_in_italy=False, partner_in_eu=True),
            'TD19': dict(move_types=['in_invoice', 'in_refund'], import_type='in_invoice', simplified=False, self_invoice=True, services_or_goods="consu", goods_in_italy=True),
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
                if isinstance(document_type_feature, (tuple, list)):
                    comparisons.append(invoice_feature in document_type_feature)
                else:
                    comparisons.append(invoice_feature == document_type_feature)
            if all(comparisons):
                return code
        return False

    def _l10n_it_edi_is_simplified_document_type(self, document_type):
        mapping = self._l10n_it_edi_document_type_mapping()
        return mapping.get(document_type, {}).get('simplified', False)

    def _l10n_it_edi_demo_mode_update(self):
        for move in self:
            filename = move.l10n_it_edi_attachment_id and move.l10n_it_edi_attachment_id.name or '???'
            self._l10n_it_edi_write_update(
                transformed_update_data={
                    'l10n_it_edi_state': 'forwarded',
                    'l10n_it_edi_transaction': f'demo_{uuid.uuid4()}',
                    'send_ack_to_edi_proxy': False,
                    'date': fields.Date.today(),
                    'filename': filename},
                message=_("The e-invoice file %s has been sent in Demo EDI mode.", filename))

    def _l10n_it_edi_update(self, updates_data):
        id_transactions_to_ack = []
        for move in self:
            update_data = updates_data[move.l10n_it_edi_transaction]
            parsed_update_data = move._l10n_it_edi_parse_update_data(update_data)
            transformed_update_data = move._l10n_it_edi_transform_update_data(parsed_update_data)
            message = move._l10n_it_edi_get_message(transformed_update_data)
            move._l10n_it_edi_write_update(transformed_update_data, message)
            if (transformed_update_data.get('send_ack_to_edi_proxy')
                and (id_transaction_to_ack := transformed_update_data.get('l10n_it_edi_transaction'))):
                id_transactions_to_ack.append(id_transaction_to_ack)
        return id_transactions_to_ack

    def _l10n_it_edi_parse_update_data(self, update_data):
        sdi_state = update_data.get('state', '')
        if not (xml_content := update_data.get('xml_content')):
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

    def _l10n_it_edi_transform_update_data(self, parsed_update_data):
        """ Reads the notification XML coming from the EDI Proxy Server
            Recovers information about the new state.
            Computes whether the EDI Proxy Server is to be acked,
            and whether the id_transaction has to be reset.
        """
        self.ensure_one()
        update_state_map = {
            'not_found': False,
            'awaiting_outcome': 'processing',
            'notificaScarto': 'rejected',
            'ricevutaConsegna': 'forwarded',
            'forward_attempt_failed': 'forward_attempt_failed',
            'notificaMancataConsegna': 'forward_failed',
            ('notificaEsito', 'EC01'): 'accepted_by_pa_partner',
            ('notificaEsito', 'EC02'): 'rejected_by_pa_partner',
            'notificaDecorrenzaTermini': 'accepted_by_pa_partner_after_expiry',
        }
        sdi_state = parsed_update_data['sdi_state']
        filename = parsed_update_data.get('filename')
        errors = parsed_update_data.get('errors', [])
        date = parsed_update_data.get('date', fields.Date.today())
        if not filename and self.l10n_it_edi_attachment_id:
            filename = self.l10n_it_edi_attachment_id.name
        outcome = parsed_update_data.get('outcome', False)
        if not outcome:
            new_state = update_state_map.get(sdi_state, False)
        else:
            new_state = update_state_map.get((sdi_state, outcome), False)

        parsed_update_data.update({
            'l10n_it_edi_state': new_state,
            'l10n_it_edi_transaction': False if new_state in (False, 'rejected') else self.l10n_it_edi_transaction,
            'send_ack_to_edi_proxy': bool(new_state),
            'date': date,
            'errors': errors,
            'filename': filename,
        })
        return parsed_update_data

    def _l10n_it_edi_write_update(self, transformed_update_data, message):
        """ Update the record with the data coming from the IAP server.
            Eventually post the message.
            Commit the transaction.
        """
        self.ensure_one()
        old_state = self.l10n_it_edi_state
        new_state = transformed_update_data['l10n_it_edi_state']
        self.write({
            'l10n_it_edi_state': new_state,
            'l10n_it_edi_transaction': transformed_update_data['l10n_it_edi_transaction'],
            'l10n_it_edi_header': message or False,
        })

        if message and old_state != new_state:
            self.with_context(no_new_invoice=True).sudo().message_post(body=message)

        if new_state == 'rejected':
            self.l10n_it_edi_attachment_file = False

        self.env.cr.commit()

    def _l10n_it_edi_get_message(self, transformed_update_data):
        """ The status change will be notified in the chatter of the move.
            Compute the message from the notification information coming from the EDI Proxy Server
        """
        self.ensure_one()
        partner = self.commercial_partner_id
        partner_name = partner.display_name
        filename = transformed_update_data['filename']
        new_state = transformed_update_data['l10n_it_edi_state']
        if new_state == 'rejected':
            DUPLICATE_MOVE = '00404'
            DUPLICATE_FILENAME = '00002'
            error_descriptions = []
            for error_code, error_description in transformed_update_data['errors']:
                if error_code == DUPLICATE_MOVE:
                    error_description = _(
                        "The e-invoice file %s is duplicated.\n"
                        "Original message from the SdI: %s",
                        filename, error_description)
                elif error_code == DUPLICATE_FILENAME:
                    error_description = _(
                        "The e-invoice filename %s is duplicated. Please check the FatturaPA Filename sequence.\n"
                        "Original message from the SdI: %s",
                        filename, error_description)
                error_descriptions.append(error_description)

            return format_errors(_('The e-invoice has been refused by the SdI.'), error_descriptions)

        elif partner._is_pa():
            pa_specific_map = {
                'forwarded': nl2br(escape(_(
                    "The e-invoice file %s was succesfully sent to the SdI.\n"
                    "%s has 15 days to accept or reject it.",
                    filename, partner_name))),
                'forward_attempt_failed': nl2br(escape(_(
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
            'forward_attempt_failed': nl2br(escape(_(
                "The e-invoice file %s has been accepted by the SdI.\n"
                "The SdI is not able to forward it to %s at the moment.\n"
                "It will try again for up to 2 days, after which you'll eventually "
                "need to send it the invoice to the partner by post or e-mail.",
                filename, partner_name))),
            'forward_failed': nl2br(escape(_(
                "The e-invoice file %s couldn't be forwarded to %s.\n"
                "Please remember to send it via post or e-mail.",
                filename, partner_name)))
        }
        return new_state_messages_map.get(new_state)
