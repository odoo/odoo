# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import _, models, fields

SALE_TYPES = [
    ('T1000017', "Goods"),
    ('T1000018', "Services"),
    ('T1000019', "Special Procedure Goods"),
    ('T1000020', "Goods at 50% Exemption (KPK)"),
    ('T1000021', "Goods (FED in ST Mode)"),
    ('T1000022', "Services (FED in ST Mode)"),
    ('T1000023', "3rd Schedule Goods"),
    ('T1000024', "Goods at Reduced Rate"),
    ('T1000025', "Processing/Conversion of Goods"),
    ('T1000038', "Cell Phone Activation"),
    ('T1000041', "Electricity at Specific Rate"),
    ('T1000042', "Re-rollable Scrap"),
    ('T1000045', "Non-Taxable Services"),
    ('T1000048', "Mobile/Satellite Phone U/SRO 280 of 2013"),
    ('T1000049', "Adjustment Given to Steel Melters under SRO1486 (I)/2012"),
    ('T1000053', "Mobile/Satellite Phone"),
    ('T1000054', "SIM Card Activation"),
    ('T1000056', "Production Capacity"),
    ('T1000057', "Goods under SRO 649(I)/2013"),
    ('T1000059', "Palm Fatty Acid Distillate"),
    ('T1000062', "Electricity Supply to Retailers"),
    ('T1000075', "Goods at standard rate (default)"),
    ('T1000076', "Electricity to steel sector"),
    ('T1000077', "Gas to CNG stations"),
    ('T1000078', "Rerollable scrap by ship breakers"),
    ('T1000079', "SIM sale / IMEI activation"),
    ('T1000080', "Goods at zero-rate"),
    ('T1000081', "Exempt goods"),
    ('T1000082', "DTRE goods"),
    ('T1000083', "Other"),
    ('T1000084', "Telecommunication services"),
    ('T1000085', "Petroleum Products"),
    ('T1000087', "Special procedure cottonseed"),
    ('T1000088', "ReRollable Scrap"),
    ('T1000090', "Petroleum Products in Quantity"),
    ('T1000111', "Electricity Supplied to marble/granite industry"),
    ('T1000113', "Remeltable scrap"),
    ('T1000115', "Potassium Chlorate"),
    ('T1000119', "IMS Fiscal Transactions"),
    ('T1000122', "Mobile Phones"),
    ('T1000123', "Steel melting and re-rolling"),
    ('T1000125', "Ship breaking"),
    ('T1000129', "SIM"),
    ('T1000130', "Cotton ginners"),
    ('T1000132', "Electric Vehicle"),
    ('T1000134', "Cement /Concrete Block"),
    ('T1000136', "Online Marketplace"),
    ('T1000138', "Non-Adjustable Supplies"),
    ('T1000139', "Goods as per SRO.297(|)/2023"),
]

