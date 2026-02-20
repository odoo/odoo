from markupsafe import Markup
from typing import Literal

from odoo import _, api, models

from stdnum.no import mva
from stdnum.be import vat as be_vat
CHORUS_PRO_PEPPOL_ID = "0009:11000201100044"


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _name = "account.edi.xml.ubl_bis3"
    _inherit = ['account.edi.xml.ubl_21', 'account.edi.ubl_pint_eu']
    _description = "UBL BIS Billing 3.0.12"

    """
    * Documentation of EHF Billing 3.0: https://anskaffelser.dev/postaward/g3/
    * EHF 2.0 is no longer used:
      https://anskaffelser.dev/postaward/g2/announcement/2019-11-14-removal-old-invoicing-specifications/
    * Official doc for EHF Billing 3.0 is the OpenPeppol BIS 3 doc +
      https://anskaffelser.dev/postaward/g3/spec/current/billing-3.0/norway/

        "Based on work done in PEPPOL BIS Billing 3.0, Difi has included Norwegian rules in PEPPOL BIS Billing 3.0 and
        does not see a need to implement a different CIUS targeting the Norwegian market. Implementation of EHF Billing
        3.0 is therefore done by implementing PEPPOL BIS Billing 3.0 without extensions or extra rules."

    Thus, EHF 3 and Bis 3 are actually the same format. The specific rules for NO defined in Bis 3 are added in Bis 3.

    To avoid multi-parental inheritance in case of UBL 4.0, we're adding the sale/purchase logic here.
    * Documentation for Peppol Order transaction 3.5: https://docs.peppol.eu/poacc/upgrade-3/syntax/Order/tree/
    """

    @api.model
    def _is_customer_behind_chorus_pro(self, customer):
        return customer.peppol_eas and customer.peppol_endpoint and f"{customer.peppol_eas}:{customer.peppol_endpoint}" == CHORUS_PRO_PEPPOL_ID

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_bis3.xml"

    # -------------------------------------------------------------------------
    # EXPORT: BIS3 LAYER
    # -------------------------------------------------------------------------
    def _can_export_selfbilling(self):
        return bool(self._get_customization_id(process_type='selfbilling'))

    def _get_customization_id(self, process_type: Literal['billing', 'selfbilling'] = 'billing'):
        if process_type == 'billing':
            return 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0'
        else:
            return 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:selfbilling:3.0'

    def _add_invoice_accounting_supplier_party_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
        }
        self._ubl_add_accounting_supplier_party_node(sub_vals)

    def _add_invoice_accounting_customer_party_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
        }
        self._ubl_add_accounting_customer_party_node(sub_vals)

    def _add_invoice_delivery_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
        }
        self._ubl_add_delivery_nodes(sub_vals)

    def _add_invoice_allowance_charge_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_allowance_charge_nodes(sub_vals)

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        # OVERRIDE
        invoice = vals.get('invoice')
        if not invoice:
            return

        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_legal_monetary_total_node(sub_vals)

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_payment_means_nodes(sub_vals)

    def _add_invoice_payment_terms_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }

        self._ubl_add_payment_terms_nodes(sub_vals)

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_tax_totals_nodes(sub_vals)

    def _add_invoice_monetary_total_vals(self, vals):
        # OVERRIDE
        pass

    def _add_invoice_line_id_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_id_node(sub_vals)

    def _add_invoice_line_allowance_charge_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_allowance_charge_nodes(sub_vals)

    def _add_invoice_line_amount_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }

        if vals['document_type'] == 'credit_note':
            self._ubl_add_line_credited_quantity_node(sub_vals)
        else:
            self._ubl_add_line_invoiced_quantity_node(sub_vals)

        self._ubl_add_line_extension_amount_node(sub_vals)

    def _add_invoice_line_period_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_period_nodes(sub_vals)

    def _add_invoice_line_pricing_reference_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_pricing_reference_node(sub_vals)

    def _add_invoice_line_tax_total_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_tax_totals_nodes(sub_vals)

    def _add_invoice_line_tax_category_nodes(self, line_node, vals):
        # OVERRIDE
        pass

    def _add_invoice_line_item_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_item_node(sub_vals)

    def _add_invoice_line_price_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_price_node(sub_vals)

    def _ubl_add_invoice_line_node(self, vals):
        # OVERRIDE. For retro-compatibility, ensure '_get_invoice_line_node' is called.
        sub_vals = {
            **vals,
            'base_line': vals['line_vals']['base_line'],
        }
        vals['line_node'].update(self._get_invoice_line_node(sub_vals))

    def _ubl_add_credit_note_line_node(self, vals):
        # OVERRIDE. For retro-compatbility, ensure '_get_invoice_line_node' is called.
        sub_vals = {
            **vals,
            'base_line': vals['line_vals']['base_line'],
        }
        vals['line_node'].update(self._get_invoice_line_node(sub_vals))

    def _add_invoice_line_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        if vals['document_type'] == 'invoice':
            self._ubl_add_invoice_line_nodes(sub_vals)
        elif vals['document_type'] == 'credit_note':
            self._ubl_add_credit_note_line_nodes(sub_vals)

    def _add_invoice_header_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_version_id_node(sub_vals)
        self._ubl_add_customization_id_node(sub_vals)
        self._ubl_add_profile_id_node(sub_vals)
        self._ubl_add_id_node(sub_vals)
        self._ubl_add_copy_indicator_node(sub_vals)
        self._ubl_add_issue_date_node(sub_vals)
        if vals['document_type'] == 'invoice':
            self._ubl_add_due_date_node(sub_vals)
            self._ubl_add_invoice_type_code_node(sub_vals)
        elif vals['document_type'] == 'credit_note':
            self._ubl_add_credit_note_type_code_node(sub_vals)
        self._ubl_add_notes_nodes(sub_vals)
        self._ubl_add_document_currency_code_node(sub_vals)
        self._ubl_add_tax_currency_code_node(sub_vals)
        self._ubl_add_buyer_reference_node(sub_vals)
        self._ubl_add_invoice_period_nodes(sub_vals)
        self._ubl_add_order_reference_node(sub_vals)
        self._ubl_add_billing_reference_nodes(sub_vals)

    def _add_invoice_config_vals(self, vals):
        super()._add_invoice_config_vals(vals)
        invoice = vals['invoice']
        vals.update(self._init_invoice_export_values(invoice))

    def _setup_base_lines(self, vals):
        # OVERRIDE
        pass

    def _add_invoice_base_lines_vals(self, vals):
        # OVERRIDE
        pass

    def _add_invoice_line_vals(self, vals):
        # OVERRIDE
        pass

    # -------------------------------------------------------------------------
    # EXPORT: Constraints
    # -------------------------------------------------------------------------

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals)
        constraints.update(self._export_document_node_constraints(vals))

        constraints.update(
            self._invoice_constraints_peppol_en16931_ubl(invoice, vals)
        )
        constraints.update(
            self._invoice_constraints_cen_en16931_ubl(invoice, vals)
        )

        return constraints

    def _invoice_constraints_cen_en16931_ubl(self, invoice, vals):
        return {}

    def _invoice_constraints_peppol_en16931_ubl(self, invoice, vals):
        """
        corresponds to the errors raised by 'schematron/openpeppol/3.13.0/xslt/PEPPOL-EN16931-UBL.xslt' for
        invoices in ecosio. This xslt was obtained by transforming the corresponding sch
        https://docs.peppol.eu/poacc/billing/3.0/files/PEPPOL-EN16931-UBL.sch.

        The national rules (https://docs.peppol.eu/poacc/billing/3.0/bis/#national_rules) are included in this file.
        They always refer to the supplier's country.
        """
        constraints = {}

        if vals['supplier'].country_id.code == 'NO':
            vat = vals['supplier'].vat
            constraints.update({
                # NO-R-001: For Norwegian suppliers, a VAT number MUST be the country code prefix NO followed by a
                # valid Norwegian organization number (nine numbers) followed by the letters MVA.
                # Note: mva.is_valid("179728982MVA") is True while it lacks the NO prefix
                'no_r_001': _(
                    "The VAT number of the supplier does not seem to be valid. It should be of the form: NO179728982MVA."
                ) if not mva.is_valid(vat) or len(vat) != 14 or vat[:2] != 'NO' or vat[-3:] != 'MVA' else "",
            })

        if vals['supplier'].country_id.code == 'BE' and vals['supplier'].company_registry:
            if not be_vat.is_valid(vals['supplier'].company_registry):
                constraints.update({
                    'PEPPOL-COMMON-R043_supplier': _('%s should have a valid KBO/BCE number in the Company ID field', vals['supplier'].display_name),
                })

        if vals['customer'].country_id.code == 'BE' and vals['customer'].company_registry:
            if not be_vat.is_valid(vals['customer'].company_registry):
                constraints.update({
                    'PEPPOL-COMMON-R043_customer': _('%s should have a valid KBO/BCE number in the Company ID field', vals['customer'].display_name),
                })
        return constraints

    # -------------------------------------------------------------------------
    # Sale/Purchase Order: Import
    # -------------------------------------------------------------------------

    def _import_order_payment_terms_id(self, company_id, tree, xpath):
        """ Return payment term name from given tree and try to find a match. """
        payment_term_name = self._find_value(xpath, tree)
        if not payment_term_name:
            return False
        payment_term_domain = self.env['account.payment.term']._check_company_domain(company_id)
        payment_term_domain.append(('name', '=', payment_term_name))
        return self.env['account.payment.term'].search(payment_term_domain, limit=1)

    def _retrieve_order_vals(self, order, tree):
        order_vals = {}
        logs = []

        order_vals['date_order'] = tree.findtext('.//{*}EndDate') or tree.findtext('.//{*}IssueDate')
        order_vals['note'] = self._import_description(tree, xpaths=['./{*}Note'])
        order_vals['payment_term_id'] = self._import_order_payment_terms_id(order.company_id, tree, './/cac:PaymentTerms/cbc:Note')
        order_vals['currency_id'], currency_logs = self._import_currency(tree, './/{*}DocumentCurrencyCode')

        logs += currency_logs
        return order_vals, logs

    def _import_order_ubl(self, order, file_data, new):
        """ Common importing method to extract order data from file_data.
        :param order: Order to fill details from file_data.
        :param file_data: File data to extract order related data from.
        :return: True if there's no exception while extraction.
        :rtype: Boolean
        """
        tree = file_data['xml_tree']

        # Update the order.
        order_vals, logs = self._retrieve_order_vals(order, tree)
        if order:
            order.write(order_vals)
            order.message_post(body=Markup("<strong>%s</strong>") % _("Format used to import the document: %s", self._description))
            if logs:
                order._create_activity_set_details(Markup("<ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % l for l in logs))

    def _import_invoice_ubl_cii(self, invoice, file_data, new=False):
        """
        corresponds to the errors raised by 'schematron/openpeppol/3.13.0/xslt/PEPPOL-EN16931-UBL.xslt' for
        invoices in ecosio. This xslt was obtained by transforming the corresponding sch
        https://docs.peppol.eu/poacc/billing/3.0/files/PEPPOL-EN16931-UBL.sch.

        The national rules (https://docs.peppol.eu/poacc/billing/3.0/bis/#national_rules) are included in this file.
        They always refer to the supplier's country.
        """
        if invoice.invoice_line_ids:
            return invoice._reason_cannot_decode_has_invoice_lines()
        return self._ubl_import_invoice(invoice, file_data, new=new)
