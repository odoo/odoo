# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import Command, models, fields, _
from odoo.addons.l10n_it_edi.tools.xml_utils import get_text, get_float, get_date, format_errors


_logger = logging.getLogger(__name__)


class L10nItEdiImport(models.AbstractModel):
    _name = 'l10n_it_edi.import'
    _description = "Import invoices and bills from IT EDI XML"

    def _l10n_it_edi_search_partner(self, company, vat, codice_fiscale, email):
        for domain in [vat and [('vat', 'ilike', vat)],
                       codice_fiscale and [('l10n_it_codice_fiscale', 'in', ('IT' + codice_fiscale, codice_fiscale))],
                       email and ['|', ('email', '=', email), ('l10n_it_pec_email', '=', email)]]:
            if partner := domain and self.env['res.partner'].search(domain + [('company_id', 'in', (False, company.id))], limit=1):
                return partner
        return self.env['res.partner']

    def _l10n_it_edi_search_tax_for_import(self, company, percentage, extra_domain=None):
        """ Returns the VAT, Withholding or Pension Fund tax that suits the conditions given
            and matches the percentage found in the XML for the company. """
        conditions = [
            ('company_id', '=', company.id),
            ('amount', '=', percentage),
            ('amount_type', '=', 'percent'),
            ('type_tax_use', '=', 'purchase'),
        ] + (extra_domain or [])

        # As we're importing vendor bills, we're excluding Reverse Charge Taxes
        # which have a [100.0, 100.0, -100.0] repartition lines factor_percent distribution.
        # We only allow for taxes that have all positive repartition lines factor_percent distribution.
        taxes = self.env['account.tax'].search(conditions).filtered(
            lambda tax: all([rep_line.factor_percent >= 0 for rep_line in tax.invoice_repartition_line_ids]))

        return taxes[0] if taxes else taxes

    def _l10n_it_edi_get_extra_info(self, company, document_type, body_tree):
        """ This function is meant to collect other information that has to be inserted on the invoice lines by submodules.
            :return extra_info, messages_to_log"""
        return {'simplified': self.env['account.move']._l10n_it_edi_is_simplified_document_type(document_type)}, []

    def _l10n_it_edi_import(self, move, data, is_new):
        """ Decodes a l10n_it_edi move into an Odoo move.

        :param move:   the move which is either newly created or to be updated.
        :param data:   the dictionary with the content to be imported
                       keys: 'filename', 'content', 'xml_tree', 'type', 'sort_weight'
        :param is_new: whether the move is newly created or to be updated
        :returns:      the imported move
        """
        tree = data['xml_tree']
        company = move.company_id

        # For unsupported document types, just assume in_invoice, and log that the type is unsupported
        document_type = get_text(tree, '//DatiGeneraliDocumento/TipoDocumento')
        move_type = move._l10n_it_edi_document_type_mapping().get(document_type, {}).get('import_type')
        if not move_type:
            move_type = "in_invoice"
            _logger.info('Document type not managed: %s. Invoice type is set by default.', document_type)

        move.move_type = move_type

        # Collect extra info from the XML that may be used by submodules to further put information on the invoice lines
        extra_info, message_to_log = self._l10n_it_edi_get_extra_info(company, document_type, tree)

        # Partner
        vat = get_text(tree, '//CedentePrestatore//IdCodice')
        codice_fiscale = get_text(tree, '//CedentePrestatore//CodiceFiscale')
        email = get_text(tree, '//DatiTrasmissione//Email')
        if partner := self._l10n_it_edi_search_partner(company, vat, codice_fiscale, email):
            move.partner_id = partner
        else:
            message_to_log.append("%s<br/>%s" % (
                _("Vendor not found, useful informations from XML file:"),
                self._compose_info_message(tree, './/CedentePrestatore')))

        # Numbering attributed by the transmitter
        if progressive_id := get_text(tree, '//ProgressivoInvio'):
            move.payment_reference = progressive_id

        # Document Number
        if number := get_text(tree, './/DatiGeneraliDocumento//Numero'):
            move.ref = number

        # Currency
        if currency_str := get_text(tree, './/DatiGeneraliDocumento/Divisa'):
            currency = self.env.ref('base.%s' % currency_str.upper(), raise_if_not_found=False)
            if currency != self.env.company.currency_id and currency.active:
                move.currency_id = currency

        # Date
        if document_date := get_date(tree, './/DatiGeneraliDocumento/Data'):
            move.invoice_date = document_date
        else:
            message_to_log.append(_("Document date invalid in XML file: %s", document_date))

        # Stamp Duty
        if stamp_duty := get_text(tree, './/DatiGeneraliDocumento/DatiBollo/ImportoBollo'):
            move.l10n_it_stamp_duty = float(stamp_duty)

        # Comment
        for narration in get_text(tree, './/DatiGeneraliDocumento//Causale', many=True):
            move.narration = '%s%s<br/>' % (move.narration or '', narration)

        # Informations relative to the purchase order, the contract, the agreement,
        # the reception phase or invoices previously transmitted
        # <2.1.2> - <2.1.6>
        for document_type in ['DatiOrdineAcquisto', 'DatiContratto', 'DatiConvenzione', 'DatiRicezione', 'DatiFattureCollegate']:
            for element in tree.xpath('.//DatiGenerali/' + document_type):
                message_to_log.append("%s %s<br/>%s" % (document_type, _("from XML file:"),
                self._compose_info_message(element, '.')))

        #  Dati DDT. <2.1.8>
        if elements := tree.xpath('.//DatiGenerali/DatiDDT'):
            message_to_log.append("%s<br/>%s" % (
                _("Transport informations from XML file:"),
                self._compose_info_message(tree, './/DatiGenerali/DatiDDT')))

        # Due date. <2.4.2.5>
        if due_date := get_date(tree, './/DatiPagamento/DettaglioPagamento/DataScadenzaPagamento'):
            move.invoice_date_due = fields.Date.to_string(due_date)
        else:
            message_to_log.append(_("Payment due date invalid in XML file: %s", str(due_date)))

        # Information related to the purchase order <2.1.2>
        if (po_refs := get_text(tree, '//DatiGenerali/DatiOrdineAcquisto/IdDocumento', many=True)):
            move.invoice_origin = ", ".join(po_refs)

        # Total amount. <2.4.2.6>
        if amount_total := sum([float(x) for x in get_text(tree, './/ImportoPagamento', many=True) if x]):
            message_to_log.append(_("Total amount from the XML File: %s", amount_total))

        # Bank account. <2.4.2.13>
        if move.move_type not in ('out_invoice', 'in_refund'):
            if acc_number := get_text(tree, './/DatiPagamento/DettaglioPagamento/IBAN'):
                if move.partner_id and move.partner_id.commercial_partner_id:
                    bank = self.env['res.partner.bank'].search([
                        ('acc_number', '=', acc_number),
                        ('partner_id', '=', move.partner_id.commercial_partner_id.id),
                        ('company_id', 'in', [move.company_id.id, False])
                    ], order='company_id', limit=1)
                else:
                    bank = self.env['res.partner.bank'].search([
                        ('acc_number', '=', acc_number),
                        ('company_id', 'in', [move.company_id.id, False])
                    ], order='company_id', limit=1)
                if bank:
                    move.partner_bank_id = bank
                else:
                    message_to_log.append("%s<br/>%s" % (
                        _("Bank account not found, useful informations from XML file:"),
                        self._compose_info_message(
                            tree, ['.//DatiPagamento//Beneficiario',
                                './/DatiPagamento//IstitutoFinanziario',
                                './/DatiPagamento//IBAN',
                                './/DatiPagamento//ABI',
                                './/DatiPagamento//CAB',
                                './/DatiPagamento//BIC',
                                './/DatiPagamento//ModalitaPagamento'])))
        elif elements := tree.xpath('.//DatiPagamento/DettaglioPagamento'):
            message_to_log.append("%s<br/>%s" % (
                _("Bank account not found, useful informations from XML file:"),
                self._compose_info_message(tree, './/DatiPagamento')))

        # Invoice lines. <2.2.1>
        tag_name = './/DettaglioLinee' if not extra_info['simplified'] else './/DatiBeniServizi'
        for element in tree.xpath(tag_name):
            move_line_form = move.invoice_line_ids.create({
                'move_id': move.id,
                'tax_ids': [fields.Command.clear()]})
            if move_line_form:
                message_to_log += self._l10n_it_edi_import_line(element, move_line_form, extra_info)

        # Global discount summarized in 1 amount
        if discount_elements := tree.xpath('.//DatiGeneraliDocumento/ScontoMaggiorazione'):
            taxable_amount = float(move.tax_totals['amount_untaxed'])
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

            move.invoice_line_ids = [Command.create({
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
                'res_id': move.id,
            })

            # no_new_invoice to prevent from looping on the.message_post that would create a new invoice without it
            move.with_context(no_new_invoice=True).sudo().message_post(
                body=(_("Attachment from XML")),
                attachment_ids=[attachment_64.id],
            )

        for message in message_to_log:
            move.sudo().message_post(body=message)
        return move

    def _l10n_it_edi_import_line(self, element, move_line_form, extra_info=None):
        extra_info = extra_info or {}
        company = move_line_form.company_id
        partner = move_line_form.partner_id
        message_to_log = []

        # Sequence.
        line_elements = element.xpath('.//NumeroLinea')
        if line_elements:
            move_line_form.sequence = int(line_elements[0].text)

        # Product.
        if elements_code := element.xpath('.//CodiceArticolo'):
            for element_code in elements_code:
                type_code = element_code.xpath('.//CodiceTipo')[0]
                code = element_code.xpath('.//CodiceValore')[0]
                product = self.env['product.product'].search([('barcode', '=', code.text)])
                if (product and type_code.text == 'EAN'):
                    move_line_form.product_id = product
                    break
                if partner:
                    product_supplier = self.env['product.supplierinfo'].search([('partner_id', '=', partner.id), ('product_code', '=', code.text)], limit=2)
                    if product_supplier and len(product_supplier) == 1 and product_supplier.product_id:
                        move_line_form.product_id = product_supplier.product_id
                        break
            if not move_line_form.product_id:
                for element_code in elements_code:
                    code = element_code.xpath('.//CodiceValore')[0]
                    product = self.env['product.product'].search([('default_code', '=', code.text)], limit=2)
                    if product and len(product) == 1:
                        move_line_form.product_id = product
                        break

        # Name and Quantity.
        move_line_form.name = " ".join(get_text(element, './/Descrizione').split())
        move_line_form.quantity = float(get_text(element, './/Quantita') or '1')

        # Taxes
        percentage = None
        if not extra_info['simplified']:
            percentage = get_float(element, './/AliquotaIVA')
            if price_unit := get_float(element, './/PrezzoUnitario'):
                move_line_form.price_unit = price_unit
        elif amount := get_float(element, './/Importo'):
            percentage = get_float(element, './/Aliquota')
            if not percentage and (tax_amount := get_float(element, './/Imposta')):
                percentage = round(tax_amount / (amount - tax_amount) * 100)
            move_line_form.price_unit = amount / (1 + percentage / 100)

        move_line_form.tax_ids = []
        if percentage is not None:
            conditions = [('l10n_it_has_exoneration', '=', False)]
            if l10n_it_kind_exoneration := get_text(element, './/Natura'):
                conditions = [('l10n_it_kind_exoneration', '=', l10n_it_kind_exoneration)]
            if tax := self._l10n_it_edi_search_tax_for_import(company, percentage, conditions):
                move_line_form.tax_ids += tax
            else:
                message_to_log.append("%s<br/>%s" % (
                    _("Tax not found for line with description '%s'", move_line_form.name),
                    self._compose_info_message(element, '.'),
                ))

        # Discounts
        if elements := element.xpath('.//ScontoMaggiorazione'):
            element = elements[0]
            # Special case of only 1 percentage discount
            if len(elements) == 1:
                if discount_percentage := get_float(element, './/Percentuale'):
                    discount_type = get_text(element, './/Tipo')
                    discount_sign = -1 if discount_type == 'MG' else 1
                    move_line_form.discount = discount_sign * discount_percentage
            # Discounts in cascade summarized in 1 percentage
            else:
                total = get_float(element, './/PrezzoTotale')
                discount = 100 - (100 * total) / (move_line_form.quantity * move_line_form.price_unit)
                move_line_form.discount = discount

        return message_to_log

    def _compose_info_message(self, tree, tags):
        result = ""
        for tag in tags if isinstance(tags, (tuple, list)) else list(tags):
            for el in tree.xpath(tag):
                result += format_errors("", [f'{subel.tag}: {subel.text}' for subel in el.iter()])
        return result