SCHEDULE_CODES = [
    ('S1000012', "FED 1st Schedule"),
    ('S1000047', "946(I)/2013"),
    ('S1000055', "572(I)/2014"),
    ('S1000056', "898(I)/2013"),
    ('S1000058', "549(I)/2008"),
    ('S1000059', "646(I)/2005"),
    ('S1000061', "863(I)/2007"),
    ('S1000062', "Zero Rated Elec."),
    ('S1000063', "Zero Rated Gas"),
    ('S1000065', "Section 4(b)"),
    ('S1000066', "670(I)/2013"),
    ('S1000067', "1007(I)/2005"),
    ('S1000068', "164(I)/2010"),
    ('S1000069', "172(I)/2006"),
    ('S1000070', "326(I)/2008"),
    ('S1000071', "408(I)/2012"),
    ('S1000072', "539(I)/2008"),
    ('S1000073', "542(I)/2008"),
    ('S1000074', "551(I)/2008"),
    ('S1000075', "727(I)/2011"),
    ('S1000076', "76(I)/2008"),
    ('S1000077', "880(I)/2007"),
    ('S1000080', "FED 3rd Schedule Table I"),
    ('S1000081', "FED 3rd Schedule Table II"),
    ('S1000082', "525(I)/2008"),
    ('S1000083', "811(I)/2009"),
    ('S1000084', "802(I)/2009"),
    ('S1000085', "678(I)/2004"),
    ('S1000086', "760(I)/2012"),
    ('S1000087', "499(I)/2013"),
    ('S1000088', "501(I)/2013"),
    ('S1000089', "896(I)/2013"),
    ('S1000090', "DTRE"),
    ('S1000095', "342(I)/2002"),
    ('S1000096', "188(I)/2015"),
    ('S1000100', "213(I)/2013"),
    ('S1000106', "327(I)/2008"),
    ('S1000107', "484(I)/2015"),
    ('S1000118', "1180(I)/2016"),
    ('S1000119', "21(I)/2017"),
    ('S1000120', "91(I)/2017"),
    ('S1000121', "125(I)/2017"),
    ('S1000122', "223(I)/2017"),
    ('S1000123', "408(I)/2017"),
    ('S1000124', "581(I)/2017"),
    ('S1000126', "608(I)/2012"),
    ('S1000127', "79(I)/2012"),
    ('S1000128', "657(I)/2013"),
    ('S1000130', "398(I)/2015"),
    ('S1000335', "292(I)/2017"),
    ('S1000345', "867(I)/2017"),
    ('S1000346', "757(I)/2017"),
    ('S1000347', "713(I)/2017"),
    ('S1000349', "984(I)/2017"),
    ('S1000350', "641(I)/2017"),
    ('S1000352', "781(I)2018"),
    ('S1000353', "777(I)2018"),
    ('S1000358', "1167(I)/2018"),
    ('S1000359', "1308(I)/2018"),
    ('S1000360', "1125(I)/2011"),
    ('S1000362', "253(I)/2019"),
    ('S1000371', "8th Schedule Table II"),
    ('S1000383', "6th Schedule Table I"),
    ('S1000384', "6th Schedule Table II"),
    ('S1000387', "5th Schedule"),
    ('S1000390', "495(I)/2016"),
    ('S1000394', "3rd Schedule"),
    ('S1000395', "590(I)/2017"),
    ('S1000396', "Section 49"),
    ('S1000397', "587(I)/2017"),
    ('S1000398', "237(I)/2020"),
    ('S1000399', "6th Schedule Table III"),
    ('S1000404', "1450(I)/2021"),
    ('S1000408', "1579(1)/2021"),
    ('S1000412', "1604(I)/2021"),
    ('S1000416', "01(I)/2022"),
    ('S1000420', "88(I)/2022"),
    ('S1000424', "183(I)/2022"),
    ('S1000429', "321(I)/2022"),
    ('S1000431', "ICTO Table II"),
    ('S1000433', "1212(I)/2018"),
    ('S1000441', "1636(1)/2022"),
    ('S1000446', "9th Schedule"),
    ('S1000449', "297(I)/2023-Table-II"),
    ('S1000450', "297(I)/2023-Table-I"),
    ('S1000451', "8th Schedule Table I"),
    ('S1000452', "ICTO Table I")
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_pk_edi_sale_type = fields.Selection(
        selection=SALE_TYPES,
        string="Sale Type (FBR)",
        default='T1000024',
        required=True
    )
    l10n_pk_edi_schedule_code = fields.Selection(
        selection=SCHEDULE_CODES,
        string="Schedule Code (FBR)",
        default='S1000012'
    )
    l10n_pk_edi_hs_code = fields.Char(
        string="HS Code (FBR)",
        help="Standardized code for international shipping and goods declaration.",
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _l10n_pk_edi_export_check(self):
        """
            Validating Products for E-Invoicing Compliance
        """

        def _group_by_error_code(product):
            if any(not product[field] for field in (
                'l10n_pk_edi_sale_type', 'l10n_pk_edi_schedule_code', 'l10n_pk_edi_hs_code'
            )):
                return 'product_value_missing'
            if (
                product.l10n_pk_edi_hs_code
                and not re.match('^[a-zA-Z0-9]{8}$', product.l10n_pk_edi_hs_code)
            ):
                return 'product_hscode_invalid'
            return False

        error_messages = {
            'product_value_missing': _(
                "Product(s) should have a Sale Type, Schedule Code and HS Code."
            ),
            'product_hscode_invalid': _(
                "Product(s) has invalid HS Code. It should contains exactly 8 digits."
            ),
        }
        return {
            f"l10n_pk_edi_{error_code}": {
                'level': 'danger',
                'message': error_messages[error_code],
                'action_text': _("View Product(s)"),
                'action': products._get_records_action(name=_("Check Product(s)")),
            } for error_code, products in self.grouped(_group_by_error_code).items() if error_code
        }
