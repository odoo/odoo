import math
from num2words import num2words

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountEdiXmlUblTr(models.AbstractModel):
    _name = "account.edi.xml.ubl.tr"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL-TR 1.2"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        # EXTENDS account_edi_ubl_cii
        return '%s_einvoice.xml' % invoice.name.replace("/", "_")

    def _export_invoice_vals(self, invoice):
        def _get_formatted_id(invoice):
            # For now, we assume that the sequence is going to be in the format {prefix}/{year}/{invoice_number}.
            # To send an invoice to Nlvera, the format needs to follow ABC2009123456789.
            parts = invoice.name.split('/')
            prefix, year, number = parts[0], parts[1], parts[2].zfill(9)
            return f"{prefix.upper()}{year}{number}"

        # EXTENDS account.edi.xml.ubl_21
        vals = super()._export_invoice_vals(invoice)

        # Check the customer status if it hasn't been done before as it's needed for profile_id
        if invoice.partner_id.l10n_tr_nilvera_customer_status == 'not_checked':
            invoice.partner_id.check_nilvera_customer()

        # Update the Invoice Template
        vals['InvoiceType_template'] = 'l10n_tr_nilvera_einvoice.ubl_tr_InvoiceType'

        vals['vals'].update({
            'id': _get_formatted_id(invoice),
            'customization_id': 'TR1.2',
            'profile_id': 'TEMELFATURA' if invoice.partner_id.l10n_tr_nilvera_customer_status == 'einvoice' else 'EARSIVFATURA',
            'copy_indicator': 'false',
            'uuid': invoice.l10n_tr_nilvera_uuid,
            'document_type_code': 'SATIS' if invoice.move_type == 'out_invoice' else 'IADE',
            'due_date': False,
            'line_count_numeric': len(invoice.line_ids),
            'order_issue_date': invoice.invoice_date,
            'pricing_currency_code': invoice.currency_id.name.upper() if invoice.currency_id != invoice.company_id.currency_id else False,
            'currency_dp': 2,
        })
        # Nilvera will reject any <BuyerReference> tag, so remove it
        if vals['vals'].get('buyer_reference'):
            del vals['vals']['buyer_reference']

        vals['vals']['note_vals'].append({'note': self._l10n_tr_get_amount_integer_partn_text_note(invoice.amount_residual_signed, self.env.ref('base.TRY')), 'note_attrs': {}})
        if vals['invoice'].currency_id.name != 'TRY':
            vals['vals']['note_vals'].append({'note': self._l10n_tr_get_amount_integer_partn_text_note(invoice.amount_residual, vals['invoice'].currency_id), 'note_attrs': {}})
            vals['vals']['note_vals'].append({'note': self._get_invoice_currency_exchange_rate(invoice.currency_id, invoice.company_id, invoice.invoice_date)})
        return vals

    @api.model
    def _l10n_tr_get_amount_integer_partn_text_note(self, amount, currency):
        sign = math.copysign(1.0, amount)
        amount_integer_part, amount_decimal_part = divmod(abs(amount), 1)
        amount_decimal_part = int(amount_decimal_part * 100)

        text_i = num2words(amount_integer_part * sign, lang="tr") or 'Sifir'
        text_d = num2words(amount_decimal_part * sign, lang="tr") or 'Sifir'
        return f'YALNIZ : {text_i} {currency.name} {text_d} {currency.currency_subunit_label}'.upper()

    def _get_invoice_currency_exchange_rate(self, currency, company, date):
        converted_rate = currency._convert(1, company.currency_id, company=company, date=date, round=False)
        # Nilvera Portal accepts the exchange rate for 6 decimals places only.
        return f'KUR : {converted_rate:.6f} TL'

    def _get_country_vals(self, country):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_country_vals(country)
        vals['name'] = country.with_context(lang='tr_TR').name
        return vals

    def _get_partner_party_identification_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_partner_party_identification_vals_list(partner)
        # Nilvera will reject any <ID> without a <schemeID>, so remove all items not
        # having the following structure : {'id': '...', 'id_attrs': {'schemeID': '...'}}
        vals = [v for v in vals if v.get('id') and v.get('id_attrs', {}).get('schemeID')]
        vals.append({
            'id_attrs': {
                'schemeID': 'VKN' if partner.is_company else 'TCKN',
            },
            'id': partner.vat,
        })
        return vals

    def _get_partner_address_vals(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_partner_address_vals(partner)
        vals.update({
            'city_subdivision_name ': partner.city,
            'city_name': partner.state_id.name,
            'country_subentity': False,
            'country_subentity_code': False,
        })
        return vals

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # EXTENDS account.edi.xml.ubl_21
        if partner.l10n_tr_nilvera_customer_status == "einvoice" and not partner.ref:
            raise UserError(_("E-Invoice customers must have a tax office name in the partner reference field."))

        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)
        for vals in vals_list:
            vals.pop('registration_address_vals', None)
            vals["tax_scheme_vals"].update(
                {
                    "id": "",
                    "name": partner.ref,
                }
            )
        return vals_list

    def _get_partner_party_legal_entity_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        vals_list = super()._get_partner_party_legal_entity_vals_list(partner)
        for vals in vals_list:
            vals.pop('registration_address_vals', None)
        return vals_list

    def _get_partner_person_vals(self, partner):
        if not partner.is_company:
            name_parts = partner.name.split(' ', 1)
            return {
                'first_name': name_parts[0],
                # If no family name is present, use a zero-width space (U+200B) to ensure the XML tag is rendered. This is required by Nilvera.
                'family_name': name_parts[1] if len(name_parts) > 1 else '\u200B',
            }
        return super()._get_partner_person_vals(partner)

    def _get_delivery_vals_list(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        delivery_vals = super()._get_delivery_vals_list(invoice)
        if 'picking_ids' in invoice._fields and invoice.picking_ids:
            delivery_vals[0]['delivery_id'] = invoice.picking_ids[0].name
            return delivery_vals
        return []

    def _get_invoice_payment_means_vals_list(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        vals_list = super()._get_invoice_payment_means_vals_list(invoice)
        for vals in vals_list:
            vals.pop('instruction_id', None)
            vals.pop('payment_id_vals', None)
        return vals_list

    def _get_tax_category_list(self, invoice, taxes):
        # OVERRIDES account.edi.common
        res = []
        for tax in taxes:
            is_withholding = invoice.currency_id.compare_amounts(tax.amount, 0) == -1
            tax_type_code = '9015' if is_withholding else '0015'
            tax_scheme_name = 'KDV Tevkifatı' if is_withholding else 'Gerçek Usulde KDV'
            res.append({
                'id': tax_type_code,
                'percent': tax.amount if tax.amount_type == 'percent' else False,
                'tax_scheme_vals': {'name': tax_scheme_name, 'tax_type_code': tax_type_code},
            })
        return res

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # EXTENDS account.edi.xml.ubl_21
        tax_totals_vals = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)

        for vals in tax_totals_vals:
            vals['currency_dp'] = 2
            for subtotal_vals in vals.get('tax_subtotal_vals', []):
                subtotal_vals['currency_dp'] = 2
                subtotal_vals.get('tax_category_vals', {})['id'] = False
                subtotal_vals.get('tax_category_vals', {})['percent'] = False

        return tax_totals_vals

    def _get_invoice_monetary_total_vals(self, invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount):
        # EXTENDS account.edi.xml.ubl_20
        vals = super()._get_invoice_monetary_total_vals(invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount)
        # allowance_total_amount needs to have a value even if 0.0 otherwise it's blank in the Nilvera PDF.
        vals['allowance_total_amount'] = allowance_total_amount

        # <cac:PrepaidAmount> node is not supported by Nilvera, so it is removed and added to the payable_amount so that
        # the total invoice amount (in invoice currency) is preserved.
        prepaid_amount = vals.pop('prepaid_amount', None)
        if prepaid_amount:
            vals['payable_amount'] += prepaid_amount
        vals['currency_dp'] = 2
        return vals

    def _get_document_allowance_charge_vals_list(self, invoice):
        vals = super()._get_document_allowance_charge_vals_list(invoice)
        for val in vals:
            # The allowance_charge_reason_code is not supported in UBL TR so we need to remove that.
            val.pop('allowance_charge_reason_code', None)

        invoice_lines = invoice.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_note', 'line_section'))
        total_discount_amount = 0
        for line in invoice_lines:
            total_discount_amount += line.currency_id.round(line.price_unit * line.quantity * (line.discount / 100))
        if total_discount_amount:
            vals.append({
                # Must be false since this is a discount.
                'charge_indicator': 'false',
                'amount': total_discount_amount,
                'currency_dp': 2,
                'currency_name': invoice.currency_id.name,
                'allowance_charge_reason': "Discount",
            })
        return vals

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        # EXTENDS account.edi.xml.ubl_21
        line_item_vals = super()._get_invoice_line_item_vals(line, taxes_vals)
        line_item_vals['classified_tax_category_vals'] = False
        return line_item_vals

    def _get_additional_document_reference_list(self, invoice):
        # EXTENDS account.edi.xml.ubl_20
        additional_document_reference_list = super()._get_additional_document_reference_list(invoice)
        if invoice.partner_id.l10n_tr_nilvera_customer_status == 'earchive':
            additional_document_reference_list.append({
                'id': "ELEKTRONIK",
                'issue_date': invoice.invoice_date,
                'document_type_code': "SEND_TYPE",
            })
        return additional_document_reference_list

    def _get_invoice_line_allowance_vals_list(self, line, tax_values_list=None):
        # EXTENDS account.edi.xml.ubl_20
        vals_list = super()._get_invoice_line_allowance_vals_list(line, tax_values_list)
        for vals in vals_list:
            vals.pop('allowance_charge_reason_code', None)
            vals['currency_dp'] = 2
        return vals_list

    def _get_invoice_line_price_vals(self, line):
        # EXTEND 'account.edi.common'
        invoice_line_price_vals = super()._get_invoice_line_price_vals(line)
        invoice_line_price_vals['base_quantity_attrs'] = {'unitCode': line.product_uom_id._get_unece_code()}
        invoice_line_price_vals['currency_dp'] = 2
        return invoice_line_price_vals

    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        invoice_line_vals = super()._get_invoice_line_vals(line, line_id, taxes_vals)
        invoice_line_vals['line_quantity_attrs'] = {'unitCode': line.product_uom_id._get_unece_code()}
        invoice_line_vals['currency_dp'] = 2
        return invoice_line_vals

    def _get_pricing_exchange_rate_vals_list(self, invoice):
        # EXTENDS 'account.edi.xml.ubl_20'
        if invoice.currency_id != invoice.company_id.currency_id:
            return [{
                'source_currency_code': invoice.currency_id.name.upper(),
                'target_currency_code': invoice.company_id.currency_id.name.upper(),
                'calculation_rate': round(invoice.currency_id._get_conversion_rate(invoice.currency_id, invoice.company_id.currency_id, invoice.company_id, invoice.invoice_date), 6),
                'date': invoice.invoice_date,
            }]
        return []

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_retrieve_partner_vals(self, tree, role):
        # EXTENDS account.edi.xml.ubl_20
        partner_vals = super()._import_retrieve_partner_vals(tree, role)
        partner_vals.update({
            'vat': self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cac:PartyIdentification//cbc:ID[string-length(text()) > 5]', tree),
        })
        return partner_vals

    def _import_fill_invoice_form(self, invoice, tree, qty_factor):
        # EXTENDS account.edi.xml.ubl_20
        logs = super()._import_fill_invoice_form(invoice, tree, qty_factor)

        # ==== Nilvera UUID ====
        if uuid_node := tree.findtext('./{*}UUID'):
            invoice.l10n_tr_nilvera_uuid = uuid_node

        return logs
