from odoo import models


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
            return f"{prefix}{year}{number}"

        # EXTENDS account.edi.xml.ubl_21
        vals = super()._export_invoice_vals(invoice)

        # Check the customer status if it hasn't been done before as it's needed for profile_id
        if invoice.partner_id.l10n_tr_nilvera_customer_status == 'not_checked':
            invoice.partner_id.check_nilvera_customer()

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
        })
        return vals

    def _get_partner_party_identification_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_partner_party_identification_vals_list(partner)
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
            'city_subdivision_name ': partner.state_id.name,
            'country_subentity': False,
            'country_subentity_code': False,
        })
        return vals

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # EXTENDS account.edi.xml.ubl_21
        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)
        for vals in vals_list:
            vals.pop('registration_address_vals', None)
        return vals_list

    def _get_partner_party_legal_entity_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        vals_list = super()._get_partner_party_legal_entity_vals_list(partner)
        for vals in vals_list:
            vals.pop('registration_address_vals', None)
        return vals_list

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
            for subtotal_vals in vals.get('tax_subtotal_vals', []):
                subtotal_vals.get('tax_category_vals', {})['id'] = False
                subtotal_vals.get('tax_category_vals', {})['percent'] = False

        return tax_totals_vals

    def _get_invoice_monetary_total_vals(self, invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount):
        # EXTENDS account.edi.xml.ubl_20
        vals = super()._get_invoice_monetary_total_vals(invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount)
        # allowance_total_amount needs to have a value even if 0.0 otherwise it's blank in the Nilvera PDF.
        vals['allowance_total_amount'] = allowance_total_amount
        if invoice.currency_id.is_zero(vals.get('prepaid_amount', 1)):
            del vals['prepaid_amount']
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
