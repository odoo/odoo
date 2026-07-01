from datetime import datetime
import logging
import io

from markupsafe import Markup
from lxml import etree

from odoo.addons.account.tools import dict_to_xml
from odoo import _, api, fields, models, Command
from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, float_repr, format_list, html2plaintext, pdf, str2bool
from odoo.tools.float_utils import float_round
from odoo.tools.translate import _lt
from odoo.tools.misc import clean_context, formatLang, html_escape
from odoo.tools.xml_utils import find_xml_value

_logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# UNIT OF MEASURE
# -------------------------------------------------------------------------
UOM_TO_UNECE_CODE = {
    'uom.product_uom_unit': 'C62',
    'uom.product_uom_dozen': 'DZN',
    'uom.product_uom_kgm': 'KGM',
    'uom.product_uom_gram': 'GRM',
    'uom.product_uom_day': 'DAY',
    'uom.product_uom_hour': 'HUR',
    'uom.product_uom_minute': 'MIN',
    'uom.product_uom_ton': 'TNE',
    'uom.product_uom_meter': 'MTR',
    'uom.product_uom_km': 'KMT',
    'uom.product_uom_cm': 'CMT',
    'uom.product_uom_litre': 'LTR',
    'uom.product_uom_cubic_meter': 'MTQ',
    'uom.product_uom_lb': 'LBR',
    'uom.product_uom_oz': 'ONZ',
    'uom.product_uom_inch': 'INH',
    'uom.product_uom_foot': 'FOT',
    'uom.product_uom_mile': 'SMI',
    'uom.product_uom_floz': 'OZA',
    'uom.product_uom_qt': 'QTL',
    'uom.product_uom_gal': 'GLL',
    'uom.product_uom_cubic_inch': 'INQ',
    'uom.product_uom_cubic_foot': 'FTQ',
    'uom.uom_square_meter': 'MTK',
    'uom.uom_square_foot': 'FTK',
    'uom.product_uom_yard': 'YRD',
    'uom.product_uom_millimeter': 'MMT',
    'uom.product_uom_kwh': 'KWH',
}

# -------------------------------------------------------------------------
# ELECTRONIC ADDRESS SCHEME (EAS), see https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/
# -------------------------------------------------------------------------
EAS_MAPPING = {
    'AD': {'9922': 'vat'},
    'AE': {'0235': 'vat'},
    'AL': {'9923': 'vat'},
    'AT': {'9915': 'vat'},
    'AU': {'0151': 'vat'},
    'BA': {'9924': 'vat'},
    'BE': {'0208': 'company_registry', '9925': 'vat'},
    'BG': {'9926': 'vat'},
    'CH': {'9927': 'vat', '0183': None},
    'CY': {'9928': 'vat'},
    'CZ': {'9929': 'vat'},
    'DE': {'9930': 'vat', '0246': 'l10n_de_widnr'},
    'DK': {'0184': 'vat', '0198': 'vat'},
    'EE': {'9931': 'vat'},
    'ES': {'9920': 'vat'},
    'FI': {'0216': None, '0213': 'vat'},
    'FR': {'0225': 'peppol_endpoint', '0009': 'siret', '9957': 'vat', '0002': None},  # `peppol_endpoint` used as place holder for custom logic via `_get_peppol_endpoint_value`
    'SG': {'0195': 'l10n_sg_unique_entity_number'},
    'GB': {'9932': 'vat'},
    'GR': {'9933': 'vat'},
    'HR': {'9934': 'vat', '0088': 'company_registry'},
    'HU': {'9910': 'l10n_hu_eu_vat'},
    'IE': {'9935': 'vat'},
    'IS': {'0196': 'vat'},
    'IT': {'0211': 'vat', '0210': 'l10n_it_codice_fiscale'},
    'JP': {'0221': 'vat'},
    'LI': {'9936': 'vat'},
    'LT': {'9937': 'vat'},
    'LU': {'9938': 'vat'},
    'LV': {'0218': 'company_registry', '9939': 'vat'},
    'MC': {'9940': 'vat'},
    'ME': {'9941': 'vat'},
    'MK': {'9942': 'vat'},
    'MT': {'9943': 'vat'},
    'MY': {'0230': None},
    # Do not add the vat for NL, since: "[NL-R-003] For suppliers in the Netherlands, the legal entity identifier
    # MUST be either a KVK or OIN number (schemeID 0106 or 0190)" in the Bis 3 rules (in PartyLegalEntity/CompanyID).
    'NG': {'0244': 'vat'},
    'NL': {'0106': None, '0190': None},
    'NO': {'0192': 'l10n_no_bronnoysund_number'},
    'NZ': {'0088': 'company_registry'},
    'PL': {'9945': 'vat'},
    'PT': {'9946': 'vat'},
    'RO': {'9947': 'vat'},
    'RS': {'9948': 'vat'},
    'SE': {'0007': 'company_registry', '9955': 'vat'},
    'SI': {'9949': 'vat'},
    'SK': {'9950': 'vat', '0245': 'company_registry'},
    'SM': {'9951': 'vat'},
    'TR': {'9952': 'vat'},
    'VA': {'9953': 'vat'},
    # DOM-TOM
    'BL': {'0009': 'siret', '9957': 'vat', '0002': None},  # Saint Barthélemy
    'GF': {'0009': 'siret', '9957': 'vat', '0002': None},  # French Guiana
    'GP': {'0009': 'siret', '9957': 'vat', '0002': None},  # Guadeloupe
    'MF': {'0009': 'siret', '9957': 'vat', '0002': None},  # Saint Martin
    'MQ': {'0009': 'siret', '9957': 'vat', '0002': None},  # Martinique
    'NC': {'0009': 'siret', '9957': 'vat', '0002': None},  # New Caledonia
    'PF': {'0009': 'siret', '9957': 'vat', '0002': None},  # French Polynesia
    'PM': {'0009': 'siret', '9957': 'vat', '0002': None},  # Saint Pierre and Miquelon
    'RE': {'0009': 'siret', '9957': 'vat', '0002': None},  # Réunion
    'TF': {'0009': 'siret', '9957': 'vat', '0002': None},  # French Southern and Antarctic Lands
    'WF': {'0009': 'siret', '9957': 'vat', '0002': None},  # Wallis and Futuna
    'YT': {'0009': 'siret', '9957': 'vat', '0002': None},  # Mayotte
}

# -------------------------------------------------------------------------
# AREA of countries
# -------------------------------------------------------------------------

GST_COUNTRY_CODES = {
    'AU', 'NZ', 'IN', 'SG', 'MY', 'PK', 'BD', 'LK', 'NP', 'BT', 'PG', 'SA',
    'AG', 'BS', 'BB', 'DM', 'GD', 'JM', 'KN', 'LC', 'VC', 'TT',
}

EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES = {
    # EU Member States
    'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE',
    'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'CH',

    # EFTA Countries in the EEA
    'IS', 'LI', 'NO',
}

COCONTRACTANT_DEFAULT_NOTE = _lt('Reverse charge: In the absence of a written objection within one month of receipt of the invoice, '
                              'the customer is deemed to acknowledge that they are a taxable person required to file periodic returns. '
                              'If this condition is not met, the customer will be liable for the payment of the tax, interest, '
                              'and penalties due in relation to this condition.')


class FloatFmt(float):
    """ A float with a given precision.
    The precision is used when formatting the float.
    """
    def __new__(cls, value, min_dp=2, max_dp=None):
        return super().__new__(cls, value)

    def __init__(self, value, min_dp=2, max_dp=None):
        self.min_dp = min_dp
        self.max_dp = max_dp

    def __str__(self):
        if not isinstance(self.min_dp, int) or (self.max_dp is not None and not isinstance(self.max_dp, int)):
            return "<FloatFmt()>"
        # why do we round ?
        # imagine we have: 0.499 and max_dp = 2.
        # The best representation for 0.499 with max_dp = 2 is 0.50 not 0.49
        # rounding with max_dp precision ensure we have the best representation with max_dp decimal places.
        self_float = float_round(float(self), self.min_dp if self.max_dp is None else self.max_dp)
        if self.max_dp is None:
            return float_repr(self_float, self.min_dp)
        else:
            # Format the float to between self.min_dp and self.max_dp decimal places.
            # We start by formatting to self.max_dp, and then remove trailing zeros,
            # but always keep at least self.min_dp decimal places.
            amount_max_dp = float_repr(self_float, self.max_dp)
            num_trailing_zeros = len(amount_max_dp) - len(amount_max_dp.rstrip('0'))
            return float_repr(self_float, max(self.max_dp - num_trailing_zeros, self.min_dp))

    def __repr__(self):
        if not isinstance(self.min_dp, int) or (self.max_dp is not None and not isinstance(self.max_dp, int)):
            return "<FloatFmt()>"
        self_float = float(self)
        if self.max_dp is None:
            return f"FloatFmt({self_float!r}, {self.min_dp!r})"
        else:
            return f"FloatFmt({self_float!r}, {self.min_dp!r}, {self.max_dp!r})"


