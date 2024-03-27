# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools import frozendict


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # If a reverse charge transaction, user has to choose a reverse charge supply code.
    l10n_cz_supplies_code = fields.Selection(
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

    # Helper field for defining when code of supply is mandatory
    is_reverse_charge = fields.Boolean(
        string="Is Reverse Charge",
        default=False,
        help="Whether line contains a tax related to reverse charge transactions",
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    def _compute_tax_key(self):
        """ Override to allow extra keys/split in the reverse charge tax lines"""
        super()._compute_tax_key()
        for line in self.filtered('l10n_cz_supplies_code'):
            line.tax_key = frozendict(**line.tax_key, l10n_cz_supplies_code=line.l10n_cz_supplies_code)

    def _compute_all_tax(self):
        """ Override to allow extra keys/split in the reverse charge tax lines"""
        super()._compute_all_tax()
        for line in self.filtered('l10n_cz_supplies_code'):
            for key in list(line.compute_all_tax.keys()):
                new_key = frozendict(**key, l10n_cz_supplies_code=line.l10n_cz_supplies_code)
                line.compute_all_tax[new_key] = line.compute_all_tax.pop(key)

    @api.onchange('tax_ids')
    def _onchange_tax_ids(self):
        for line in self:
            if any(line.tax_ids._origin.mapped('l10n_cz_reverse_charge')):
                line.is_reverse_charge = True
            else:
                line.is_reverse_charge = False
