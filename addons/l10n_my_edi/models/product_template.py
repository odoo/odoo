# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

CLASSIFICATION_CODES_LIST = [
    ("001", "(001) Breastfeeding equipment "),
    ("002", "(002) Child care centres and kindergartens fees"),
    ("003", "(003) Computer, smartphone or tablet"),
    ("004", "(004) Consolidated e-Invoice "),
    (
        "005",
        "(005) Construction materials (as specified under Fourth Schedule of the Lembaga Pembangunan Industri Pembinaan Malaysia Act 1994)",
    ),
    ("006", "(006) Disbursement"),
    ("007", "(007) Donation"),
    ("008", "(008) -Commerce - e-Invoice to buyer / purchaser"),
    ("009", "(009) e-Commerce - Self-billed e-Invoice to seller, logistics, etc. "),
    ("010", "(010) Education fees"),
    ("011", "(011) Goods on consignment (Consignor)"),
    ("012", "(012) Goods on consignment (Consignee)"),
    ("013", "(013) Gym membership"),
    ("014", "(014) Insurance - Education and medical benefits"),
    ("015", "(015) Insurance - Takaful or life insurance"),
    ("016", "(016) Interest and financing expenses"),
    ("017", "(017) Internet subscription"),
    ("018", "(018) Land and building"),
    (
        "019",
        "(019) Medical examination for learning disabilities and early intervention or rehabilitation treatments of learning disabilities",
    ),
    ("020", "(020) Medical examination or vaccination expenses"),
    ("021", "(021) Medical expenses for serious diseases"),
    ("022", "(022) Others"),
    (
        "023",
        "(023) Petroleum operations (as defined in Petroleum (Income Tax) Act 1967)",
    ),
    ("024", "(024) Private retirement scheme or deferred annuity scheme"),
    ("025", "(025) Motor vehicle"),
    (
        "026",
        "(026) Subscription of books / journals / magazines / newspapers / other similar publications",
    ),
    ("027", "(027) Reimbursement"),
    ("028", "(028) Rental of motor vehicle"),
    (
        "029",
        "(029) EV charging facilities (Installation, rental, sale / purchase or subscription fees) ",
    ),
    ("030", "(030) Repair and maintenance"),
    ("031", "(031) Research and development"),
    ("032", "(032) Foreign income"),
    ("033", "(033) Self-billed - Betting and gaming"),
    ("034", "(034) Self-billed - Importation of goods"),
    ("035", "(035) Self-billed - Importation of services"),
    ("036", "(036) Self-billed - Others"),
    (
        "037",
        "(037) Self-billed - Monetary payment to agents, dealers or distributors",
    ),
    (
        "038",
        "(038) Fees related to sports equipment, facility rentals, competition registration, and training imposed by registered sports organizations under the Sports Development Act 1997",
    ),
    ("039", "(039) Supporting equipment for disabled person"),
    ("040", "(040) Voluntary contribution to approved provident fund "),
    ("041", "(041) Dental examination or treatment"),
    ("042", "(042) Fertility treatment"),
    (
        "043",
        "(043) Treatment and home care nursing, daycare centres and residential care centers",
    ),
    ("044", "(044) Vouchers, gift cards, loyalty points, etc"),
    (
        "045",
        "(045) Self-billed - Non-monetary payment to agents, dealers or distributors",
    ),
]


class ProductTemplate(models.Model):
    """
    These codes are required by the API. They represent the product classifications that are used in Malaysia.
    As defined in the list of codes allowed here: https://sdk.myinvois.hasil.gov.my/codes/classification-codes/
    """
    _inherit = "product.template"

    # ------------------
    # Fields declaration
    # ------------------

    l10n_my_edi_classification_code = fields.Selection(
        string="Malaysian classification code",
        selection=CLASSIFICATION_CODES_LIST,
    )