class AccountEdiCommon(models.AbstractModel):
    _name = "account.edi.common"
    _description = "Common functions for EDI documents: generate the data, the constraints, etc"

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _vals_to_etree(self, vals):
        document_node = vals['document_node']
        return dict_to_xml(document_node, nsmap=document_node['_nsmap'], template=document_node['_template'])

    def _etree_to_string(self, tree):
        return etree.tostring(tree, xml_declaration=True, encoding='UTF-8')

    def _define_document_type(self, vals, document_type):
        vals['_document_type'] = {
            'name': document_type,
            'model': self,
        }

    def _get_document_type(self, vals):
        return vals.get('_document_type', {}).get('name')

    def _is_document(self, vals, *document_types):
        return self._get_document_type(vals) in document_types

    def module_installed(self, module_name):
        return self.env['ir.module.module']._get(module_name).state == 'installed'

    def format_float(self, amount, precision_digits):
        if amount is None:
            return None
        return float_repr(float_round(amount, precision_digits), precision_digits)

    def _get_currency_decimal_places(self, currency_id):
        # Allows other documents to easily override in case there is a flat max precision number
        return currency_id.decimal_places

    def _get_uom_unece_code(self, uom):
        """
        list of codes: https://docs.peppol.eu/poacc/billing/3.0/codelist/UNECERec20/ (sorted by letter)
        """
        xmlid = uom.get_external_id()
        if xmlid and uom.id in xmlid:
            return UOM_TO_UNECE_CODE.get(xmlid[uom.id], 'C62')
        return 'C62'

    def _find_value(self, xpaths, tree, nsmap=False):
        """ Iteratively queries the tree using the xpaths and returns a result as soon as one is found """
        if not isinstance(xpaths, (tuple, list)):
            xpaths = [xpaths]
        for xpath in xpaths:
            # functions from ElementTree like "findtext" do not fully implement xpath, use "xpath" (from lxml) instead
            # (e.g. "//node[string-length(text()) > 5]" raises an invalidPredicate exception with "findtext")
            val = find_xml_value(xpath, tree, nsmap)
            if val:
                return val

    def _can_export_selfbilling(self):
        return False

    def _get_belgian_cocontractant_note(self, customer, supplier):

        if (invoice := self.env.context.get('tax_exemption_reason_invoice')) and customer.country_id.code == 'BE' and supplier.country_id == customer.country_id:
            co_contractant = self.env['account.chart.template'].ref('fiscal_position_template_4', raise_if_not_found=False)
            if co_contractant and invoice.fiscal_position_id == co_contractant:
                note = html2plaintext(invoice.fiscal_position_id.note) if invoice.fiscal_position_id.note else ''
                return note or COCONTRACTANT_DEFAULT_NOTE
        return ''

    # -------------------------------------------------------------------------
    # TAXES
    # -------------------------------------------------------------------------

    def _validate_taxes(self, tax_ids):
        """ Validate the structure of the tax repartition lines (invalid structure could lead to unexpected results) """
        for tax in tax_ids:
            try:
                tax._validate_repartition_lines()
            except ValidationError as e:
                error_msg = _("Tax '%(tax_name)s' is invalid: %(error_message)s", tax_name=tax.name, error_message=e.args[0])  # args[0] gives the error message
                raise ValidationError(error_msg)

    def _get_tax_unece_codes(self, customer, supplier, tax):
        """
        Source: doc of Peppol (but the CEF norm is also used by factur-x, yet not detailed)
        https://docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice/cac-TaxTotal/cac-TaxSubtotal/cac-TaxCategory/cbc-TaxExemptionReasonCode/
        https://docs.peppol.eu/poacc/billing/3.0/codelist/vatex/
        https://docs.peppol.eu/poacc/billing/3.0/codelist/UNCL5305/
        :returns: {
            tax_category_code: str,
            tax_exemption_reason_code: str,
            tax_exemption_reason: str,
        }
        """

        def create_dict(tax_category_code=None, tax_exemption_reason_code=None, tax_exemption_reason=None):
            return {
                'tax_category_code': tax_category_code,
                'tax_exemption_reason_code': tax_exemption_reason_code,
                'tax_exemption_reason': tax_exemption_reason,
            }

        # add Norway, Iceland, Liechtenstein
        if customer.country_id.code == 'ES' and customer.zip:
            if customer.zip[:2] in ('35', '38'):  # Canary
                # [BR-IG-10]-A VAT breakdown (BG-23) with VAT Category code (BT-118) "IGIC" shall not have a VAT
                # exemption reason code (BT-121) or VAT exemption reason text (BT-120).
                return create_dict(tax_category_code='L')
            if customer.zip[:2] in ('51', '52'):
                return create_dict(tax_category_code='M')  # Ceuta & Mellila

        cocontractant_note = self._get_belgian_cocontractant_note(customer, supplier)
        if cocontractant_note:
            if not tax.amount:
                return create_dict(
                    tax_category_code='AE',
                    tax_exemption_reason_code='VATEX-EU-AE',
                    tax_exemption_reason=cocontractant_note
                )
            raise UserError(_("Invalid Tax Setup for Co-Contractor. Please apply the standard co-contractor tax, or ensure your custom tax uses a tax amount of 0"))

        if supplier.country_id == customer.country_id:
            if not tax or tax.amount == 0:
                # in theory, you should indicate the precise law article
                return create_dict(tax_category_code='E')
            elif tax.has_negative_factor:
                # Special case: Purchase reverse-charge taxes for self-billed invoices.
                # From the buyer's perspective, this is a standard tax with a non-zero percentage but
                # two tax repartition lines that cancel each other out.
                # But from the seller's perspective, this is a zero-percent tax (VAT liability is deferred
                # to the buyer).
                # For a self-billed invoice we, the buyer, create the invoice on behalf of the seller.
                # So in the XML we put the zero-percent tax with code 'AE' that the seller would have used.
                return create_dict(tax_category_code='AE')
            else:
                return create_dict(tax_category_code='S')  # standard VAT

        if supplier.country_id.code in EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES and supplier.vat:
            if tax.amount != 0 and not tax.has_negative_factor:
                # otherwise, the validator will complain because G and K code should be used with 0% tax
                # For purchase reverse-charge taxes for self-billed invoices, we put the zero-percent tax
                # with code 'G' or 'K' that the buyer would have used, see explanation above.
                return create_dict(tax_category_code='S')
            if customer.country_id.code not in EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES:
                return create_dict(
                    tax_category_code='G',
                    tax_exemption_reason_code='VATEX-EU-G',
                    tax_exemption_reason=_('Export outside the EU'),
                )
            if customer.country_id.code in EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES:
                return create_dict(
                    tax_category_code='K',
                    tax_exemption_reason_code='VATEX-EU-IC',
                    tax_exemption_reason=_('Intra-Community supply'),
                )

        if tax.amount != 0:
            return create_dict(tax_category_code='S')
        else:
            return create_dict(tax_category_code='E')

    def _get_tax_category_code(self, customer, supplier, tax):
        if not tax:
            return 'E'
        return self._get_tax_unece_codes(customer, supplier, tax).get('tax_category_code')

    def _get_tax_exemption_reason(self, customer, supplier, tax):
        if not tax:
            return {
                'tax_exemption_reason': _("Exempt from tax"),
                'tax_exemption_reason_code': None,
            }
        res = self._get_tax_unece_codes(customer, supplier, tax)
        return {
            'tax_exemption_reason': res.get('tax_exemption_reason'),
            'tax_exemption_reason_code': res.get('tax_exemption_reason_code'),
        }

    def _get_tax_category_list(self, customer, supplier, taxes):
        """ Full list: https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred5305.htm
        Subset: https://docs.peppol.eu/poacc/billing/3.0/codelist/UNCL5305/

        :param taxes:   account.tax records.
        :return:        A list of values to fill the TaxCategory foreach template.
        """
        res = []
        for tax in taxes:
            tax_unece_codes = self._get_tax_unece_codes(customer, supplier, tax)
            res.append({
                'id': tax_unece_codes.get('tax_category_code'),
                'percent': tax.amount if tax.amount_type == 'percent' else False,
                'name': tax_unece_codes.get('tax_exemption_reason'),
                'tax_scheme_vals': {'id': 'VAT'},
                **tax_unece_codes,
            })
        return res

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    def _check_required_fields(self, record, field_names, custom_warning_message=""):
        """Check if at least one of the field_names are set on the record/dict

        :param record: either a recordSet or a dict
        :param field_names: The field name or list of field name that has to
                            be checked. If a list is provided, check that at
                            least one of them is set.
        :return: an Error message or None
        """
        if not record:
            return custom_warning_message or _("The element %(record)s is required on %(field_list)s.", record=record, field_list=format_list(self.env, field_names))

        if not isinstance(field_names, (list, tuple)):
            field_names = (field_names,)

        has_values = any((field_name in record and record[field_name]) for field_name in field_names)
        # field is present
        if has_values:
            return

        # field is not present
        if custom_warning_message or isinstance(record, dict):
            return custom_warning_message or _(
                "The element %(record)s is required on %(field_list)s.",
                record=record,
                field_list=format_list(self.env, field_names),
            )

        display_field_names = record.fields_get(field_names)
        if len(field_names) == 1:
            display_field = f"'{display_field_names[field_names[0]]['string']}'"
            return _("The field %(field)s is required on %(record)s.", field=display_field, record=record.display_name)
        else:
            display_fields = format_list(self.env, [f"'{display_field_names[x]['string']}'" for x in display_field_names])
            return _("At least one of the following fields %(field_list)s is required on %(record)s.", field_list=display_fields, record=record.display_name)

    # -------------------------------------------------------------------------
    # COMMON CONSTRAINTS
    # -------------------------------------------------------------------------

    def _invoice_constraints_common(self, invoice):
        # check that there is a tax on each line
        for line in invoice.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_note', 'line_section') and x._check_edi_line_tax_required()):
            if not line.tax_ids:
                return {'tax_on_line': _("Each invoice line should have at least one tax.")}
        return {}

    # -------------------------------------------------------------------------
    # Import invoice
    # -------------------------------------------------------------------------

    def _import_invoice_ubl_cii(self, invoice, file_data, new=False):
        tree = file_data['xml_tree']

        # Not able to decode the move_type from the xml.
        move_type, qty_factor = self._get_import_document_amount_sign(tree)
        if not move_type:
            return

        # Check for inconsistent move_type.
        journal = invoice.journal_id
        if journal.type == 'sale':
            move_type = 'out_' + move_type
        elif journal.type == 'purchase':
            move_type = 'in_' + move_type
        else:
            return
        if not new and invoice.move_type != move_type:
            # with an email alias to create account_move, first the move is created (using alias_defaults, which
            # contains move_type = 'out_invoice') then the attachment is decoded, if it represents a credit note,
            # the move type needs to be changed to 'out_refund'
            types = {move_type, invoice.move_type}
            if types == {'out_invoice', 'out_refund'} or types == {'in_invoice', 'in_refund'}:
                invoice.move_type = move_type
            else:
                return

        # Update the invoice.
        invoice.move_type = move_type
        with invoice._get_edi_creation() as invoice:
            logs = self._import_fill_invoice(invoice, tree, qty_factor)
        if invoice:
            body = Markup("<strong>%s</strong>") % \
                _("Format used to import the invoice: %s",
                  self.env['ir.model']._get(self._name).name)

            if logs:
                body += Markup("<ul>%s</ul>") % \
                    Markup().join(Markup("<li>%s</li>") % l for l in logs)

            invoice.message_post(body=body)

        # For UBL, we should override the computed tax amount if it is less than 0.05 different of the one in the xml.
        # In order to support use case where the tax total is adapted for rounding purpose.
        # This has to be done after the first import in order to let Odoo compute the taxes before overriding if needed.
        with invoice._get_edi_creation() as invoice:
            self._correct_invoice_tax_amount(tree, invoice)

        # Set XML as ubl_cii_xml_file (XML used to import)
        if invoice.is_purchase_document(include_receipts=True):
            file_data['attachment'].write({
                'res_field': 'ubl_cii_xml_file',
                'res_model': invoice._name,
                'res_id': invoice.id,
            })

        attachments = self._import_attachments(invoice, tree)
        if attachments:
            invoice.with_context(no_new_invoice=True).message_post(attachment_ids=attachments.ids)

        return True

    def _import_attachments(self, invoice, tree):
        # Import the embedded documents in the xml if some are found
        attachments = self.env['ir.attachment']
        if invoice.message_main_attachment_id:
            # Invoice look like it was already imported, don't import attachments again
            return attachments

        attachments_data = attachments._extract_additional_documents(tree)
        for data in attachments_data:
            data.update({
                'res_id': invoice.id,
                'res_model': invoice._name,
            })
        attachments = self.env['ir.attachment'].create(attachments_data)
        # Upon receiving an email (containing an xml) with a configured alias to create invoice, the xml is
        # set as the main_attachment. To be rendered in the form view, the pdf should be the main_attachment.
        for attachment in attachments:
            if invoice.message_main_attachment_id and \
                    invoice.message_main_attachment_id.name.endswith('.xml') and \
                    'pdf' not in invoice.message_main_attachment_id.mimetype and \
                    attachment.mimetype == 'application/pdf':
                invoice._message_set_main_attachment_id(attachment, force=True, filter_xml=False)
        return attachments

    def _import_partner(self, company_id, name, phone, email, vat, country_code=False, peppol_eas=False, peppol_endpoint=False, street=False, street2=False, city=False, zip_code=False):
        """ Retrieve the partner, if no matching partner is found, create it (only if he has a vat and a name) """
        logs = []
        if peppol_eas and peppol_endpoint:
            domain = [('peppol_eas', '=', peppol_eas), ('peppol_endpoint', '=', peppol_endpoint)]
        else:
            domain = False
        partner = self.env['res.partner'] \
            .with_company(company_id) \
            ._retrieve_partner(name=name, phone=phone, email=email, vat=vat, domain=domain)
        if not partner and name and vat:
            partner_vals = {'name': name, 'email': email, 'phone': phone, 'street': street, 'street2': street2,
                            'zip': zip_code, 'city': city, 'is_company': True}
            if peppol_eas and peppol_endpoint:
                partner_vals.update({'peppol_eas': peppol_eas, 'peppol_endpoint': peppol_endpoint})
            if country_code == 'GB':
                # While the code is gb, the xml_id is uk
                country_code = 'UK'
            country = self.env.ref(f'base.{country_code.lower()}', raise_if_not_found=False) if country_code else False
            if country:
                partner_vals['country_id'] = country.id
            partner = self.env['res.partner'].create(partner_vals)
            if vat and self.env['res.partner']._run_vat_test(vat, country, partner.is_company):
                partner.vat = vat
            logs.append(_("Could not retrieve a partner corresponding to '%s'. A new partner was created.", name))
        return partner, logs

    def _import_partner_bank(self, invoice, bank_details):
        if invoice.move_type in ('out_refund', 'in_invoice'):
            partner = invoice.partner_id
        elif invoice.move_type in ('out_invoice', 'in_refund'):
            partner = invoice.company_id.partner_id
        else:
            return

        banks = self.env['res.partner.bank']
        for account_number in bank_details:
            try:
                banks += self.env['res.partner.bank']._find_or_create_bank_account(
                    account_number=account_number,
                    partner=partner,
                    company=invoice.company_id,
                )
            except UserError as e:
                invoice._message_log(body=_("The bank account couldn't be fetched: %s", str(e)))
        if banks:
            invoice.partner_bank_id = banks[0]

    def _import_document_allowance_charges(self, tree, record, tax_type, qty_factor=1):
        logs = []
        xpaths = self._get_document_allowance_charge_xpaths()
        line_vals = []
        for allow_el in tree.iterfind(xpaths['root']):
            name = allow_el.findtext(xpaths['reason']) or ""
            # Charge indicator factor: -1 for discount, 1 for charge
            charge_indicator = -1 if allow_el.findtext(xpaths['charge_indicator']).lower() == 'false' else 1
            amount = float(allow_el.findtext(xpaths['amount']) or 0)
            base_amount = float(allow_el.findtext(xpaths['base_amount']) or 0)
            if base_amount:
                price_unit = base_amount * charge_indicator * qty_factor
                percentage = float(allow_el.findtext(xpaths['percentage']) or 100)
                quantity = percentage / 100
            else:
                price_unit = amount * charge_indicator * qty_factor
                quantity = 1

            # Taxes
            tax_ids = []
            for tax_percent_node in allow_el.iterfind(xpaths['tax_percentage']):
                tax_amount = float(tax_percent_node.text)
                tax = self.env['account.tax'].search([
                    *self.env['account.tax']._check_company_domain(record.company_id),
                    ('amount', '=', tax_amount),
                    ('amount_type', '=', 'percent'),
                    ('type_tax_use', '=', tax_type),
                ], limit=1)
                if tax:
                    tax_ids += tax.ids
                elif name:
                    logs.append(_(
                        "Could not retrieve the tax: %(tax_percentage)s %% for line '%(line)s'.",
                        tax_percentage=tax_amount,
                        line=name,
                    ))
                else:
                    logs.append(
                        _("Could not retrieve the tax: %s for the document level allowance/charge.", tax_amount))

            line_vals.append([name, quantity, price_unit, tax_ids])
        return record._get_line_vals_list(line_vals), logs

    def _import_currency(self, tree, xpath):
        logs = []
        currency_name = tree.findtext(xpath)
        currency = self.env.company.currency_id
        if currency_name is not None:
            currency = currency.with_context(active_test=False).search([
                ('name', '=', currency_name),
            ], limit=1)
            if currency:
                if not currency.active:
                    logs.append(_("The currency '%s' is not active.", currency.name))
            else:
                logs.append(_("Could not retrieve currency: %s. Did you enable the multicurrency option "
                              "and activate the currency?", currency_name))
        return currency.id, logs

    def _import_description(self, tree, xpaths):
        description = ""
        for xpath in xpaths:
            note = tree.findtext(xpath)
            if note:
                description += f"<p>{html_escape(note)}</p>"
        return description

    def _import_prepaid_amount(self, invoice, tree, xpath, qty_factor):
        logs = []
        prepaid_amount = float(tree.findtext(xpath) or 0)
        if not invoice.currency_id.is_zero(prepaid_amount):
            amount = prepaid_amount * qty_factor
            formatted_amount = formatLang(self.env, amount, currency_obj=invoice.currency_id)
            logs.append(_("A payment of %s was detected.", formatted_amount))
        return logs

    def _import_rounding_amount(self, invoice, tree, xpath, qty_factor):
        """
        Add an invoice line representing the rounding amount given in the document.
        - The amount is assumed to be in document currency
        """
        logs = []
        line_vals = []

        currency = invoice.currency_id
        rounding_amount_currency = currency.round(qty_factor * float(tree.findtext(xpath) or 0))

        if invoice.currency_id.is_zero(rounding_amount_currency):
            return line_vals, logs

        inverse_rate = abs(invoice.amount_total_signed) / invoice.amount_total if invoice.amount_total else 0
        rounding_amount = invoice.company_id.currency_id.round(rounding_amount_currency * inverse_rate)

        line_vals.append({
            'display_type': 'product',
            'name': _('Rounding'),
            'quantity': 1,
            'product_id': False,
            'price_unit': rounding_amount_currency,
            'amount_currency': invoice.direction_sign * rounding_amount_currency,
            'balance': invoice.direction_sign * rounding_amount,
            'company_id': invoice.company_id.id,
            'move_id': invoice.id,
            'tax_ids': False,
        })

        formatted_amount = formatLang(self.env, rounding_amount_currency, currency_obj=currency)
        logs.append(_("A rounding amount of %s was detected.", formatted_amount))

        return line_vals, logs

    def _import_invoice_lines(self, invoice, tree, xpath, qty_factor):
        logs = []
        lines_values = []
        for line_tree in tree.iterfind(xpath):
            line_values = self.with_company(invoice.company_id)._retrieve_invoice_line_vals(line_tree, invoice.move_type, qty_factor)
            if line_values is None:
                continue

            line_values['tax_ids'], tax_logs = self._retrieve_taxes(
                invoice, line_values, invoice.journal_id.type,
            )
            logs += tax_logs
            if not line_values['product_uom_id']:
                line_values.pop('product_uom_id')  # if no uom, pop it so it's inferred from the product_id
            lines_values.append(line_values)
            lines_values += self._retrieve_line_charges(invoice, line_values, line_values['tax_ids'])
        return lines_values, logs

    def _retrieve_invoice_line_vals(self, tree, document_type=False, qty_factor=1):
        # Start and End date (enterprise fields)
        xpath_dict = self._get_invoice_line_xpaths(document_type, qty_factor)
        deferred_values = {}
        start_date = end_date = None
        if self.env['account.move.line']._fields.get('deferred_start_date'):
            start_date_node = tree.find(xpath_dict['deferred_start_date'])
            end_date_node = tree.find(xpath_dict['deferred_end_date'])
            if start_date_node is not None and end_date_node is not None:  # there is a constraint forcing none or the two to be set
                start_date = datetime.strptime(start_date_node.text.strip(), xpath_dict['date_format'])
                end_date = datetime.strptime(end_date_node.text.strip(), xpath_dict['date_format'])
            deferred_values = {
                'deferred_start_date': start_date,
                'deferred_end_date': end_date,
            }

        line_vals = self._retrieve_line_vals(tree, document_type, qty_factor)
        if not line_vals.get('price_subtotal'):
            return None

        return {
            **line_vals,
            **deferred_values,
        }

    @api.model
    def _retrieve_rebate_val(self, tree, xpath_dict, quantity):
        # Discount. /!\ as no percent discount can be set on a line, need to infer the percentage
        # from the amount of the actual amount of the discount (the allowance charge)
        rebate = 0
        rebate_node = tree.find(xpath_dict['rebate'])
        net_price_unit_node = tree.find(xpath_dict['net_price_unit'])
        gross_price_unit_node = tree.find(xpath_dict['gross_price_unit'])
        if rebate_node is not None:
            rebate = float(rebate_node.text)
        elif net_price_unit_node is not None and gross_price_unit_node is not None:
            rebate = float(gross_price_unit_node.text) - float(net_price_unit_node.text)
        return rebate

    @api.model
    def _retrieve_charge_allowance_vals(self, tree, xpath_dict, quantity):
        charges = []
        discount_amount = 0
        for allowance_charge_node in tree.iterfind(xpath_dict['allowance_charge']):
            charge_indicator = allowance_charge_node.findtext(xpath_dict['allowance_charge_indicator']) or 'false'
            amount = float(allowance_charge_node.findtext(xpath_dict['allowance_charge_amount'], default='0'))
            reason_code = allowance_charge_node.findtext(xpath_dict['allowance_charge_reason_code'], default='')
            reason = allowance_charge_node.findtext(xpath_dict['allowance_charge_reason'], default='')
            if charge_indicator.lower() == 'true':
                charges.append({
                    'amount': amount,
                    'line_quantity': quantity,
                    'reason': reason,
                    'reason_code': reason_code,
                })
            else:
                discount_amount += amount
        return discount_amount, charges

    def _retrieve_line_vals(self, tree, document_type=False, qty_factor=1):
        """
        Read the xml invoice, extract the invoice line values, compute the odoo values
        to fill an invoice line form: quantity, price_unit, discount, product_uom_id.

        The way of computing invoice line is quite complicated:
        https://docs.peppol.eu/poacc/billing/3.0/bis/#_calculation_on_line_level (same as in factur-x documentation)

        line_net_subtotal = ( gross_unit_price - rebate ) * (delivered_qty / basis_qty) - allow_charge_amount

        with (UBL | CII):
            * net_unit_price = 'Price/PriceAmount' | 'NetPriceProductTradePrice' (mandatory) (BT-146)
            * gross_unit_price = 'Price/AllowanceCharge/BaseAmount' | 'GrossPriceProductTradePrice' (optional) (BT-148)
            * basis_qty = 'Price/BaseQuantity' | 'BasisQuantity' (optional, either below net_price node or
                gross_price node) (BT-149)
            * delivered_qty = 'InvoicedQuantity' (invoice) | 'BilledQuantity' (bill) | 'Quantity' (order) (mandatory) (BT-129)
            * allow_charge_amount = sum of 'AllowanceCharge' | 'SpecifiedTradeAllowanceCharge' (same level as Price)
                ON THE LINE level (optional) (BT-136 / BT-141)
            * line_net_subtotal = 'LineExtensionAmount' | 'LineTotalAmount' (mandatory) (BT-131)
            * rebate = 'Price/AllowanceCharge' | 'AppliedTradeAllowanceCharge' below gross_price node ! (BT-147)
                "item price discount" which is different from the usual allow_charge_amount
                gross_unit_price (BT-148) - rebate (BT-147) = net_unit_price (BT-146)

        In Odoo, we obtain:
        (1) = price_unit  =  gross_price_unit / basis_qty  =  (net_price_unit + rebate) / basis_qty
        (2) = quantity  =  delivered_qty
        (3) = discount (converted into a percentage)  =  100 * (1 - price_subtotal / (delivered_qty * price_unit))
        (4) = price_subtotal

        Alternatively, we could also set: quantity = delivered_qty/basis_qty

        WARNING, the basis quantity parameter is annoying, for instance, an invoice with a line:
            item A  | price per unit of measure/unit price: 30  | uom = 3 pieces | billed qty = 3 | rebate = 2  | untaxed total = 28
        Indeed, 30 $ / 3 pieces = 10 $ / piece => 10 * 3 (billed quantity) - 2 (rebate) = 28

        UBL ROUNDING: "the result of Item line net
            amount = ((Item net price (BT-146)÷Item price base quantity (BT-149))×(Invoiced Quantity (BT-129))
        must be rounded to two decimals, and the allowance/charge amounts are also rounded separately."
        It is not possible to do it in Odoo.
        """
        xpath_dict = self._get_line_xpaths(document_type, qty_factor)
        # basis_qty (optional)
        basis_qty = float(self._find_value(xpath_dict['basis_qty'], tree) or 1) or 1.0

        # gross_price_unit (optional)
        gross_price_unit = None
        gross_price_unit_node = tree.find(xpath_dict['gross_price_unit'])
        if gross_price_unit_node is not None:
            gross_price_unit = float(gross_price_unit_node.text)

        # net_price_unit (mandatory)
        net_price_unit = None
        net_price_unit_node = tree.find(xpath_dict['net_price_unit'])
        if net_price_unit_node is not None:
            net_price_unit = float(net_price_unit_node.text)

        # delivered_qty (mandatory)
        delivered_qty = 1
        product_vals = {k: self._find_value(v, tree) for k, v in xpath_dict['product'].items()}
        product = self._import_product(**product_vals)
        product_uom = self.env['uom.uom']
        quantity_node = tree.find(xpath_dict['delivered_qty'])
        if quantity_node is not None:
            delivered_qty = float(quantity_node.text)
            uom_xml = quantity_node.attrib.get('unitCode')
            if uom_xml:
                uom_infered_xmlid = {v: k for k, v in UOM_TO_UNECE_CODE.items()}.get(uom_xml)
                if uom_infered_xmlid:
                    product_uom = self.env.ref(uom_infered_xmlid, raise_if_not_found=False) or self.env['uom.uom']
        if product and product_uom and product_uom.category_id != product.product_tmpl_id.uom_id.category_id:
            # uom incompatibility
            product_uom = self.env['uom.uom']

        # line_net_subtotal (mandatory)
        price_subtotal = None
        line_total_amount_node = tree.find(xpath_dict['line_total_amount'])
        if line_total_amount_node is not None and line_total_amount_node.text and line_total_amount_node.text.strip():
            price_subtotal = float(line_total_amount_node.text)

        # quantity
        quantity = delivered_qty * qty_factor

        # rebate (optional)
        rebate = self._retrieve_rebate_val(tree, xpath_dict, quantity)

        # Charges are collected (they are used to create new lines), Allowances are transformed into discounts
        discount_amount, charges = self._retrieve_charge_allowance_vals(tree, xpath_dict, quantity)

        # price_unit
        charge_amount = sum(d['amount'] for d in charges)
        allow_charge_amount = discount_amount - charge_amount
        if gross_price_unit is not None:
            price_unit = gross_price_unit / basis_qty
        elif net_price_unit is not None:
            price_unit = (net_price_unit + rebate) / basis_qty
        elif price_subtotal is not None:
            price_unit = (price_subtotal + allow_charge_amount) / (delivered_qty or 1)
        else:
            price_unit = 0

        # discount
        discount = 0
        currency = self.env.company.currency_id
        if not float_is_zero(delivered_qty * price_unit, currency.decimal_places) and price_subtotal is not None:
            inferred_discount = 100 * (1 - (price_subtotal - charge_amount) / currency.round(delivered_qty * price_unit))
            discount = inferred_discount if not float_is_zero(inferred_discount, currency.decimal_places) else 0.0

        # Sometimes, the xml received is very bad; e.g.:
        #   * unit price = 0, qty = 0, but price_subtotal = -200
        #   * unit price = 0, qty = 1, but price_subtotal = -200
        #   * unit price = 1, qty = 0, but price_subtotal = -200
        # for instance, when filling a down payment as an document line. The equation in the docstring is not
        # respected, and the result will not be correct, so we just follow the simple rule below:
        if (
            net_price_unit is not None
            and price_subtotal is not None
            and float_compare(price_subtotal, net_price_unit * (delivered_qty / basis_qty) - allow_charge_amount, currency.decimal_places)
        ):
            if net_price_unit == 0 and delivered_qty == 0:
                quantity = 1
                price_unit = price_subtotal
            elif net_price_unit == 0:
                price_unit = price_subtotal / delivered_qty
            elif delivered_qty == 0:
                quantity = price_subtotal / price_unit

        return {
            # vals to be written on the document line
            'name': self._find_value(xpath_dict['name'], tree),
            'product_id': product.id,
            'product_uom_id': product_uom.id,
            'price_unit': price_unit,
            'quantity': quantity,
            'discount': discount,
            'tax_nodes': self._get_tax_nodes(tree),  # see `_retrieve_taxes`
            'charges': charges,  # see `_retrieve_line_charges`
            'price_subtotal': price_subtotal,
        }

    def _import_product(self, **product_vals):
        return self.env['product.product']._retrieve_product(**product_vals)

    def _retrieve_fixed_tax(self, company_id, fixed_tax_vals):
        """ Retrieve the fixed tax at import, iteratively search for a tax:
        1. not price_include matching the name and the amount
        2. not price_include matching the amount
        3. price_include matching the name and the amount
        4. price_include matching the amount
        """
        base_domain = [
            *self.env['account.journal']._check_company_domain(company_id),
            ('amount_type', '=', 'fixed'),
            ('amount', '=', fixed_tax_vals['amount']),
        ]
        for price_include in (False, True):
            for name in (fixed_tax_vals['reason'], False):
                domain = base_domain + [('price_include', '=', price_include)]
                if name:
                    domain.append(('name', '=', name))
                tax = self.env['account.tax'].search(domain, limit=1)
                if tax:
                    return tax
        return self.env['account.tax']

    def _retrieve_taxes(self, record, line_values, tax_type, tax_exigibility=None):
        """
        Retrieve the taxes on the document line at import.

        In a UBL/CII xml, the Odoo "price_include" concept does not exist. Hence, first look for a price_include=False,
        if it is unsuccessful, look for a price_include=True.
        """
        # Taxes: all amounts are tax excluded, so first try to fetch price_include=False taxes,
        # if no results, try to fetch the price_include=True taxes. If results, need to adapt the price_unit.
        logs = []
        taxes = []
        fpos_dest_ids = record.fiscal_position_id.tax_ids.mapped('tax_dest_id').ids if record.fiscal_position_id else []
        fpos_domain = [('id', 'in', fpos_dest_ids)] if fpos_dest_ids else []
        for tax_node in line_values.pop('tax_nodes'):
            amount = float(tax_node.text)
            domain = [
                *self.env['account.journal']._check_company_domain(record.company_id),
                ('amount_type', '=', 'percent'),
                ('type_tax_use', '=', tax_type),
                ('amount', '=', amount),
                ('country_id', '=', record.tax_country_id.id),
            ]
            tax = self.env['account.tax']
            if hasattr(record, '_get_specific_tax'):
                tax = record._get_specific_tax(line_values['name'], 'percent', amount, tax_type).filtered_domain(domain)[:1]
            if tax_exigibility is not None:
                if not tax:
                    tax = self.env['account.tax'].search(domain + fpos_domain + [('price_include', '=', False), ('tax_exigibility', '=', tax_exigibility)], limit=1)
                if not tax:
                    tax = self.env['account.tax'].search(domain + fpos_domain + [('price_include', '=', True), ('tax_exigibility', '=', tax_exigibility)], limit=1)
                if not tax:
                    tax = self.env['account.tax'].search(domain + [('price_include', '=', False), ('tax_exigibility', '=', tax_exigibility)], limit=1)
                if not tax:
                    tax = self.env['account.tax'].search(domain + [('price_include', '=', True), ('tax_exigibility', '=', tax_exigibility)], limit=1)
                if not tax:
                    logs.append(
                        _("Tax with matching exigibility could not be retrieved: '%(exigibility)s' for line '%(line)s'.",
                        exigibility=tax_exigibility,
                        line=line_values['name']),
                    )
            if not tax and fpos_domain:
                tax = self.env['account.tax'].search(domain + fpos_domain + [('price_include', '=', False)], limit=1)
            if not tax and fpos_domain:
                tax = self.env['account.tax'].search(domain + fpos_domain + [('price_include', '=', True)], limit=1)
            if not tax:
                tax = self.env['account.tax'].search(domain + [('price_include', '=', False)], limit=1)
            if not tax:
                tax = self.env['account.tax'].search(domain + [('price_include', '=', True)], limit=1)

            if not tax:
                logs.append(
                    _("Could not retrieve the tax: %(amount)s %% for line '%(line)s'.",
                    amount=amount,
                    line=line_values['name']),
                )
            else:
                taxes.append(tax.id)
                if tax.price_include:
                    line_values['price_unit'] *= (1 + tax.amount / 100)
        return taxes, logs

    def _retrieve_line_charges(self, record, line_values, taxes):
        """
        Handle the charges on the document line at import.

        For each charge on the line, it creates a new aml.
        Special case: if the ReasonCode == 'AEO', there is a high chance the xml was produced by Odoo and the
        corresponding line had a fixed tax, so it first tries to find a matching fixed tax to apply to the current aml.
        """
        charges_vals = []
        for charge in line_values.pop('charges'):
            if not charge['line_quantity']:
                continue

            if charge['reason_code'] == 'AEO':
                # a 1 eur fixed tax on a line with quantity=2 will yield an AllowanceCharge with amount = 2
                charge_copy = charge.copy()
                charge_copy['amount'] /= charge_copy['line_quantity']
                if tax := self._retrieve_fixed_tax(record.company_id, charge_copy):
                    taxes.append(tax.id)
                    if tax.price_include:
                        line_values['price_unit'] += tax.amount
                    continue

            price_subtotal_before = line_values['price_unit'] * charge['line_quantity'] * (1.0 - line_values['discount'] / 100.0)
            price_subtotal_after = price_subtotal_before + charge['amount']
            line_values['price_unit'] += charge['amount'] / charge['line_quantity']
            new_price_subtotal_before_discount = line_values['price_unit'] * charge['line_quantity']
            line_values['discount'] = (1 - (price_subtotal_after / new_price_subtotal_before_discount)) * 100.0
        return record._get_line_vals_list(charges_vals)

    def _get_document_allowance_charge_xpaths(self):
        # OVERRIDE
        pass

    def _get_invoice_line_xpaths(self, invoice_line, qty_factor):
        # OVERRIDE
        pass

    def _correct_invoice_tax_amount(self, tree, invoice):
        pass  # To be implemented by the format if needed

    def _import_init_collected_values(self, invoice, file_data):
        tree = file_data['xml_tree']
        company = invoice.company_id

        return {
            'invoice': invoice,
            'company': company,
            'odoo_document_type': 'sale' if invoice.journal_id.type == 'sale' else 'purchase',
            'tree': tree,
            'file_data': file_data,
            'logs': [],
            'to_write': {},
        }

    def _import_invoice_document_sign(self, collected_values):
        tree = collected_values['tree']
        suffix_invoice_type, document_sign = self._get_import_document_amount_sign(tree)
        collected_values['is_refund'] = suffix_invoice_type == 'refund'
        collected_values['file_document_sign'] = document_sign or 1

    def _import_invoice_update_move_type(self, collected_values):
        invoice = collected_values['invoice']
        odoo_document_type = collected_values['odoo_document_type']
        is_refund = collected_values['is_refund']
        logs = collected_values['logs']

        prefix = 'out' if odoo_document_type == 'sale' else 'in'
        suffix = 'refund' if is_refund else 'invoice'
        move_type = f'{prefix}_{suffix}'
        if invoice.move_type != move_type:
            invoice.move_type = move_type

            if is_refund:
                logs.append(self.env._("The invoice has been converted into a credit note and the quantities have been reverted."))

    def _import_retrieve_customer(self, collected_values):
        company = collected_values['company']
        customer_values = collected_values['customer_values']
        customer_values['account_numbers'] = collected_values.get('partner_bank_values', {}).get('account_numbers')
        self.env['res.partner']._import_retrieve_customer(
            search_plan=self._import_retrieve_customer_search_plan(collected_values),
            company=company,
            customer_values_list=[customer_values],
        )
        if partner := customer_values.get('customer'):
            collected_values['to_write']['partner_id'] = partner.id

    def _import_get_country(self, collected_values):
        customer_values = collected_values['customer_values']
        country_code = customer_values.get('country_code')
        if not country_code:
            return None

        if country_code == 'GB':
            # While the code is gb, the xml_id is uk
            country_code = 'UK'
        return self.env.ref(f'base.{country_code.lower()}', raise_if_not_found=False)

    def _import_retrieve_customer_search_plan(self, collected_values):
        ResPartner = self.env['res.partner']
        return [
            ResPartner._import_retrieve_customer_from_vat,
            ResPartner._import_retrieve_customer_from_eas_endpoint,
            ResPartner._import_retrieve_customer_from_email,
            ResPartner._import_retrieve_customer_from_phone,
            ResPartner._import_retrieve_customer_from_name,
        ]

    def _import_create_missing_customer(self, collected_values):
        customer_values = collected_values['customer_values']
        logs = collected_values['logs']
        customer = customer_values.get('customer')

        name = customer_values.get('name')
        vat = customer_values.get('vat')
        if not name or not vat:
            return

        vat_mismatch = False
        if customer:
            if not customer.vat:
                country = self._import_get_country(collected_values)
                if self.env['res.partner']._run_vat_test(vat, country, True):
                    customer.vat = vat
                return
            if customer.vat.replace(' ', '') == vat.replace(' ', '').replace('.', ''):
                return
            vat_mismatch = True

        partner_create_values = self._import_prepare_missing_customer_create_values(collected_values)
        customer = self.env['res.partner'].create(partner_create_values)
        if vat_mismatch:
            logs.append(_("Could not retrieve a partner corresponding to '%s' with the same VAT. A new partner was created.", name))
        else:
            logs.append(_("Could not retrieve a partner corresponding to '%s'. A new partner was created.", name))
        customer_values['customer'] = customer
        collected_values['to_write']['partner_id'] = customer.id

    def _import_prepare_missing_customer_create_values(self, collected_values):
        customer_values = collected_values['customer_values']
        partner_create_values = {
            'is_company': True,
        }
        for key in ('phone', 'name', 'email', 'street', 'street2', 'zip', 'city'):
            if value := customer_values.get(key):
                partner_create_values[key] = value

        if (peppol_eas := customer_values.get('peppol_eas')) and (
        peppol_endpoint := customer_values.get('peppol_endpoint')):
            partner_create_values['peppol_eas'] = peppol_eas
            partner_create_values['peppol_endpoint'] = peppol_endpoint

        country = self._import_get_country(collected_values)
        if country:
            partner_create_values['country_id'] = country.id
        if customer_values.get('vat') and self.env['res.partner']._run_vat_test(customer_values['vat'], country, True):
            partner_create_values['vat'] = customer_values['vat']
        return partner_create_values

    def _import_invoice_add_currency(self, collected_values):
        currency_values = collected_values['currency_values']
        logs = collected_values['logs']
        company = collected_values['company']
        currency = company.currency_id
        if currency_code := currency_values['currency_code']:
            currency = currency.with_context(active_test=False).search([('name', '=', currency_code)], limit=1)
            if currency:
                if not currency.active:
                    logs.append(self.env._("The currency '%s' is not active.", currency.name))
            else:
                logs.append(self.env._(
                    "Could not retrieve currency: %s. Did you enable the multicurrency option "
                    "and activate the currency?",
                    currency_code,
                ))

        currency_values['currency'] = currency
        if invoice_date := collected_values['to_write'].get('invoice_date'):
            currency_date = invoice_date
        else:
            currency_date = fields.Date.context_today(self)
        currency_values['rate'] = currency._get_conversion_rate(
            from_currency=company.currency_id,
            to_currency=currency,
            company=company,
            date=currency_date,
        )

        collected_values['to_write']['currency_id'] = currency.id

    def _import_retrieve_partner_bank(self, collected_values):
        company = collected_values['company']
        move_type = collected_values['invoice'].move_type
        if move_type in ('out_refund', 'in_invoice'):
            partner = collected_values.get('customer_values', {}).get('customer')
        elif move_type in ('out_invoice', 'in_refund'):
            partner = company.partner_id
        else:
            return
        if not partner:
            return

        partner_bank_values = collected_values['partner_bank_values']
        account_numbers = partner_bank_values['account_numbers']
        logs = collected_values['logs']
        partner_banks = self.env['res.partner.bank']
        for account_number in account_numbers:
            try:
                partner_banks += self.env['res.partner.bank']._find_or_create_bank_account(
                    account_number=account_number,
                    partner=partner,
                    company=company,
                )
            except UserError as e:
                logs.append(self.env._("The bank account couldn't be fetched: %s", str(e)))

        partner_bank_values['partner_banks'] = partner_banks
        if partner_banks:
            collected_values['to_write']['partner_bank_id'] = partner_banks[:1].id

    def _import_retrieve_products_search_plan(self, collected_values):
        ProductProduct = self.env['product.product']
        return [
            ProductProduct._import_retrieve_product_from_barcode,
            ProductProduct._import_retrieve_product_from_default_code,
            ProductProduct._import_retrieve_product_from_name,
            ProductProduct._import_retrieve_product_from_invoice_predictive,
        ]

    def _import_invoice_retrieve_products(self, collected_values):
        company = collected_values['company']
        lines_collected_values = collected_values['lines_collected_values']
        product_values_list = [
            line_collected_values['product_values']
            for line_collected_values in lines_collected_values
        ]

        self.env['product.product']._import_retrieve_product(
            search_plan=self._import_retrieve_products_search_plan(collected_values),
            company=company,
            product_values_list=product_values_list,
        )

        for line_collected_values in lines_collected_values:
            to_write = line_collected_values['to_write']
            if product := line_collected_values['product_values'].get('product'):
                to_write['product_id'] = product.id
            else:
                to_write['product_id'] = False

    def _import_invoice_retrieve_product_uoms(self, collected_values):
        lines_collected_values = collected_values['lines_collected_values']
        logs = collected_values['logs']
        cache = {}
        for line_collected_values in lines_collected_values:
            product_uom_values = line_collected_values['product_uom_values']
            uom_code = product_uom_values.get('uom_code')
            to_write = line_collected_values['to_write']

            to_write['product_uom_id'] = False
            if uom_code:
                matched_uom_xmlid = {v: k for k, v in UOM_TO_UNECE_CODE.items()}.get(uom_code)
                if matched_uom_xmlid:
                    if matched_uom_xmlid in cache:
                        uom = cache[matched_uom_xmlid]
                    else:
                        uom = cache[matched_uom_xmlid] = self.env.ref(matched_uom_xmlid, raise_if_not_found=False)
                    if uom:
                        product = line_collected_values['product_values'].get('product')
                        if product and uom.category_id != product.product_tmpl_id.uom_id.category_id:
                            logs.append(_(
                                "The Unit of Measure '%(uom)s' (from unit code '%(code)s', "
                                "category %(xml_category)s) was ignored on the line for product "
                                "'%(product)s' because it does not match the product's UoM "
                                "category (%(product_category)s). The UoM was left empty.",
                                uom=uom.name,
                                code=uom_code,
                                product=product.display_name,
                                xml_category=uom.category_id.name,
                                product_category=product.product_tmpl_id.uom_id.category_id.name,
                            ))
                            product_uom_values['force_empty'] = True
                            continue
                        to_write['product_uom_id'] = uom.id
                        product_uom_values['uom'] = uom

    def _import_invoice_retrieve_accounts(self, collected_values):
        if not self.module_installed('account_accountant'):
            # _predict_specific_account is defined in account_accountant
            return

        accounts_map = {}
        lines_collected_values = collected_values['lines_collected_values']
        for line_collected_values in lines_collected_values:
            account_values = line_collected_values['account_values']
            if predictive := account_values.get('invoice_predictive'):
                account_params = {'move': predictive['invoice'], 'name': predictive['name'], 'partner': predictive['partner']}
                account_key = tuple(account_params.values())
                if account_key not in accounts_map:
                    accounts_map[account_key] = self.env['account.move.line']._predict_specific_account(**account_params)
                account_id = accounts_map.get(account_key)
                if account_id:
                    account_values['account'] = self.env['account.account'].browse(account_id)

    def _import_retrieve_taxes_search_plan(self, collected_values):
        AccountTax = self.env['account.tax']
        return [
            AccountTax._import_retrieve_tax_from_invoice_predictive,
            AccountTax._import_retrieve_tax_from_price_include_exclude,
        ]

    def _import_invoice_retrieve_taxes(self, collected_values):
        company = collected_values['company']
        logs = collected_values['logs']
        lines_collected_values = collected_values['lines_collected_values']
        tax_values_list = list(collected_values.setdefault('taxes_values', {}))
        for line_collected_values in lines_collected_values:
            tax_values_list += line_collected_values['taxes_values']
            for charge in line_collected_values['charges']:
                if tax_values := charge.get('attempt_tax_values'):
                    tax_values_list.append(tax_values)
        for allowance_charge_value in collected_values['allowances'] + collected_values['charges']:
            if tax_values := allowance_charge_value.get('taxes_values'):
                tax_values_list.append(tax_values)

        if customer := collected_values.get('customer_values', {}).get('customer'):
            fiscal_position = self.env['account.move'].new({
                'company_id': collected_values['company'].id,
                'move_type': collected_values['invoice'].move_type,
                'partner_id': customer.id,
            }).fiscal_position_id
            for tax_values in tax_values_list:
                tax_values['fiscal_position'] = fiscal_position

        self.env['account.tax']._import_retrieve_tax(
            search_plan=self._import_retrieve_taxes_search_plan(collected_values),
            company=company,
            tax_values_list=tax_values_list,
        )

        # Taxes at the document line level.
        for line_collected_values in lines_collected_values:
            to_write = line_collected_values['to_write']
            tax_ids_commands = to_write['tax_ids'] = [Command.set([])]
            for tax_values in line_collected_values['taxes_values']:
                if tax := tax_values.get('tax'):
                    tax_ids_commands[0][2].append(tax.id)
                elif reason := tax_values.get('name'):
                    logs.append(self.env._(
                        "Could not retrieve the tax: %(tax_percentage)s %% for line '%(line)s'.",
                        tax_percentage=tax_values['amount'],
                        line=reason,
                    ))
                else:
                    logs.append(self.env._(
                        "Could not retrieve the tax: %s for the document level allowance/charge.",
                        tax_values['amount'],
                    ))

        # Taxes at the document level.
        for tax_values in collected_values.get('taxes_values', []):
            if tax_values.get('tax'):
                continue

            if reason := tax_values.get('name'):
                logs.append(self.env._(
                    "Could not retrieve the tax: %(tax_percentage)s %% for line '%(line)s'.",
                    tax_percentage=tax_values['amount'],
                    line=reason,
                ))
            else:
                logs.append(self.env._(
                    "Could not retrieve the tax: %s for the document level allowance/charge.",
                    tax_values['amount'],
                ))

    def _import_invoice_get_default_base_line_kwargs(self, collected_values):
        invoice = collected_values['invoice']

        taxes = self.env['account.tax']
        for tax_values in collected_values['taxes_values']:
            if tax := tax_values.get('tax'):
                taxes |= tax

        base_line_kwargs = {
            'sign': invoice.direction_sign,
            'is_refund': invoice.move_type in ('out_refund', 'in_refund'),
            'currency_id': collected_values['currency_values']['currency'],
            'rate': collected_values['currency_values']['rate'],
            'special_mode': 'total_excluded',
            '_create_values': {},
        }
        if partner := collected_values['customer_values'].get('partner'):
            base_line_kwargs['partner_id'] = partner

        return base_line_kwargs

    def _import_invoice_get_allowance_charge_line_kwargs(self, collected_values):
        allowance_charge = collected_values['allowance_charge']
        file_document_sign = collected_values['file_document_sign']
        tax_values = allowance_charge.get('taxes_values')
        multiplier_factor_numeric = allowance_charge['multiplier_factor_numeric']
        amount = allowance_charge['amount']
        reason = allowance_charge['reason']

        charge_indicator = allowance_charge['charge_indicator']
        if charge_indicator.lower() == 'true':
            charge_indicator_sign = 1
        else:
            charge_indicator_sign = -1

        if base_amount := allowance_charge.get('base_amount'):
            price_unit = base_amount * charge_indicator_sign * file_document_sign
            quantity = multiplier_factor_numeric / 100
        else:
            price_unit = amount * charge_indicator_sign * file_document_sign
            quantity = 1

        base_line_kwargs = {
            **self._import_invoice_get_default_base_line_kwargs(collected_values),
            'quantity': quantity,
            'price_unit': price_unit,
            'tax_ids': tax_values.get('tax') if tax_values else None,
        }
        base_line_kwargs['_create_values']['name'] = reason
        return base_line_kwargs

    def _import_invoice_line_get_product_base_line_kwargs(self, collected_values):
        to_write = collected_values['to_write']

        taxes = self.env['account.tax']
        for tax_values in collected_values['taxes_values']:
            if tax := tax_values.get('tax'):
                taxes |= tax

        base_line_kwargs = {
            **self._import_invoice_get_default_base_line_kwargs(collected_values),
            'quantity': to_write['quantity'],
            'price_unit': to_write['price_unit'],
            'discount': to_write['discount'],
            'tax_ids': taxes,
        }
        if product := collected_values['product_values'].get('product'):
            base_line_kwargs['product_id'] = product
        if uom := collected_values['product_uom_values'].get('uom'):
            base_line_kwargs['product_uom_id'] = uom
        elif collected_values['product_uom_values'].get('force_empty'):
            # Override the product_uom_id compute so the saved line keeps no UoM.
            base_line_kwargs['_create_values']['product_uom_id'] = False
        if account := collected_values['account_values'].get('account'):
            base_line_kwargs['account_id'] = account

        if name := collected_values.get('name'):
            base_line_kwargs['_create_values']['name'] = name
        if deferred_start_date := to_write.get('deferred_start_date'):
            base_line_kwargs['_create_values']['deferred_start_date'] = deferred_start_date
        if deferred_end_date := to_write.get('deferred_end_date'):
            base_line_kwargs['_create_values']['deferred_end_date'] = deferred_end_date
        base_line_kwargs['_create_values'] = {
            **base_line_kwargs['_create_values'],
            **self._import_invoice_line_add_optional_fields(collected_values),
        }
        return base_line_kwargs

    def _import_invoice_line_add_optional_fields(self, collected_values):
        return {}

    def _import_invoice_add_base_lines(self, collected_values):
        AccountTax = self.env['account.tax']
        base_lines = collected_values['base_lines'] = []
        company = collected_values['company']
        lines_collected_values = collected_values['lines_collected_values']

        # Allowances / charges lines at document level.
        for allowance_charge in collected_values['charges'] + collected_values['allowances']:
            base_line_kwargs = self._import_invoice_get_allowance_charge_line_kwargs({
                **collected_values,
                'allowance_charge': allowance_charge,
            })
            base_lines.append(AccountTax._prepare_base_line_for_taxes_computation(
                record=None,
                **base_line_kwargs,
            ))

        for line_collected_values in lines_collected_values:
            to_write = line_collected_values['to_write']

            # Extract charges matched with a fixed tax.
            for charge in line_collected_values['charges']:
                attempt_tax_values = charge.get('attempt_tax_values')
                if not attempt_tax_values or not attempt_tax_values.get('tax'):
                    continue

                # Suppose price_unit = 19, quantity = 10, discount = 10%
                # for a total of 190 (before discount) and 171 (after discount).
                # A charge of 25 is already accounted in 190 and we retrieve a fixed tax of 50 / 10 = 5.
                # We need now to extract 25 from 190 as:
                # price_subtotal_before = 171
                # price_subtotal_after = 171 - 50 = 121
                # price_unit = 19 - 5 = 14
                # new_price_subtotal_before_discount = 140
                # discount = (1 - (121 / 140)) * 100 = 13.5714286%
                # That way, 14 * 10 * (1 - 0.135714286) = 121.
                # The fix tax is giving an amount of 50.
                # 121 + 50 = the original 171 we had at the beginning!
                price_subtotal_before = to_write['price_unit'] * to_write['quantity'] * (1.0 - to_write['discount'] / 100.0)
                price_subtotal_after = price_subtotal_before - charge['amount']
                to_write['price_unit'] -= charge['amount'] / to_write['quantity']
                new_price_subtotal_before_discount = to_write['price_unit'] * to_write['quantity']
                to_write['discount'] = (1 - (price_subtotal_after / new_price_subtotal_before_discount)) * 100.0

            # Product line.
            base_line_kwargs = self._import_invoice_line_get_product_base_line_kwargs(line_collected_values)
            base_lines.append(AccountTax._prepare_base_line_for_taxes_computation(
                record=None,
                **base_line_kwargs,
            ))

        AccountTax._add_tax_details_in_base_lines(base_lines, company)
        AccountTax._round_base_lines_tax_details(base_lines, company)

        # Fix 'price_unit' if some price-included taxes are involved.
        for base_line in base_lines:
            for tax_data in base_line['tax_details']['taxes_data']:
                if tax_data['tax'].price_include:
                    base_line['price_unit'] += tax_data['raw_tax_amount_currency'] / (base_line['quantity'] if base_line['quantity'] else 1)

        # Remove lines having a zero amount.
        collected_values['base_lines'] = [
            base_line
            for base_line in collected_values['base_lines']
            if (not base_line['currency_id'].is_zero(base_line['tax_details']['total_included_currency']) or base_line.get('discount'))
        ]

    def _import_invoice_write_collected_values(self, collected_values):
        invoice = collected_values['invoice']
        base_lines = collected_values['base_lines']

        to_write = collected_values['to_write']
        invoice_line_ids = to_write['invoice_line_ids'] = []
        for base_line in base_lines:
            create_values = {
                **base_line['_create_values'],
                'quantity': base_line['quantity'],
                'price_unit': base_line['price_unit'],
                'discount': base_line['discount'],
                'tax_ids': [Command.set(base_line['tax_ids'].ids)]
            }
            # If the values were not initialized, we don't want to prevent compute by explicitly putting them empty
            if base_line['product_id']:
                create_values['product_id'] = base_line['product_id'].id
            if base_line['product_uom_id']:
                create_values['product_uom_id'] = base_line['product_uom_id'].id
            if base_line['account_id']:
                create_values['account_id'] = base_line['account_id'].id
            invoice_line_ids.append(Command.create(create_values))

        container = {'records': invoice}
        with (
            invoice._check_balanced(container),
            invoice._disable_discount_precision(),
            invoice._sync_dynamic_lines(container),
        ):
            invoice.write(to_write)

    def _import_invoice_fix_taxes_amounts(self, collected_values):
        AccountTax = self.env['account.tax']
        invoice = collected_values['invoice']
        tax_total_values = collected_values['tax_total_values']
        tolerance = 0.03
        total_tax_amount = sum(x['tax_amount_currency'] for x in tax_total_values.values())
        currency = collected_values['currency_values']['currency']

        tax_to_taxes = {}
        taxes_to_tax_amount_currency = {}
        is_complete = True
        for tax_key, global_tax_values in tax_total_values.items():
            taxes = self.env['account.tax']
            for related_tax_values in global_tax_values['related_taxes_values']:
                tax = related_tax_values.get('tax')
                if tax:
                    taxes |= tax
                else:
                    is_complete = False
                    break

            for tax in taxes:
                tax_to_taxes[tax] = taxes
            taxes_to_tax_amount_currency[taxes] = global_tax_values['tax_amount_currency']

        # If we are too far away from the total retrieved in the xml, don't fix anything: the error is elsewhere.
        collected_values['are_taxes_complete'] = is_complete
        if (
            not is_complete
            or currency.compare_amounts(abs(invoice.amount_tax - total_tax_amount) - tolerance, 0.0) > 0
        ):
            return

        # Fix the base lines.
        def grouping_function(_base_line, tax_data):
            return tax_data and tax_to_taxes.get(tax_data['tax'])

        base_lines, tax_lines = invoice._get_rounded_base_and_tax_lines()
        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for taxes, values in values_per_grouping_key.items():
            if not taxes:
                continue

            target_tax_amount_currency = taxes_to_tax_amount_currency[taxes]
            target_factors = [
                {
                    'factor': tax_data['raw_tax_amount_currency'],
                    'tax_data': tax_data,
                }
                for _base_line, taxes_data in values['base_line_x_taxes_data']
                for tax_data in taxes_data
            ]
            amounts_to_distribute = AccountTax._distribute_delta_amount_smoothly(
                precision_digits=currency.decimal_places,
                delta_amount=target_tax_amount_currency,
                target_factors=target_factors,
            )
            for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                tax_data = target_factor['tax_data']
                tax_data['tax_amount_currency'] = amount_to_distribute

        AccountTax._add_accounting_data_in_base_lines_tax_details(base_lines, invoice.company_id, include_caba_tags=invoice.always_tax_exigible)
        tax_results = AccountTax._prepare_tax_lines(base_lines, invoice.company_id, tax_lines=tax_lines)

        line_ids_commands = []
        for tax_line_vals, grouping_key, to_update in tax_results['tax_lines_to_update']:
            line_ids_commands.append(Command.update(tax_line_vals['record'].id, {
                'amount_currency': to_update['amount_currency'],
                'balance': to_update['balance'],
            }))

        container = {'records': invoice}
        with (
            invoice._check_balanced(container),
            invoice._disable_discount_precision(),
            invoice._sync_dynamic_lines(container),
        ):
            invoice.line_ids = line_ids_commands

    def _import_invoice_post_processing(self, collected_values):
        # During the import, fill 'ubl_cii_xml_file' to be retrieved later if necessary.
        invoice = collected_values['invoice']
        if invoice.is_purchase_document(include_receipts=True):
            collected_values['file_data']['attachment'].write({
                'res_field': 'ubl_cii_xml_file',
                'res_model': invoice._name,
                'res_id': invoice.id,
            })

        # Collect the embedded documents.
        invoice = collected_values['invoice']
        attachments = self._generate_pdt_attachment(invoice, collected_values['tree']) or self.env['ir.attachment']

        # Chatter.
        body = Markup("<strong>%s</strong>") % self.env._(
            "Format used to import the invoice: %s",
            self.env['ir.model']._get(self._name).name,
        )
        if logs := dict.fromkeys(collected_values['logs']):
            body += Markup("<ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % l for l in logs)
        invoice.with_context(no_new_invoice=True).message_post(body=body, attachment_ids=attachments.ids)

    def _generate_pdt_attachment(self, invoice, tree):
        """ ATTEMPTS to create a PDF attachment when the XML file doesn't provide one."""
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        disable_pdf_in_xml = str2bool(IrConfigParam.get_param("account_edi_ubl_cii.disable_pdf_in_xml", 'False'))
        additional_docs = self._import_attachments(invoice, tree)
        if (
            additional_docs or
            invoice.message_main_attachment_id or
            not invoice.is_purchase_document() or
            disable_pdf_in_xml
        ):
            return additional_docs
        try:
            invoices_by_odoo_xmlid = 'account_edi_ubl_cii.action_report_account_invoices_generated_by_odoo'
            if not self.env.ref(invoices_by_odoo_xmlid, raise_if_not_found=False):
                _logger.warning("Missing template while generating substitute PDF attachment for invoice %s", invoice.id)
                return additional_docs
            report_xmlid = invoices_by_odoo_xmlid

            pdf_raw, pdf_extension = self.env['ir.actions.report'] \
                        ._render_qweb_pdf(report_xmlid, res_ids=[invoice.id])

            if pdf_extension != 'pdf':
                return additional_docs

            if not self.env.ref('account_edi_ubl_cii.layout_invoices_generated_by_odoo', raise_if_not_found=False):
                # TODO: Remove in master
                # add a watermark to the generated pdf
                with io.BytesIO(pdf_raw) as pdf_stream:
                    new_pdf_stream = pdf.add_banner(pdf_stream, _('Generated by Odoo'), logo=False)
                    pdf_raw = new_pdf_stream.getvalue()
                    new_pdf_stream.close()

            invoice_name = invoice.display_name.replace(_('Draft'), '')
            pdf_filename = _('%(invoice_name)s - Generated by Odoo', invoice_name=invoice_name)

            attachment = self.env['ir.attachment'].create({
                'name': pdf_filename + '.pdf',
                'res_id': invoice.id,
                'res_model': 'account.move',
                'raw': pdf_raw,
                'type': 'binary',
                'mimetype': 'application/pdf',
            })
            invoice._message_set_main_attachment_id(attachment, force=True, filter_xml=False)
            return attachment
        except Exception:  # noqa: BLE001
            _logger.exception("Error while generating substitute PDF attachment for invoice %s", invoice.id)
        return additional_docs
