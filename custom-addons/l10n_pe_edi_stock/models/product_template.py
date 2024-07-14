# coding: utf-8

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_pe_edi_tariff_fraction = fields.Selection(
        selection=[
            ('1701130000', 'Cane sugar'),
            ('1701140000', 'Other cane sugars'),
            ('1701910000', 'With added flavoring or coloring'),
            ('1701999000', 'Others (Sugar)'),
            ('1703100000', 'Cane Molasses'),
            ('2207100000', 'Undenatured ethyl alcohol with an alcoholic strength by volume of at least 80% vol'),
            ('2207200010', 'Alcohol fuel'),
            ('2207200090', 'Others (Alcohol)'),
            ('2208901000', 'Undenatured ethyl alcohol with an alcoholic strength by volume of less than 80% vol'),
            ('1006200000', 'Husked rice (cargo rice or brown rice)'),
            ('1006300000', 'Semi-milled or milled rice, including pearled or glazed'),
            ('1006400000', 'Broken rice'),
            ('2302200000', 'Not applicable'),
        ],
        string="Tariff Fraction (PE)",
        help="Peru: The tariff fraction of the product. This takes the form of the HS Code of the corresponding description."
    )
