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
            ('2601110000', 'Unagglomerated'),
            ('2601120000', 'Agglomerates'),
            ('2601200000', 'Roasted iron pyrites (pyrite ashes)'),
            ('2602000000', 'Manganese ores and concentrates thereof, including ferruginous manganese ores and '
             'concentrates thereof, containing 20 % more by weight of manganese, on dry product.'),
            ('2603000000', 'Copper ores and concentrates'),
            ('2604000000', 'Nickel ores and their concentrates'),
            ('2605000000', 'Cobalt ores and concentrates'),
            ('2606000000', 'Aluminium ores and their concentrates'),
            ('2607000000', 'Lead ores and concentrates'),
            ('2608000010', 'Low-grade zinc concentrate'),
            ('2608000090', 'Others (Zinc)'),
            ('2609000000', 'Tin ores and concentrates'),
            ('2610000000', 'Chromium ores and their concentrates'),
            ('2611000000', 'Tungsten ores and concentrates'),
            ('2612100000', 'Uranium ores and concentrates'),
            ('2612200000', 'Thorium ores and concentrates'),
            ('2613100000', 'Toasted'),
            ('2613900000', 'Others (Molybdenum)'),
            ('2614000000', 'Titanium ores and their concentrates'),
            ('2615100000', 'Zirconium ores and their concentrates'),
            ('2615900000', 'Others (Niobium, Tantalum, Vanadium)'),
            ('2616100000', 'Silver ores and concentrates'),
            ('2616901000', 'Gold ores and concentrates'),
            ('2616909000', 'Others (Precious metal)'),
            ('2617100000', 'Antimony minerals and concentrates'),
            ('2617900000', 'Others (Mineral)'),
            ('2618000000', 'Granulated slag (slag sand) from the steel industry'),
            ('2619000000', 'Slag (other than granulated), beats and other waste from the iron and steel industry'),
            ('2620110000', 'Galvanizing mats'),
            ('2620190000', 'Others (Metal residues)'),
            ('2620210000', 'Leaded gasoline sludge and leaded antiknock compound sludge'),
            ('2620290000', 'Others (Metal-containing sludges)'),
            ('2620300000', 'Containing mainly copper'),
            ('2620400000', 'Containing mainly aluminium'),
            ('2620600000', 'Containing arsenic, mercury, thallium or mixtures thereof, of a kind used for the '
             'extraction of arsenic or these metals or for the manufacture of their chemical compounds'),
            ('2620910000', 'Containing antimony, beryllium, cadmium, chromium, or mixtures thereof'),
            ('2620990000', 'Others (Toxic residues: As, Hg, Tl, etc.)'),
            ('2621100000', 'Ash and residues from the incineration of municipal waste'),
            ('2621900000', 'Others (Ashes and residues)'),
        ],
        string="Tariff Fraction (PE)",
        help="Peru: The tariff fraction of the product. This takes the form of the HS Code of the corresponding description."
    )
