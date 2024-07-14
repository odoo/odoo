# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import base64
from lxml import etree
from num2words import num2words

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_repr, float_round
from odoo.exceptions import UserError

CATALOG52 = [
    ("1002", "TRANSFERENCIA GRATUITA DE UN BIEN Y/O SERVICIO PRESTADO GRATUITAMENTE"),
    ("2000", "COMPROBANTE DE PERCEPCIÓN"),
    ("2001", "BIENES TRANSFERIDOS EN LA AMAZONÍA REGIÓN SELVAPARA SER CONSUMIDOS EN LA MISMA"),
    ("2002", "SERVICIOS PRESTADOS EN LA AMAZONÍA REGIÓN SELVA PARA SER CONSUMIDOS EN LA MISMA"),
    ("2003", "CONTRATOS DE CONSTRUCCIÓN EJECUTADOS EN LA AMAZONÍA REGIÓN SELVA"),
    ("2004", "Agencia de Viaje - Paquete turístico"),
    ("2005", "Venta realizada por emisor itinerante"),
    ("2006", "Operación sujeta a detracción"),
    ("2007", "Operación sujeta al IVAP"),
    ("2008", "VENTA EXONERADA DEL IGV-ISC-IPM. PROHIBIDA LA VENTA FUERA DE LA ZONA COMERCIAL DE TACNA"),
    ("2009", "PRIMERA VENTA DE MERCANCÍA IDENTIFICABLE ENTRE USUARIOS DE LA ZONA COMERCIAL"),
    ("2010", "Restitucion Simplificado de Derechos Arancelarios"),
    ("2011", "EXPORTACION DE SERVICIOS - DECRETO LEGISLATIVO Nº 919"),
]


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pe_edi_is_required = fields.Boolean(
        string="Is the Peruvian EDI needed",
        compute='_compute_l10n_pe_edi_is_required')
    l10n_pe_edi_cancel_cdr_number = fields.Char(
        copy=False,
        help="Reference from webservice to consult afterwards.")
    l10n_pe_edi_refund_reason = fields.Selection(
        selection=[
            ('01', 'Cancellation of the operation'),
            ('02', 'Cancellation by error in the RUC'),
            ('03', 'Correction by error in the description'),
            ('04', 'Global discount'),
            ('05', 'Discount per item'),
            ('06', 'Total refund'),
            ('07', 'Refund per item'),
            ('08', 'Bonus'),
            ('09', 'Decrease in value'),
            ('10', 'Other concepts'),
            ('11', 'Adjust in the exportation operation'),
            ('12', 'Adjust of IVAP'),
        ],
        string="Credit Reason",
        help='It contains all possible values for the refund reason according to Catalog No. 09')
    l10n_pe_edi_charge_reason = fields.Selection(
        selection=[
            ('01', 'Default interest'),
            ('02', 'Increase in value'),
            ('03', 'Penalties / other concepts'),
            ('11', 'Adjustments of export operations'),
            ('12', 'Adjustments affecting the IVAP'),
        ],
        string="Debit Reason",
        help='It contains all possible values for the charge reason according to Catalog No. 10')
    l10n_pe_edi_cancel_reason = fields.Char(
        string="Cancel Reason",
        copy=False,
        help="Peru: Reason given by the user for cancelling this move, structure of voided summary: sac:VoidReasonDescription.")
    l10n_pe_edi_operation_type = fields.Selection(
        selection=[
            ('0101', '[0101] Internal sale'),
            ('0112', '[0112] Internal Sale - Sustains Natural Person Deductible Expenses'),
            ('0113', '[0113] Internal Sale-NRUS'),
            ('0200', '[0200] Export of Goods'),
            ('0201', '[0201] Exportation of Services - Provision of services performed entirely in the country'),
            ('0202', '[0202] Exportation of Services - Provision of non-domiciled lodging services'),
            ('0203', '[0203] Exports of Services - Transport of shipping companies'),
            ('0204', '[0204] Exportation of Services - Services to foreign-flagged ships and aircraft'),
            ('0205', '[0205] Exportation of Services - Services that make up a Tourist Package'),
            ('0206', '[0206] Exports of Services - Complementary services to freight transport'),
            ('0207', '[0207] Exportation of Services - Supply of electric power in favor of subjects domiciled in ZED'),
            ('0208', '[0208] Exportation of Services - Provision of services partially carried out abroad'),
            ('0301', '[0301] Operations with air waybill (issued in the national scope)'),
            ('0302', '[0302] Passenger rail transport operations'), ('0303', '[0303] Oil royalty Pay Operations'),
            ('0401', '[0401] Non-domiciled sales that do not qualify as an export'),
            ('1001', '[1001] Operation Subject to Detraction'),
            ('1002', '[1002] Operation Subject to Detraction - Hydrobiological Resources'),
            ('1003', '[1003] Operation Subject to Drawdown - Passenger Transport Services'),
            ('1004', '[1004] Operation Subject to Drawdown - Cargo Transportation Services'),
            ('2001', '[2001] Operation Subject to Perception')
        ],
        string="Operation Type (PE)",
        store=True, readonly=False,
        compute='_compute_l10n_pe_edi_operation_type',
        help="Peru: Defines the operation type, all the options can be used for all the document types, except "
             "'[0113] Internal Sale-NRUS' that is for document type 'Boleta' and '[0112] Internal Sale - Sustains "
             "Natural Person Deductible Expenses' exclusive for document type 'Factura'"
             "It can't be changed after validation. This is an optional feature added to avoid a warning. Catalog No. 51.")
    l10n_pe_edi_legend = fields.Selection(
        selection=CATALOG52,
        string="Legend Code", help="Peru: Specific operation type code.")
    l10n_pe_edi_legend_value = fields.Char(
        string="Legend",
        store=True, readonly=False, compute='_compute_l10n_pe_edi_legend_value',
        help="Peru: Specific operation type value.")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_type', 'company_id')
    def _compute_l10n_pe_edi_is_required(self):
        for move in self:
            move.l10n_pe_edi_is_required = move.country_code == 'PE' \
                and move.is_sale_document() and move.journal_id.l10n_latam_use_documents

    @api.depends('move_type', 'company_id')
    def _compute_l10n_pe_edi_operation_type(self):
        for move in self:
            move.l10n_pe_edi_operation_type = '0101' if move.country_code == 'PE' and move.is_sale_document() else False

    @api.depends('l10n_pe_edi_legend')
    def _compute_l10n_pe_edi_legend_value(self):
        for move in self:
            if move.l10n_pe_edi_legend:
                matched_elements = [element for element in CATALOG52 if element[0] == move.l10n_pe_edi_legend]
                move.l10n_pe_edi_legend_value = matched_elements[0][1]
            else:
                move.l10n_pe_edi_legend_value = False

    @api.depends('journal_id', 'partner_id', 'company_id', 'move_type', 'debit_origin_id', 'l10n_pe_edi_operation_type')
    def _compute_l10n_latam_available_document_types(self):
        # EXTENDS 'l10n_latam_invoice_document'
        pe02_moves = self.filtered(
            lambda move: (
                move.state == 'draft'
                and move.country_code == 'PE'
                and move.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code != '6'
                and move.l10n_pe_edi_operation_type in ('0200', '0201', '0202', '0203', '0204', '0205', '0206', '0207', '0208')
                and move.journal_id.type == 'sale'
            )
        )
        for rec in pe02_moves.filtered(lambda move: move.move_type == 'out_invoice'):
            rec.l10n_latam_available_document_type_ids = self.env.ref('l10n_pe.document_type01') | self.env.ref('l10n_pe.document_type08')
        for rec in pe02_moves.filtered(lambda move: move.move_type == 'out_refund'):
            rec.l10n_latam_available_document_type_ids = self.env.ref('l10n_pe.document_type02')
        return super(AccountMove, self - pe02_moves)._compute_l10n_latam_available_document_types()

    # -------------------------------------------------------------------------
    # SEQUENCE HACK
    # -------------------------------------------------------------------------

    def _get_last_sequence_domain(self, relaxed=False):
        # OVERRIDE
        where_string, param = super()._get_last_sequence_domain(relaxed)
        if self.l10n_pe_edi_is_required:
            where_string += " AND l10n_latam_document_type_id = %(l10n_latam_document_type_id)s"
            param['l10n_latam_document_type_id'] = self.l10n_latam_document_type_id.id or 0
        return where_string, param

    def _get_starting_sequence(self):
        # OVERRIDE
        if self.l10n_pe_edi_is_required and self.l10n_latam_document_type_id:
            doc_mapping = {'01': 'FFI', '03': 'BOL', '07': 'CNE', '08': 'NDI'}
            middle_code = doc_mapping.get(self.l10n_latam_document_type_id.code, self.journal_id.code)
            # TODO: maybe there is a better method for finding decent 2nd journal default invoice names
            if self.journal_id.code != 'INV':
                middle_code = middle_code[:1] + self.journal_id.code[:2]
            return "%s %s-00000000" % (self.l10n_latam_document_type_id.doc_code_prefix, middle_code)

        return super()._get_starting_sequence()

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    def _l10n_pe_edi_get_serie_folio(self):
        number_match = [rn for rn in re.finditer(r'\d+', self.name.replace(' ', ''))]
        serie = self.name[:number_match[-1].start()].replace('-', '').replace(' ', '') or None
        folio = number_match[-1].group() or None
        return {'serie': serie, 'folio': folio}

    def _l10n_pe_edi_get_spot(self):
        max_percent = max(self.invoice_line_ids.mapped('product_id.l10n_pe_withhold_percentage'), default=0)
        if not max_percent or not self.l10n_pe_edi_operation_type in ['1001', '1002', '1003', '1004'] or self.move_type == 'out_refund':
            return {}
        line = self.invoice_line_ids.filtered(lambda r: r.product_id.l10n_pe_withhold_percentage == max_percent)[0]
        national_bank = self.env.ref('l10n_pe.peruvian_national_bank')
        national_bank_account = self.company_id.bank_ids.filtered(lambda b: b.bank_id == national_bank)
        # just take the first one (but not meant to have multiple)
        national_bank_account_number = national_bank_account[0].acc_number if national_bank_account else False

        return {
            'id': 'Detraccion',
            'payment_means_id': line.product_id.l10n_pe_withhold_code,
            'payee_financial_account': national_bank_account_number,
            'payment_means_code': '999',
            'spot_amount': float_round(self.amount_total * (max_percent / 100.0), precision_rounding=0.01),
            'amount': float_round(self.amount_total_signed * (max_percent / 100.0), precision_rounding=1),
            'payment_percent': max_percent,
            'spot_message': "Operación sujeta al sistema de Pago de Obligaciones Tributarias-SPOT, Banco de la Nacion %s%% Cod Serv. %s" % (
                line.product_id.l10n_pe_withhold_percentage, line.product_id.l10n_pe_withhold_code)
        }

    # -------------------------------------------------------------------------
    # REPORT
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_pe_edi_amount_to_text(self):
        """Transform a float amount to text words on peruvian format: AMOUNT IN TEXT 11/100
        :returns: Amount transformed to words peruvian format for invoices
        :rtype: str
        """
        self.ensure_one()
        amount_i, amount_d = divmod(self.amount_total, 1)
        amount_d = int(round(amount_d * 100, 2))
        words = num2words(amount_i, lang='es')
        result = '%(words)s Y %(amount_d)02d/100 %(currency_name)s' % {
            'words': words,
            'amount_d': amount_d,
            'currency_name':  self.currency_id.currency_unit_label,
        }
        return result.upper()

    def _l10n_pe_edi_get_extra_report_values(self):
        ''' Get values from the current invoice in order to render extra informations in the report.

        Qr-code documentation:
        https://cpe.sunat.gob.pe/sites/default/files/inline-files/Aspectos%20t%C3%A9cnicos%20-%20emisor%20electr%C3%B3nico_0.pdf#page=6

        Example of the text:
        '20557912879|6|FPPP|2346274|603.61|3957.01|2020-07-15|6|20462509236|5zVcyL443M1vVGhdFNi+H9jcslo=|\r\n'

        That specifies the next fields to be in the QR and Pipe separated:
        a) RUC number of the invoice issuer
        b) Document type
        c) Number conformed by serie and correlative
        d) IGV in case of having it
        e) Total amount
        f) Emission date
        g) Document type of the partner
        h) Document number of the partner

        :return: A python dictionary.
        '''
        self.ensure_one()

        # Parse the edi document.
        edi_attachment_zipped = self._get_edi_attachment(self.env.ref('l10n_pe_edi.edi_pe_ubl_2_1'))
        if not edi_attachment_zipped:
            return {}
        edi_attachment_str = self.env['account.edi.format']._l10n_pe_edi_unzip_edi_document(base64.decodebytes(edi_attachment_zipped.with_context(bin_size=False).datas))
        edi_tree = etree.fromstring(edi_attachment_str)

        # Qr-code
        signature_hash = edi_tree.xpath('//ds:DigestValue', namespaces={'ds': 'http://www.w3.org/2000/09/xmldsig#'})[0].text
        igv_tax_amount = ''
        nsmap = {k: v for k, v in edi_tree.nsmap.items() if k}
        for tax_element in edi_tree.xpath('//cac:TaxSubtotal', namespaces=nsmap):
            tax_name_elements = tax_element.xpath(".//cac:TaxScheme/cbc:Name", namespaces=nsmap)
            tax_amount_elements = tax_element.xpath(".//cbc:TaxAmount", namespaces=nsmap)
            if tax_name_elements and tax_amount_elements and tax_name_elements[0].text == 'IGV':
                igv_tax_amount = tax_amount_elements[0].text
                break

        serie_folio = self._l10n_pe_edi_get_serie_folio()
        qr_code_values = [
            self.company_id.vat,
            self.company_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
            serie_folio['serie'],
            serie_folio['folio'],
            igv_tax_amount,
            str(self.amount_total),
            fields.Date.to_string(self.date),
            self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
            self.commercial_partner_id.vat or '00000000',
            signature_hash,
        ]

        return {
            'qr_str': '|'.join(qr_code_values) + '|\r\n',
            'amount_to_text': self._l10n_pe_edi_amount_to_text(),
        }

    def _l10n_pe_edi_get_payment_means(self):
        payment_means_id = 'Credito'
        if not self.invoice_date_due or self.invoice_date_due == self.invoice_date:
            payment_means_id = 'Contado'
        return payment_means_id

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def button_cancel_posted_moves(self):
        # OVERRIDE
        pe_edi_format = self.env.ref('l10n_pe_edi.edi_pe_ubl_2_1', raise_if_not_found=False)
        pe_invoices = pe_edi_format and self.filtered(pe_edi_format._get_move_applicability)
        if pe_invoices:
            credit_notes_needed = pe_invoices.filtered(lambda move: move.l10n_latam_document_type_id.code == '03')
            if credit_notes_needed:
                raise UserError(_("Invoices with this document type always need to be cancelled through a credit note. "
                                  "There is no possibility to cancel."))
            cancel_reason_needed = pe_invoices.filtered(lambda move: not move.l10n_pe_edi_cancel_reason)
            if cancel_reason_needed:
                return self.env.ref('l10n_pe_edi.action_l10n_pe_edi_cancel').sudo().read()[0]
        return super().button_cancel_posted_moves()

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.l10n_latam_use_documents and self.company_id.country_id.code == 'PE':
            return 'l10n_pe_edi.report_invoice_document'
        return super()._get_name_invoice_report()
