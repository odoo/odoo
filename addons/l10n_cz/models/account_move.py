# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    taxable_supply_date = fields.Date()
    reverse_charge = fields.Boolean(help='Received or realized taxable supplies in the domestic reverse charge regime')
    # If a reverse charge transaction, user has to choose a reverse charge supply code.
    supplies_code_reverse_charge = fields.Selection(
        selection=[
            ('1', 'Gold'),
            ('1a', 'Gold - brokering the delivery of investment gold'),
            ('3', 'Delivery of immovable property, if tax is applied to this delivery'),
            ('3a', 'Delivery of immovable property in forced sale'),
            ('4', 'Construction and assembly work'),
            ('4a', 'Construction and assembly work - provision of workers'),
            ('5', 'Goods listed in Appendix No. 5'),
            ('6', 'Delivery of goods originally provided as a guarantee'),
            ('7', 'Delivery of goods after transfer of retention of title'),
            ('11', 'Permits for emissions according to Section 92f of the VAT Act'),
            ('12', 'Cereals and technical crops'),
            ('13', 'Metals'),
            ('14', 'Mobile Phones'),
            ('15', 'Integrated circuits'),
            ('16', 'Portable devices for automated data processing'),
            ('17', 'Video game console'),
            ('18', 'Delivery of electricity certificates'),
            ('19', 'Supply of electricity through systems or networks to a trader'),
            ('20', 'Delivery of gas through systems or networks to the trader'),
            ('21', 'Provision of defined electronic communications services'),
        ],
        string='Code of Supply',
        help='Code of subject of supply in the domestic reverse charge regime.',
    )
    # If not a reverse charge transaction, user can optionally select a scheme code
    scheme_code = fields.Selection(
        selection=[
            ('0', '0 - Standard VAT regime'),
            ('1', '1 - Section 89 of VAT Act special scheme for a travel service'),
            ('2', '2 - Section 90 of VAT Act margin scheme'),
        ],
        string='Special scheme code',
        help='Code indicating special scheme, needed for VAT control report.',
        default='0',
    )
