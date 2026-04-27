from odoo import fields, models

SUPPLIES_CODE_SELECTION = [
    ('1', "Gold"),
    ('1a', "Gold - brokering the delivery of investment gold"),
    ('3', "Delivery of immovable property, if tax is applied to this delivery"),
    ('3a', "Delivery of immovable property in forced sale"),
    ('4', "Construction and assembly work"),
    ('4a', "Construction and assembly work - provision of workers"),
    ('5', "Goods listed in Appendix No. 5"),
    ('6', "Delivery of goods originally provided as a guarantee"),
    ('7', "Delivery of goods after transfer of retention of title"),
    ('11', "Permits for emissions according to Section 92f of the VAT Act"),
    ('12', "Cereals and technical crops"),
    ('13', "Metals"),
    ('14', "Mobile Phones"),
    ('15', "Integrated circuits"),
    ('16', "Portable devices for automated data processing"),
    ('17', "Video game console"),
    ('18', "Delivery of electricity certificates"),
    ('19', "Supply of electricity through systems or networks to a trader"),
    ('20', "Delivery of gas through systems or networks to the trader"),
    ('21', "Provision of defined electronic communications services"),
]


TRANSACTION_CODE_SELECTION = [
    ('0', "0 Goods"),
    ('1', "1 Business asset"),
    ('2', "2 Triangular"),
    ('3', "3 Service"),
]

TRANSACTION_CODE_HELP = """
    Transaction code:
    0 - Supply of goods to another Member State to a person registered for tax in another Member State (Section 13(1) and (2) of the Act)
    1 - Transfer of business assets by the taxpayer to another Member State (Article 13(6) of the Act)
    2 - Supply of goods within the territory of the European Community in the form of triangular trade (Section 17 of the Act), this code is to be filled in by the middle person only
    3 - Supply of a service with a place of supply in another Member State (Article 9(1) of the Act), if the recipient of the service is obliged to declare and pay the tax
    Required in the line not marked as cancellation line.
"""


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_cz_transaction_code = fields.Selection(
        string="Transaction code",
        selection=TRANSACTION_CODE_SELECTION,
        help=TRANSACTION_CODE_HELP,
    )

    # If a reverse charge transaction, user has to choose a reverse charge supply code.
    l10n_cz_supplies_code = fields.Selection(
        selection=SUPPLIES_CODE_SELECTION,
        string="Code of Supply",
        help="Code of subject of supply in the domestic reverse charge regime.",
    )
