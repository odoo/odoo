from markupsafe import Markup

from odoo import _, api, models
from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, float_repr
from odoo.tools.float_utils import float_round
from odoo.tools.misc import clean_context, formatLang, html_escape
from odoo.tools.xml_utils import find_xml_value
from datetime import datetime

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
    'uom.product_uom_qt': 'QT',
    'uom.product_uom_gal': 'GLL',
    'uom.product_uom_cubic_inch': 'INQ',
    'uom.product_uom_cubic_foot': 'FTQ',
    'uom.product_uom_square_meter': 'MTK',
    'uom.product_uom_square_foot': 'FTK',
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
    'DE': {'9930': 'vat'},
    'DK': {'0184': 'vat', '0198': 'vat'},
    'EE': {'9931': 'vat'},
    'ES': {'9920': 'vat'},
    'FI': {'0216': None, '0213': 'vat'},
    'FR': {'0009': 'company_registry', '9957': 'vat', '0002': None},
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
    'NL': {'0106': None, '0190': None},
    'NO': {'0192': 'l10n_no_bronnoysund_number'},
    'NZ': {'0088': 'company_registry'},
    'PL': {'9945': 'vat'},
    'PT': {'9946': 'vat'},
    'RO': {'9947': 'vat'},
    'RS': {'9948': 'vat'},
    'SE': {'0007': 'company_registry', '9955': 'vat'},
    'SI': {'9949': 'vat'},
    'SK': {'9950': 'vat'},
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
        self_float = float(self)
        min_dp_int = int(self.min_dp)
        if self.max_dp is None:
            return float_repr(self_float, min_dp_int)
        else:
            # Format the float to between self.min_dp and self.max_dp decimal places.
            # We start by formatting to self.max_dp, and then remove trailing zeros,
            # but always keep at least self.min_dp decimal places.
            max_dp_int = int(self.max_dp)
            amount_max_dp = float_repr(self_float, max_dp_int)
            num_trailing_zeros = len(amount_max_dp) - len(amount_max_dp.rstrip('0'))
            return float_repr(self_float, max(max_dp_int - num_trailing_zeros, min_dp_int))

    def __repr__(self):
        if not isinstance(self.min_dp, int) or (self.max_dp is not None and not isinstance(self.max_dp, int)):
            return "<FloatFmt()>"
        self_float = float(self)
        min_dp_int = int(self.min_dp)
        if self.max_dp is None:
            return f"FloatFmt({self_float!r}, {min_dp_int!r})"
        else:
            max_dp_int = int(self.max_dp)
            return f"FloatFmt({self_float!r}, {min_dp_int!r}, {max_dp_int!r})"


