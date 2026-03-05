import re

from copy import deepcopy
from datetime import datetime
from collections import defaultdict
from markupsafe import Markup
from lxml import etree

from odoo import _, api, models
from odoo.addons.account.tools import dict_to_xml
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import float_compare, float_is_zero, float_repr
from odoo.tools.float_utils import float_round
from odoo.tools.misc import formatLang, html_escape
from odoo.tools.xml_utils import find_xml_value

from odoo.addons.base.models.res_country import EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES

# -------------------------------------------------------------------------
# MAPPING FOR TAX EXEMPTION
# -------------------------------------------------------------------------
TAX_EXEMPTION_MAPPING = {
    'VATEX-EU-79-C': 'Exempt based on article 79, point c of Council Directive 2006/112/EC',
    'VATEX-EU-132': 'Exempt based on article 132 of Council Directive 2006/112/EC',
    'VATEX-EU-132-1A': 'Exempt based on article 132, section 1 (a) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1B': 'Exempt based on article 132, section 1 (b) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1C': 'Exempt based on article 132, section 1 (c) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1D': 'Exempt based on article 132, section 1 (d) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1E': 'Exempt based on article 132, section 1 (e) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1F': 'Exempt based on article 132, section 1 (f) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1G': 'Exempt based on article 132, section 1 (g) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1H': 'Exempt based on article 132, section 1 (h) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1I': 'Exempt based on article 132, section 1 (i) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1J': 'Exempt based on article 132, section 1 (j) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1K': 'Exempt based on article 132, section 1 (k) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1L': 'Exempt based on article 132, section 1 (l) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1M': 'Exempt based on article 132, section 1 (m) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1N': 'Exempt based on article 132, section 1 (n) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1O': 'Exempt based on article 132, section 1 (o) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1P': 'Exempt based on article 132, section 1 (p) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1Q': 'Exempt based on article 132, section 1 (q) of Council Directive 2006/112/EC',
    'VATEX-EU-135-1': 'Exempt based on article 135, section 1 of Council Directive 2006/112/EC',
    'VATEX-EU-143': 'Exempt based on article 143 of Council Directive 2006/112/EC',
    'VATEX-EU-143-1A': 'Exempt based on article 143, section 1 (a) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1B': 'Exempt based on article 143, section 1 (b) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1C': 'Exempt based on article 143, section 1 (c) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1D': 'Exempt based on article 143, section 1 (d) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1E': 'Exempt based on article 143, section 1 (e) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1F': 'Exempt based on article 143, section 1 (f) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1FA': 'Exempt based on article 143, section 1 (fa) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1G': 'Exempt based on article 143, section 1 (g) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1H': 'Exempt based on article 143, section 1 (h) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1I': 'Exempt based on article 143, section 1 (i) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1J': 'Exempt based on article 143, section 1 (j) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1K': 'Exempt based on article 143, section 1 (k) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1L': 'Exempt based on article 143, section 1 (l) of Council Directive 2006/112/EC',
    'VATEX-EU-144': 'Exempt based on article 144 of Council Directive 2006/112/EC',
    'VATEX-EU-146-1E': 'Exempt based on article 146 section 1 (e) of Council Directive 2006/112/EC',
    'VATEX-EU-148': 'Exempt based on article 148 of Council Directive 2006/112/EC',
    'VATEX-EU-148-A': 'Exempt based on article 148, section (a) of Council Directive 2006/112/EC',
    'VATEX-EU-148-B': 'Exempt based on article 148, section (b) of Council Directive 2006/112/EC',
    'VATEX-EU-148-C': 'Exempt based on article 148, section (c) of Council Directive 2006/112/EC',
    'VATEX-EU-148-D': 'Exempt based on article 148, section (d) of Council Directive 2006/112/EC',
    'VATEX-EU-148-E': 'Exempt based on article 148, section (e) of Council Directive 2006/112/EC',
    'VATEX-EU-148-F': 'Exempt based on article 148, section (f) of Council Directive 2006/112/EC',
    'VATEX-EU-148-G': 'Exempt based on article 148, section (g) of Council Directive 2006/112/EC',
    'VATEX-EU-151': 'Exempt based on article 151 of Council Directive 2006/112/EC',
    'VATEX-EU-151-1A': 'Exempt based on article 151, section 1 (a) of Council Directive 2006/112/EC',
    'VATEX-EU-151-1AA': 'Exempt based on article 151, section 1 (aa) of Council Directive 2006/112/EC',
    'VATEX-EU-151-1B': 'Exempt based on article 151, section 1 (b) of Council Directive 2006/112/EC',
    'VATEX-EU-151-1C': 'Exempt based on article 151, section 1 (c) of Council Directive 2006/112/EC',
    'VATEX-EU-151-1D': 'Exempt based on article 151, section 1 (d) of Council Directive 2006/112/EC',
    'VATEX-EU-151-1E': 'Exempt based on article 151, section 1 (e) of Council Directive 2006/112/EC',
    'VATEX-EU-153': 'Exempt based on article 153 of Council Directive 2006/112/EC',
    'VATEX-EU-159': 'Exempt based on article 159 of Council Directive 2006/112/EC',
    'VATEX-EU-309': 'Exempt based on article 309 of Council Directive 2006/112/EC',
    'VATEX-EU-AE': 'Reverse charge',
    'VATEX-EU-D': 'Intra-Community acquisition from second hand means of transport',
    'VATEX-EU-F': 'Intra-Community acquisition of second hand goods',
    'VATEX-EU-G': 'Export outside the EU',
    'VATEX-EU-I': 'Intra-Community acquisition of works of art',
    'VATEX-EU-IC': 'Intra-Community supply',
    'VATEX-EU-O': 'Not subject to VAT',
    'VATEX-EU-J': 'Intra-Community acquisition of collectors items and antiques',
    'VATEX-FR-FRANCHISE': 'France domestic VAT franchise in base',
    'VATEX-FR-CNWVAT': 'France domestic Credit Notes without VAT, due to supplier forfeit of VAT for discount',
    'VATEX-FR-CGI261-1': 'Exempt based on 1 of article 261 of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261-2': 'Exempt based on 2 of article 261 of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261-3': 'Exempt based on 3 of article 261 of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261-4': 'Exempt based on 4 of article 261 of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261-5': 'Exempt based on 5 of article 261 of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261-7': 'Exempt based on 7 of article 261 of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261-8': 'Exempt based on 8 of article 261 of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261A': 'Exempt based on article 261 A of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261B': 'Exempt based on article 261 B of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261C-1': 'Exempt based on 1° of article 261 C of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261C-2': 'Exempt based on 2° of article 261 C of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261C-3': 'Exempt based on 3° of article 261 C of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261D-1': 'Exempt based on 1° of article 261 D of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261D-1BIS': 'Exempt based on 1°bis of article 261 D of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261D-2': 'Exempt based on 2° of article 261 D of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261D-3': 'Exempt based on 3° of article 261 D of the Code Général des Impôts (CGI ; General tax code) Exonération de TVA - Article 261 D-3° du Code Général des Impôts',
    'VATEX-FR-CGI261D-4': 'Exempt based on 4° of article 261 D of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261E-1': 'Exempt based on 1° of article 261 E of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI261E-2': 'Exempt based on 2° of article 261 E of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI277A': 'Exempt based on article 277 A of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI275': 'Exempt based on article 275 of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-298SEXDECIESA': 'Exempt based on article 298 sexdecies A of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-CGI295': 'Exempt based on article 295 of the Code Général des Impôts (CGI ; General tax code)',
    'VATEX-FR-AE': 'Exempt based on 2 of article 283 of the Code Général des Impôts (CGI ; General tax code)',
}