class AccountEdiCommon(models.AbstractModel):
    _name = 'account.edi.common'
    _description = "Common functions for EDI documents: generate the data, the constraints, etc"

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

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
        list of codes: https://docs.peppol.eu/poacc/billing/3.0/codelist/UNECERec20/
        or https://unece.org/fileadmin/DAM/cefact/recommendations/bkup_htm/add2c.htm (sorted by letter)
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

        if tax and (code := tax.ubl_cii_tax_exemption_reason_code):
            return {
                'tax_exemption_reason_code': code,
                'tax_exemption_reason': TAX_EXEMPTION_MAPPING.get(code, _("Exempt from tax") if tax.ubl_cii_requires_exemption_reason else None),
            }

        tax_category_code = self._get_tax_category_code(customer, supplier, tax)
        tax_exemption_reason = tax_exemption_reason_code = None

        if not tax:
            tax_exemption_reason = _("Exempt from tax")
        elif tax_category_code == 'E':
            tax_exemption_reason = _('Articles 226 items 11 to 15 Directive 2006/112/EN')
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
        with invoice._get_edi_creation() as invoice:
            fill_invoice_logs = self._import_fill_invoice(invoice, tree, qty_factor)

        # For UBL, we should override the computed tax amount if it is less than 0.05 different of the one in the xml.
        # In order to support use case where the tax total is adapted for rounding purpose.
        # This has to be done after the first import in order to let Odoo compute the taxes before overriding if needed.
        with invoice._get_edi_creation() as invoice:
            self._correct_invoice_tax_amount(tree, invoice)

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
        additional_docs = tree.findall('./{*}AdditionalDocumentReference')
        for document in additional_docs:
            attachment_name = document.find('{*}ID')
            attachment_data = document.find('{*}Attachment/{*}EmbeddedDocumentBinaryObject')
            if attachment_name is not None and attachment_data is not None:
                mimetype = attachment_data.attrib.get('mimeCode')
                if not (extension := SUPPORTED_FILE_TYPES.get(mimetype)):
                    continue
                text = attachment_data.text
                # Normalize the name of the file : some e-fff emitters put the full path of the file
                # (Windows or Linux style) and/or the name of the xml instead of the pdf.
                # Get only the filename with the right extension.
                name = (attachment_name.text or 'invoice').split('\\')[-1].split('/')[-1].split('.')[0] + extension
                attachment = self.env['ir.attachment'].create({
                    'name': name,
                    'res_id': invoice.id,
                    'res_model': 'account.move',
                    'datas': text + '=' * (len(text) % 3),  # Fix incorrect padding
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

    def _import_partner(self, company_id, name, phone, email, vat, *, peppol_eas=False, peppol_endpoint=False, postal_address={}, **kwargs):
        """ Retrieve the partner, if no matching partner is found, create it (only if he has a vat and a name) """
        logs = []
        if peppol_eas and peppol_endpoint:
            domain = [('peppol_eas', '=', peppol_eas), ('peppol_endpoint', '=', peppol_endpoint)]
        else:
            domain = False
        partner = self.env['res.partner'] \
            .with_company(company_id) \
            ._retrieve_partner(name=name, phone=phone, email=email, vat=vat, domain=domain)
        country_code = postal_address.get('country_code')
        country = self.env['res.country'].search([('code', '=', country_code.upper())]) if country_code else self.env['res.country']
        state_code = postal_address.get('state_code')
        state = self.env['res.country.state'].search(
            [('country_id', '=', country.id), ('code', '=', state_code)],
            limit=1,
        ) if state_code and country else self.env['res.country.state']
        if not partner and name and vat:
            partner_vals = {'name': name, 'email': email, 'phone': phone, 'is_company': True}
            if peppol_eas and peppol_endpoint:
                partner_vals.update({'peppol_eas': peppol_eas, 'peppol_endpoint': peppol_endpoint})
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
        bank_details = list(set(map(sanitize_account_number, bank_details)))
        body = _("The following bank account numbers got retrieved during the import : %s", ", ".join(bank_details))
        invoice.with_context(no_new_invoice=True).message_post(body=body)

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
        for line_tree in tree.iterfind(xpath):
            line_values = self.with_company(record.company_id)._retrieve_invoice_line_vals(line_tree, document_type, qty_factor)
            if line_values is None:
                continue

            line_values['tax_ids'], tax_logs = self._retrieve_taxes(record, line_values, tax_type)
            logs += tax_logs
            if not line_values['product_uom_id']:
                line_values.pop('product_uom_id')  # if no uom, pop it so it's inferred from the product_id
            lines_values.append(line_values)
            lines_values += self._retrieve_line_charges(record, line_values, line_values['tax_ids'])
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
        if line_vals is None:
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
            charge_indicator = allowance_charge_node.findtext(xpath_dict['allowance_charge_indicator'])
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
                uom_infered_xmlid = [
                    odoo_xmlid for odoo_xmlid, uom_unece in UOM_TO_UNECE_CODE.items() if uom_unece == uom_xml
                ]
                if uom_infered_xmlid:
                    product_uom = self.env.ref(uom_infered_xmlid[0], raise_if_not_found=False) or self.env['uom.uom']
        if product and product_uom and not product_uom._has_common_reference(product.product_tmpl_id.uom_id):
            # uom incompatibility
            product_uom = self.env['uom.uom']

        # line_net_subtotal (mandatory)
        price_subtotal = None
        line_total_amount_node = tree.find(xpath_dict['line_total_amount'])
        if line_total_amount_node is None or line_total_amount_node.text is None or not line_total_amount_node.text.strip():
            return None
        price_subtotal = float(line_total_amount_node.text)
        if price_subtotal == 0:
            return None

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
            raise UserError(_("No gross price, net price nor line subtotal amount found for line in xml"))

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
        if net_price_unit is not None and float_compare(price_subtotal, net_price_unit * (delivered_qty / basis_qty) - allow_charge_amount, currency.decimal_places):
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

    def _retrieve_taxes(self, record, line_values, tax_type, tax_exigibility=False):
        """
        Retrieve the taxes on the document line at import.

        In a UBL/CII xml, the Odoo "price_include" concept does not exist. Hence, first look for a price_include=False,
        if it is unsuccessful, look for a price_include=True.
        """
        # Taxes: all amounts are tax excluded, so first try to fetch price_include=False taxes,
        # if no results, try to fetch the price_include=True taxes. If results, need to adapt the price_unit.
        logs = []
        taxes = []
        for tax_node in line_values.pop('tax_nodes'):
            amount = float(tax_node.text)
            domain = [
                *self.env['account.journal']._check_company_domain(record.company_id),
                ('amount_type', '=', 'percent'),
                ('type_tax_use', '=', tax_type),
                ('amount', '=', amount),
            ]
            tax = self.env['account.tax']
            if hasattr(record, '_get_specific_tax'):
                tax = record._get_specific_tax(line_values['name'], 'percent', amount, tax_type)
            if tax_exigibility:
                if not tax and tax_exigibility:
                    tax = self.env['account.tax'].search(domain + [('price_include', '=', False), ('tax_exigibility', '=', tax_exigibility)], limit=1)
                if not tax and tax_exigibility:
                    tax = self.env['account.tax'].search(domain + [('price_include', '=', True), ('tax_exigibility', '=', tax_exigibility)], limit=1)
                if not tax:
                    logs.append(
                        _("Tax with matching exigibility could not be retrieved: '%(exigibility)s' for line '%(line)s'.",
                        exigibility=tax_exigibility,
                        line=line_values['name']),
                    )
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
            if charge['reason_code'] == 'AEO':
                # a 1 eur fixed tax on a line with quantity=2 will yield an AllowanceCharge with amount = 2
                charge_copy = charge.copy()
                charge_copy['amount'] /= charge_copy['line_quantity']
                if tax := self._retrieve_fixed_tax(record.company_id, charge_copy):
                    taxes.append(tax.id)
                    if tax.price_include:
                        line_values['price_unit'] += tax.amount
                    continue
            charges_vals.append([
                charge['reason_code'] + " " + charge['reason'],
                1,
                charge['amount'],
                taxes,
            ])
        return record._get_line_vals_list(charges_vals)

    def _get_document_allowance_charge_xpaths(self):
        # OVERRIDE
        pass

    def _get_invoice_line_xpaths(self, invoice_line, qty_factor):
        # OVERRIDE
        pass

    def _correct_invoice_tax_amount(self, tree, invoice):
        pass  # To be implemented by the format if needed