GST_COUNTRY_CODES = {
    'AU', 'NZ', 'IN', 'SG', 'MY', 'PK', 'BD', 'LK', 'NP', 'BT', 'PG', 'SA',
    'AG', 'BS', 'BB', 'DM', 'GD', 'JM', 'KN', 'LC', 'VC', 'TT',
}

# -------------------------------------------------------------------------
# SUPPORTED FILE TYPES FOR IMPORT
# -------------------------------------------------------------------------
SUPPORTED_FILE_TYPES = {
    'application/pdf': '.pdf',
    'application/vnd.oasis.opendocument.spreadsheet': '.ods',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'image/jpeg': '.jpeg',
    'image/png': '.png',
    'text/csv': '.csv',
}


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
    _name = 'account.edi.common'
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

    def _get_tax_category_code(self, customer, supplier, tax):
        """
        Predicts the tax category code for a tax applied to a given base line.
        If the tax has a defined category code, it is returned.
        Otherwise, a reasonable default is provided, though it may not always be accurate.

        Source: doc of Peppol (but the CEF norm is also used by factur-x, yet not detailed)
        https://docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice/cac-TaxTotal/cac-TaxSubtotal/cac-TaxCategory/cbc-TaxExemptionReasonCode/
        https://docs.peppol.eu/poacc/billing/3.0/codelist/vatex/
        https://docs.peppol.eu/poacc/billing/3.0/codelist/UNCL5305/
        """
        # add Norway, Iceland, Liechtenstein
        if not tax:
            return 'E'

        if tax.ubl_cii_tax_category_code:
            return tax.ubl_cii_tax_category_code

        if customer.country_id.code == 'ES' and customer.zip:
            if customer.zip[:2] in ('35', '38'):  # Canary
                # [BR-IG-10]-A VAT breakdown (BG-23) with VAT Category code (BT-118) "IGIC" shall not have a VAT
                # exemption reason code (BT-121) or VAT exemption reason text (BT-120).
                return 'L'
            if customer.zip[:2] in ('51', '52'):
                return 'M'  # Ceuta & Mellila

        if supplier.country_id == customer.country_id:
            if not tax or tax.amount == 0:
                # in theory, you should indicate the precise law article
                return 'E'
            elif tax.has_negative_factor:
                # Special case: Purchase reverse-charge taxes for self-billed invoices.
                # From the buyer's perspective, this is a standard tax with a non-zero percentage but
                # two tax repartition lines that cancel each other out.
                # But from the seller's perspective, this is a zero-percent tax (VAT liability is deferred
                # to the buyer).
                # For a self-billed invoice we, the buyer, create the invoice on behalf of the seller.
                # So in the XML we put the zero-percent tax with code 'AE' that the seller would have used.
                return 'AE'
            else:
                return 'S'  # standard VAT

        if supplier.country_id.code in EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES and supplier.vat:
            if tax.amount != 0 and not tax.has_negative_factor:
                # Special case: Purchase reverse-charge taxes for self-billed invoices.
                # See explanation above.
                # In the XML we put the zero-percent tax with code 'G' or 'K' that the buyer would have used.
                return 'S'
            if customer.country_id.code not in EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES:
                return 'G'
            if customer.country_id.code in EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES:
                return 'K'

        if tax.amount != 0:
            return 'S'
        else:
            return 'E'

    def _get_tax_exemption_reason(self, customer, supplier, tax):
        """ Returns the reason and code from the tax if available.
            If not, it falls back to the default tax exemption reason defined for the respective tax category code.

            Note: In Peppol, taxes should be grouped by tax category code but *not* by
            exemption reason, see https://docs.peppol.eu/poacc/billing/3.0/bis/#_calculation_of_vat
        """

        # shortcut if the exemption reason is set on the tax
        if tax and tax.ubl_cii_tax_exemption_reason_code and tax.ubl_cii_tax_exemption_reason:
            return {
                'tax_exemption_reason_code': tax.ubl_cii_tax_exemption_reason_code,
                'tax_exemption_reason': tax.ubl_cii_tax_exemption_reason,
            }

        if tax and (code := tax.ubl_cii_tax_exemption_reason_code):
            return {
                'tax_exemption_reason_code': code,
                'tax_exemption_reason': TAX_EXEMPTION_MAPPING.get(code, _("Exempt from tax") if tax.ubl_cii_requires_exemption_reason else None),
            }

        tax_category_code = self._get_tax_category_code(customer, supplier, tax)
        tax_exemption_reason = tax_exemption_reason_code = None

        if not tax or tax_category_code == 'E':
            tax_exemption_reason = _("Exempt from tax")
        elif tax_category_code == 'G':
            tax_exemption_reason = _('Export outside the EU')
            tax_exemption_reason_code = 'VATEX-EU-G'
        elif tax_category_code == 'K':
            tax_exemption_reason = _('Intra-Community supply')
            tax_exemption_reason_code = 'VATEX-EU-IC'

        return {
            'tax_exemption_reason': tax_exemption_reason,
            'tax_exemption_reason_code': tax_exemption_reason_code,
        }

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
            return custom_warning_message or _("The element %(record)s is required on %(field_list)s.", record=record, field_list=field_names)

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
                field_list=field_names,
            )

        display_field_names = record.fields_get(field_names)
        if len(field_names) == 1:
            display_field = f"'{display_field_names[field_names[0]]['string']}'"
            return _("The field %(field)s is required on %(record)s.", field=display_field, record=record.display_name)
        else:
            display_fields = [f"'{display_field_names[x]['string']}'" for x in display_field_names]
            return _("At least one of the following fields %(field_list)s is required on %(record)s.", field_list=display_fields, record=record.display_name)

    # -------------------------------------------------------------------------
    # COMMON CONSTRAINTS
    # -------------------------------------------------------------------------

    def _invoice_constraints_common(self, invoice):
        # check that there is a tax on each line
        for line in invoice.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_section', 'line_subsection', 'line_note') and x._check_edi_line_tax_required()):
            if not line.tax_ids:
                return {'tax_on_line': _("Each invoice line should have at least one tax.")}
        return {}

    @api.model
    def _flatten_multilevel_constraints(self, constraints: dict):
        """Flatten multilevel dict constraints

        see `_get_flatten_multilevel_constraints_config` for config values.

        Args:
            constraints:
                Arbitrary nested dict of simple constraints.

                Special keys:
                - ``_title``: title for this group (ignored in root)
                - ``_config``: config dict (only applicable in root)
                        Defaults to {
                            'residual_title': _("Other Errors:"),
                            'residual_key': 'other',
                            'indent_suffix': '',
                            'indent_suffix_on_root_titles': True,
                        }
                - Any key starting with ``_`` (except the above) is ignored

                Example:
                    {
                        '_title': "Custom title for residual errors",
                        'oth_err_1': "Some random error",
                        '_ubl_20': {
                            '_title': "UBL 2.0 Errors",
                            'ubl20_supplier_name_required': "The field 'name' is required...",
                        },
                        'other_err_2': "Something is wrong",
                        'important': {
                            '_title': "Important Errors",
                            'some_subtitle': {
                                '_title': "Some Subtitle",
                                'error_1': "Something is wrong with the thing",
                            },
                            'some_other_subtitle': {
                                '_title': "Some Other Subtitle",
                                'error_2': "Something is wrong with the other thing",
                            },
                        },
                    }

        Returns:
            dict: Flattened dict where keys are group identifiers and values are formatted strings
                  with titles and bullet-pointed messages, properly indented for nested groups.
        """
        def remove_non_flattable(dct: dict):
            to_remove = []
            for key, value in dct.items():
                if not value or not isinstance(value, (str, dict)):
                    to_remove.append(key)
                elif isinstance(value, dict):
                    remove_non_flattable(value)
                    if not value or all(k.startswith('_') for k in value):
                        to_remove.append(key)

            for key in to_remove:
                del dct[key]

        def flatten_dict(dct: dict, level=0) -> str | None:
            if '_title' not in dct:
                raise UserError(_("Missing '_title' for multi-level constraints."))

            title = dct.pop('_title')
            simple_strings = []
            children_strings = []

            for v in dct.values():
                if isinstance(v, str):
                    simple_strings.append(v)
                elif flattened_dict := flatten_dict(v, level + 1):
                    children_strings.append(flattened_dict)

            if not simple_strings and not children_strings:
                return None

            indent_suffix = config['indent_suffix']
            indent = '\t' * (level + 1) + indent_suffix
            if level == 0 and not config['indent_suffix_on_root_titles']:
                strings = [f'{'\t' * level}{title}']
            else:
                strings = [f'{'\t' * level}{indent_suffix}{title}']

            for string in simple_strings:
                strings.append(f'{indent}{string}')

            for string in children_strings:
                strings.append(string)

            return '\n'.join(strings)

        new_constraints = deepcopy(constraints)

        config = {
            'residual_title': _("Other Errors:"),
            'residual_key': 'other',
            'indent_suffix': '',
            'indent_suffix_on_root_titles': True,
        }
        custom_config = new_constraints.pop('_config', dict())
        config.update(custom_config)

        residuals = new_constraints.pop(config['residual_key'], dict())

        # Remove values we can not flatten
        remove_non_flattable(new_constraints)

        if not residuals and all(isinstance(value, str) for value in new_constraints.values()):
            # All values are strings
            return new_constraints

        # Aggregate residuals
        to_remove = []
        for key, value in new_constraints.items():
            if isinstance(value, str):
                residuals[key] = value
                to_remove.append(key)

        # Remove aggregated residuals from root dict
        for key in to_remove:
            del new_constraints[key]

        # Add residuals to new constraints
        if residuals:
            if not new_constraints:
                return residuals
            else:
                residuals['_title'] = config['residual_title']
                new_constraints[config['residual_key']] = residuals

        # Flatten children dicts
        return {k: flattened for k, v in new_constraints.items() if (flattened := flatten_dict(v))}

    # -------------------------------------------------------------------------
    # Import invoice
    # -------------------------------------------------------------------------

    def _import_invoice_ubl_cii(self, invoice, file_data, new=False):
        invoice.ensure_one()
        if invoice.invoice_line_ids:
            return invoice._reason_cannot_decode_has_invoice_lines()

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
        with invoice.with_context(disable_onchange_name_predictive=['all'])._get_edi_creation() as invoice:
            fill_invoice_logs = self._import_fill_invoice(invoice, tree, qty_factor)

        # For UBL, we should override the computed tax amount if it is less than 0.05 different of the one in the xml.
        # In order to support use case where the tax total is adapted for rounding purpose.
        # This has to be done after the first import in order to let Odoo compute the taxes before overriding if needed.
        with invoice._get_edi_creation() as invoice:
            self._correct_invoice_tax_amount(tree, invoice)

        # Set XML as ubl_cii_xml_file (XML used to import)
        if file_data['attachment'] and invoice.is_purchase_document(include_receipts=True):
            file_data['attachment'].write({
                'res_field': 'ubl_cii_xml_file',
                'res_model': invoice._name,
                'res_id': invoice.id,
            })

        source_attachment = file_data['attachment'] or self.env['ir.attachment']
        attachments = source_attachment + self._import_attachments(invoice, tree)

        self._log_import_invoice_ubl_cii(invoice, invoice_logs=fill_invoice_logs, attachments=attachments)

    def _add_logs_import_invoice_ubl_cii(self, invoice, invoice_logs=None):
        invoice.ensure_one()
        if invoice_logs is None:
            invoice_logs = []
        format_log = self.env._("Format: %s", self.env['ir.model']._get(self._name).name)
        return [format_log] + invoice_logs

    def _log_import_invoice_ubl_cii(self, invoice, title_logs=None, invoice_logs=None, attachments=None):
        invoice.ensure_one()
        body = Markup("<strong>%s</strong>") % (title_logs or self.env._("Invoice imported"))
        if invoice_logs := self._add_logs_import_invoice_ubl_cii(invoice, invoice_logs=invoice_logs):
            body += Markup("<ul>%s</ul>") % \
                    Markup().join(Markup("<li>%s</li>") % l for l in invoice_logs)
        invoice.message_post(body=body, attachment_ids=attachments.ids if attachments else None)

    def _import_attachments(self, invoice, tree):
        # Import the embedded documents in the xml if some are found
        attachments = self.env['ir.attachment']
        if invoice.message_main_attachment_id.mimetype == 'application/pdf':
            # Invoice look like it was already imported, don't import attachments again
            return attachments
        additional_docs = tree.findall('./{*}AdditionalDocumentReference')
        for document in additional_docs:
            attachment_name = document.find('{*}ID')
            attachment_data = document.find('{*}Attachment/{*}EmbeddedDocumentBinaryObject')
            if attachment_name is not None and attachment_data is not None:
                mimetype = attachment_data.attrib.get('mimeCode')
                if not (extension := SUPPORTED_FILE_TYPES.get(mimetype)):
                    continue
                # Strip internal newlines/spaces to prevent 'raw' field validation failure on create
                text = ''.join((attachment_data.text or '').split())
                # Normalize the name of the file : some e-fff emitters put the full path of the file
                # (Windows or Linux style) and/or the name of the xml instead of the pdf.
                # Get only the filename with the right extension.
                name = (attachment_name.text or 'invoice').split('\\')[-1].split('/')[-1].split('.')[0] + extension
                attachment = self.env['ir.attachment'].create({
                    'name': name,
                    'res_id': invoice.id,
                    'res_model': 'account.move',
                    'raw': text + '=' * (len(text) % 4),  # Fix incorrect padding
                    'type': 'binary',
                    'mimetype': mimetype,
                })
                # Upon receiving an email (containing an xml) with a configured alias to create invoice, the xml is
                # set as the main_attachment. To be rendered in the form view, the pdf should be the main_attachment.
                if invoice.message_main_attachment_id and \
                        invoice.message_main_attachment_id.name.endswith('.xml') and \
                        'pdf' not in invoice.message_main_attachment_id.mimetype and \
                        mimetype == 'application/pdf':
                    invoice._message_set_main_attachment_id(attachment, force=True, filter_xml=False)
                attachments |= attachment

        return attachments

    def _import_partner(self, company_id, name, phone, email, vat, *, routing_identifier=False, additional_identifiers=None, postal_address={}, **kwargs):
        """ Retrieve the partner, if no matching partner is found, create it (only if he has a vat and a name) """
        logs = []
        domain = False
        if routing_identifier:
            scheme, _sep, endpoint = routing_identifier.partition(':')
            domain = [('routing_scheme', '=', scheme), ('routing_endpoint', '=', endpoint)]
        partner = self.env['res.partner'] \
            .with_company(company_id) \
            ._retrieve_partner(name=name, phone=phone, email=email, vat=vat, additional_identifiers=additional_identifiers, domain=domain)
        country_code = postal_address.get('country_code')
        country = self.env['res.country'].search([('code', '=', country_code.upper())]) if country_code else self.env['res.country']
        state_code = postal_address.get('state_code')
        state = self.env['res.country.state'].search(
            [('country_id', '=', country.id), ('code', '=', state_code)],
            limit=1,
        ) if state_code and country else self.env['res.country.state']
        if not partner and name and vat:
            partner_vals = {'name': name, 'email': email, 'phone': phone, 'is_company': True}
            if routing_identifier:
                partner_vals['routing_identifier'] = routing_identifier
            if additional_identifiers:
                partner_vals['additional_identifiers'] = additional_identifiers
            partner = self.env['res.partner'].create(partner_vals)
            if vat:
                partner.vat, _country_code = self.env['res.partner']._run_vat_checks(country, vat, validation='setnull')
            logs.append(_("Could not retrieve a partner corresponding to '%s'. A new partner was created.", name))
        elif not partner and not logs:
            logs.append(_("Could not retrieve partner with details: Name: %(name)s, Vat: %(vat)s, Phone: %(phone)s, Email: %(email)s",
                  name=name, vat=vat, phone=phone, email=email))
        if not partner.country_id and not partner.street and not partner.street2 and not partner.city and not partner.zip and not partner.state_id:
            partner.write({
                'country_id': country.id,
                'street': postal_address.get('street'),
                'street2': postal_address.get('additional_street'),
                'city': postal_address.get('city'),
                'zip': postal_address.get('zip'),
                'state_id': state.id,
            })
        return partner, logs

    def _import_partner_bank(self, invoice, bank_details):
        partner = None
        if invoice.move_type in ('out_refund', 'in_invoice'):
            partner = invoice.partner_id
        elif invoice.move_type in ('out_invoice', 'in_refund'):
            partner = invoice.company_id.partner_id
        if not partner:
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

    def _import_lines(self, record, tree, xpath, document_type=False, tax_type=False, qty_factor=1):
        logs = []
        lines_values = []
        vehicle = self._import_vehicle(tree, 'move', document_type, record.company_id)
        for line_tree in tree.iterfind(xpath):
            line_values, line_logs = self.with_company(record.company_id)._retrieve_invoice_line_vals(record, line_tree, document_type, qty_factor)
            logs += line_logs
            if line_values is None:
                continue

            line_values['tax_ids'], tax_logs = self._retrieve_taxes(record, line_values, tax_type)
            logs += tax_logs
            if not line_values['product_uom_id']:
                line_values.pop('product_uom_id')  # if no uom, pop it so it's inferred from the product_id
            if self._need_vehicle_id(document_type):
                line_values['vehicle_id'] = vehicle or self._import_vehicle(line_tree, 'line', document_type, record.company_id)
            lines_values.append(line_values)
            self._retrieve_line_allowance_charges(record, line_values)
            if isinstance(record, self.env.registry['account.move']) and hasattr(self.env['account.move.line'], '_get_predicted_values'):
                for fname, value in self.env['account.move.line']._get_predicted_values(
                    line_values['name'],
                    move=record,
                    line_domain=[('tax_ids', '=', line_values['tax_ids'][0])] if len(line_values['tax_ids']) == 1 else [],
                ).items():
                    if fname not in line_values:
                        line_values[fname] = self.env['account.move.line']._fields[fname].convert_to_write(value, self.env['account.move.line'])
        return lines_values, logs

    def _import_rounding_amount(self, invoice, tree, xpath, document_type=False, qty_factor=1):
        """
        Add an invoice line representing the rounding amount given in the document.
        - The amount is assumed to be in document currency
        """
        logs = []
        lines_values = []

        currency = invoice.currency_id
        rounding_amount_currency = currency.round(qty_factor * float(tree.findtext(xpath) or 0))

        if invoice.currency_id.is_zero(rounding_amount_currency):
            return lines_values, logs

        inverse_rate = abs(invoice.amount_total_signed) / invoice.amount_total if invoice.amount_total else 0
        rounding_amount = invoice.company_id.currency_id.round(rounding_amount_currency * inverse_rate)

        lines_values.append({
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

        return lines_values, logs

    def _retrieve_invoice_line_vals(self, record, tree, document_type=False, qty_factor=1):
        # Start and End date (enterprise fields)
        logs = []
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

        line_vals, line_logs = self._retrieve_line_vals(record, tree, document_type, qty_factor)
        logs += line_logs
        if not line_vals.get('price_subtotal'):
            return None, logs

        return {
            **line_vals,
            **deferred_values,
        }, logs

    @api.model
    def _retrieve_rebate_val(self, record, tree, xpath_dict, quantity, net_price_unit):
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
    def _retrieve_allowance_charge_vals(self, company_id, tree, xpath_dict, quantity, net_price_unit):
        """Retrieves AllowanceCharge nodes of an invoice line and build dictionaries
        with the relevant details for each allowance/charge.
        """

        def _is_allowance_charge_node_valid(charge_indicator, reason_code, reason, amount):
            """
            Check mandatory structural requirements for an AllowanceCharge node.
            If any of these are failing, the node is considered erroneous and
            will be ignored.

            References:
                - PEPPOL-EN16931-R043 for charge_indicator
                - BR-41, BR-43 for reason/reason_code
                - BR-42, BR-44 for amount
            """
            has_valid_charge_indicator = charge_indicator in ('true', 'false')
            has_reason = bool(reason_code or reason)
            has_amount = bool(amount)

            return has_reason and has_valid_charge_indicator and has_amount

        logs = []
        allowance_charge_vals = []
        discount_amount = 0
        has_invalid_nodes = False
        for allowance_charge_node in tree.iterfind(xpath_dict['allowance_charge']):
            charge_indicator = allowance_charge_node.findtext(xpath_dict['allowance_charge_indicator'], default='').lower()
            amount = allowance_charge_node.findtext(xpath_dict['allowance_charge_amount'])
            percent = allowance_charge_node.findtext(xpath_dict['allowance_charge_percent'])
            reason_code = allowance_charge_node.findtext(xpath_dict['allowance_charge_reason_code'], default='')
            reason = allowance_charge_node.findtext(xpath_dict['allowance_charge_reason'], default='')

            if _is_allowance_charge_node_valid(charge_indicator, reason_code, reason, amount):
                # Handle Allowance/Charge Taxes: when exporting from Odoo, we use the allowance_charge node
                vals = {
                    'charge_indicator': charge_indicator,
                    'amount': float(amount),
                    'line_quantity': quantity,
                    'net_price_unit': net_price_unit or 0,
                    'reason_code': reason_code,
                    'reason': reason,
                    'percent': float(percent) if percent else None
                }

                # We check if there is a tax present with line_discount configuration,
                # if not then we consider it as a line_discount.
                # To be kept in sync with reason_code and reason defined in `_ubl_get_line_allowance_charge_discount_node`
                if (
                    (reason_code in ('95', 'ADK') or reason == 'Discount')
                    and not self._retrieve_allowance_charge_tax(company_id, vals)
                ):
                    discount_amount += float(amount)
                else:
                    allowance_charge_vals.append(vals)
            else:
                has_invalid_nodes = True

        if has_invalid_nodes:
            logs.append(self.env._("Some line-level allowance/charge nodes were invalid and were skipped during import."))
        return discount_amount, allowance_charge_vals, logs

    def _retrieve_line_vals(self, record, tree, document_type=False, qty_factor=1):
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
        product = self._import_product(record.partner_id, **product_vals)
        product_uom = self.env['uom.uom']
        quantity_node = tree.find(xpath_dict['delivered_qty'])
        if quantity_node is not None:
            delivered_qty = float(quantity_node.text)
            if unece_code := quantity_node.attrib.get('unitCode'):
                product_uom = self.env['uom.uom']._get_uom_from_unece_code(unece_code)
        if product and product_uom and not product_uom._has_common_reference(product.product_tmpl_id.uom_id):
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
        rebate = self._retrieve_rebate_val(record.company_id, tree, xpath_dict, quantity, net_price_unit)

        # Charges are collected (they are used to create new lines), Allowances are transformed into discounts
        discount_amount, allowance_charge_vals, logs = self._retrieve_allowance_charge_vals(record.company_id, tree, xpath_dict, quantity, net_price_unit)

        # price_unit
        charge_amount = sum(d['amount'] for d in allowance_charge_vals if d['charge_indicator'] == 'true')
        allowance_amount = sum(d['amount'] for d in allowance_charge_vals if d['charge_indicator'] == 'false')
        allow_charge_amount = discount_amount + allowance_amount - charge_amount
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
            inferred_discount = 100 * (1 - (price_subtotal + allowance_amount - charge_amount) / currency.round(delivered_qty * price_unit))
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
            'allowance_charge_vals': allowance_charge_vals,  # see `_retrieve_line_allowance_charges`
            'price_subtotal': price_subtotal,
        }, logs

    def _import_product(self, partner, **product_vals):
        return self.env['product.product']._retrieve_product(**product_vals)

    def _import_vehicle(self, tree, tree_type, document_type, company):
        """
        For xmls where the VIN is located somewhere in a tag under Invoice or InvoiceLine
        :param tree: etree object
        :param tree_type: 'line' if the tree root element is <InvoiceLine> or 'move' if it's <Invoice>
        """
        if not self._need_vehicle_id(document_type):
            return False
        default_parent_node_path = './{*}Item/{*}AdditionalItemProperty'
        default_value_path = './{*}Value'
        default_linked_field = 'vin_sn'

        def default_condition(parent_node, node, value):
            return parent_node.findtext('./{*}Name') == value
        paths = [
            # {
            #   'path_type': 'line' or 'move'
            #   'parent_node_path': 'path to the parent node',
            #   'condition': lambda parent_node, node, value: 'where parent_node = parent node, node = node containing VIN Number, value = identifier',
            #   'value_path': 'path to the node where the information is to be found',
            #   'identifier': 'to be used in condition to perform a check, inner text of a node allowing to identify the node to read',
            #   'linked_field': the field to search in DB (vin_sn, license_plate),
            #   'pattern': if the value to search is not in a field specific to it (with other words like in a description)
            # }
            {'path_type': 'line', 'identifier': 'SerialNumber'},  # VIN in AdditionalItemProperty/Value with AdditionalItemProperty/Name == 'SerialNumber'
            {'path_type': 'line', 'identifier': 'VIN'},  # VIN in AdditionalItemProperty/Value with AdditionalItemProperty/Name == 'VIN'
            {'path_type': 'line', 'identifier': 'PlateNumber', 'linked_field': 'license_plate'},  # LICENSE PLATE in AdditionalItemProperty/Value with AdditionalItemProperty/Name == 'PlateNumber'
            {'path_type': 'line', 'identifier': 'LCPL-NO', 'linked_field': 'license_plate'},  # LICENSE PLATE in AdditionalItemProperty/Value with AdditionalItemProperty/Name == 'LCPL-NO'
            {
                # VIN in Item/Description
                'path_type': 'line',
                'parent_node_path': './{*}Item',
                'condition': lambda parent_node, node, value: True,
                'value_path': './{*}Description',
                'pattern': r'[A-Za-z0-9]{17}',
            },
            {
                # LICENSE PLATE in Item/Description
                'path_type': 'line',
                'parent_node_path': './{*}Item',
                'condition': lambda parent_node, node, value: True,
                'value_path': './{*}Description',
                'linked_field': 'license_plate',
                'pattern': r'\d-[A-Za-z]{3}-\d{3}',  # BE license plate format
            },
            {
                # VIN in AdditionalDocumentReference/ID with schemeID == 'AKG' (1 vin for the whole invoice)
                'path_type': 'move',
                'parent_node_path': './{*}AdditionalDocumentReference',
                'condition': lambda parent_node, node, value: node.get('schemeID') == 'AKG',
                'value_path': './{*}ID',
            },
            {
                # LICENSE PLATE in AdditionalDocumentReference/ID with schemeID == 'ABZ' (1 license plate for the whole invoice)
                'path_type': 'move',
                'parent_node_path': './{*}AdditionalDocumentReference',
                'condition': lambda parent_node, node, value: node.get('schemeID') == 'ABZ',
                'value_path': './{*}ID',
                'linked_field': 'license_plate',
            },
        ]

        results = defaultdict(set)  # {field (vin_sn|license_plate): {'AZERTYUIOP', 'POIUYTREZA'}}
        for path in [p for p in paths if p['path_type'] == tree_type]:
            parent_nodes = tree.findall(path.get('parent_node_path', default_parent_node_path))
            for parent_node in parent_nodes:
                value_node = parent_node.find(path.get('value_path', default_value_path))
                if value_node is None or not path.get('condition', default_condition)(parent_node, value_node, path.get('identifier', '')):
                    continue
                value = value_node.text
                if value is None:
                    continue
                if path.get('pattern'):
                    # we need to find the car identifier in the node
                    if candidates := re.findall(path['pattern'], value or ''):
                        results[path.get('linked_field', default_linked_field)].update(candidates)
                else:
                    # the car identifier is the full text of the node
                    results[path.get('linked_field', default_linked_field)].add(value)

        if len(results) == 0 or any(len(vals) != 1 for vals in results.values()):
            return False

        vehicles = self.env.get('fleet.vehicle').search([
            ('company_id', '=', company.id),
        ] + Domain.OR([
            [(field, 'in', vals)] for field, vals in results.items()
        ]), limit=2)
        if len(vehicles) == 1:
            return vehicles.id
        return False

    def _need_vehicle_id(self, document_type):
        return document_type == 'in_invoice' and 'fleet.vehicle' in self.env

    def _retrieve_allowance_charge_tax(self, company_id, allowance_charge_tax_vals):
        """Retrieve the Allowance/Charge tax at import using following approach:

        Matching Algorithm:
        1. Start by attempting a match using both `reason_code` and `reason` when `reason_code` is available.
        2. If no match is found, retry using only `reason_code`.
        3. If `reason_code` is not available, perform a strict match using `reason`.
        4. For each of the above attempts:
           a. First, try with `price_include=False`.
           b. If unsuccessful, retry with `price_include=True`.
        """

        # Normalize fixed tax amount by line quantity.
        # Example: fixed tax = 1, qty = 2 → AllowanceCharge amount = 2 → per-unit = 1
        qty = allowance_charge_tax_vals.get('line_quantity') or 1
        # using abs(qty) here as we handle the sign later with charge_indicator, quantity and net_price_unit.
        amount = (
            allowance_charge_tax_vals['percent']
            if allowance_charge_tax_vals.get('percent')
            else (allowance_charge_tax_vals['amount'] / abs(qty))
        )

        # if quantity is negative or net_price_unit is negative,
        # the tax amount would be negative for charges and positive for allowances
        # see - `test_invoice_with_fixed_tax_on_negative_line` for reference
        line_sign = ((qty < 0) ^ (allowance_charge_tax_vals.get('net_price_unit', 0) < 0)) == 0 and 1 or -1
        charge_sign = 1 if allowance_charge_tax_vals['charge_indicator'] == 'true' else -1

        reason_code = allowance_charge_tax_vals.get('reason_code')
        reason = allowance_charge_tax_vals.get('reason')
        is_charge = allowance_charge_tax_vals['charge_indicator'] == 'true'
        type_str = 'charge' if is_charge else 'allowance'
        base_domain = Domain([
            *self.env['account.journal']._check_company_domain(company_id),
            ('ubl_cii_type', '=', 'allowance_charge'),
            ('ubl_cii_is_charge', '=', is_charge),
            ('amount', '=', amount * line_sign * charge_sign),
            ('amount_type', '=', 'percent' if allowance_charge_tax_vals.get('percent') else 'fixed'),
            ('include_base_amount', '=', True),
        ])
        domains = []

        if reason_code:
            if reason:
                domains.append(base_domain + Domain([
                    (f'ubl_cii_{type_str}_reason_code', '=', reason_code),
                    ('ubl_cii_allowance_charge_reason', '=', reason),
                ]))
            domains.append(base_domain + Domain([
                (f'ubl_cii_{type_str}_reason_code', '=', reason_code),
            ]))
        else:
            # At least one of `reason` or `reason_code` is always set (see `_retrieve_allowance_charge_vals`).
            domains.append(base_domain + Domain([
                ('ubl_cii_allowance_charge_reason', '=', reason),
            ]))

        for domain in domains:
            for price_include in (False, True):
                tax_domain = domain + Domain([('price_include', '=', price_include)])
                tax = self.env['account.tax'].search(tax_domain, limit=1)
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
        fpos_domain = [('fiscal_position_ids', '=', record.fiscal_position_id.id)]
        if record.fiscal_position_id.is_domestic:
            fpos_domain = ['|', ('fiscal_position_ids', '=', False)] + fpos_domain
        for tax_node in line_values.pop('tax_nodes'):
            amount = float(tax_node.text)
            domain = [
                *self.env['account.journal']._check_company_domain(record.company_id),
                ('amount_type', '=', 'percent'),
                ('type_tax_use', '=', tax_type),
                ('amount', '=', amount),
                ('ubl_cii_type', '=', 'tax'),  # to avoid matching allowance_charge taxes when looking for line taxes
            ]
            tax = self.env['account.tax']
            if hasattr(record, '_get_specific_tax'):
                tax = record._get_specific_tax(line_values['name'], domain).filtered_domain(domain)[:1]
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
            if not tax:
                tax = self.env['account.tax'].search(domain + fpos_domain + [('price_include', '=', False)], limit=1)
            if not tax:
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

    def _retrieve_line_allowance_charges(self, record, line_values):
        """
        Handle the allowance/charges on the invoice line at import.

        If an allowance/charge matches a configured tax, the tax is applied to the line.
        Otherwise, price_subtotal is adjusted to represent the allowance/charge.
        """
        tax_map = [
            (val, self._retrieve_allowance_charge_tax(record.company_id, val))
            for val in line_values.pop('allowance_charge_vals')
        ]

        # Apply taxes only if all are found.
        # Otherwise adjust price_subtotal to avoid wrong tax base interactions.
        if tax_map and all(tax for _, tax in tax_map):
            for val, tax in tax_map:
                line_values['tax_ids'].append(tax.id)
                if tax.price_include:
                    line_values['price_unit'] += tax.amount
        else:
            for val, _ in tax_map:
                qty = val.get('line_quantity', 1)
                charge_sign = 1 if val['charge_indicator'] == 'true' else -1
                price_subtotal_before = line_values['price_unit'] * qty * (1.0 - line_values['discount'] / 100.0)
                price_subtotal_after = price_subtotal_before + (val['amount'] * charge_sign)
                line_values['price_unit'] += ((val['amount'] / qty) * charge_sign)
                new_price_subtotal_before_discount = line_values['price_unit'] * qty
                line_values['discount'] = (1 - (price_subtotal_after / new_price_subtotal_before_discount)) * 100.0

    def _get_document_allowance_charge_xpaths(self):
        # OVERRIDE
        pass

    def _get_invoice_line_xpaths(self, invoice_line, qty_factor):
        # OVERRIDE
        pass

    def _correct_invoice_tax_amount(self, tree, invoice):
        pass  # To be implemented by the format if needed
