# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_br_nbs_id = fields.Many2one(
        'l10n_br.nbs.code',
        'NBS Code',
        help='Brazil: Brazilian Service Classification (NBS) code required for services in the tax reform.'
    )
    l10n_br_uom_category_id = fields.Many2one(related='uom_id.category_id')
    l10n_br_legal_uom_id = fields.Many2one(
        'uom.uom',
        'Legal Unit of Measure',
        help='Brazil: Determines the conversion factor between the commercial unit and the taxable unit when taxes apply per quantity (ad rem).',
        domain="[('category_id', '=', l10n_br_uom_category_id)]",
    )
    l10n_br_taxable_is = fields.Boolean(
        'IS taxable',
        default=True,
        help='Brazil: Indicates that this product is exempt from the Selective Tax (IS) due to a specific fiscal benefit, overriding the standard IS taxation rules.',
    )
    l10n_br_customs_regime_id = fields.Many2one(
        'l10n_br.customs.regime',
        string='Special Customs Regime',
        help='Brazil: Optional value to be selected if the transaction for the capital good is subject to a special customs regime.',
    )
    # These technical values are hardcoded on Avalara's side, and shouldn't change, so we'll do a Selection field.
    l10n_br_transaction_usage = fields.Selection(
        [
            ("Táxi", "Taxi"),
            ("Pessoas com Deficiência", "People with Disabilities"),
            ("Projetos de reabilitação urbana", "Urban Rehabilitation Projects"),
            ("Industrialização por encomenda", "Manufacturing by Order"),
            ("Locação dos imóveis localizados nas zonas reabilitadas", "Lease of Properties Located in Rehabilitated Zones"),
            ("Ferrovia", "Railway"),
            ("Depende de Evento Posterior", "Subject to a Subsequent Event"),
            ("Ativo financeiro ou instrumento cambial", "Financial Asset or Foreign Exchange Instrument"),
            ("Exploração de via", "Roadway Operation"),
            ("Contribuição de Melhoria", "Improvement Contribution"),
            ("Operações não onerosas sem previsão de IBS/CBS", "Non-Onerous Transactions without IBS/CBS Applicability"),
            ("Gorjeta até 15%", "Tip up to 15%"),
            ("Livre e Gratuita", "Free of Charge"),
            ("Operação Equiparada à Exportação", "Transaction Equivalent to Export"),
            ("Exportação Indireta", "Indirect Export"),
            ("Plataforma digital de entrega", "Digital Delivery Platform"),
            ("Matéria-prima", "Raw Material"),
            ("Embalagem", "Packaging"),
            ("Ativo Imobilizado", "Fixed Asset"),
            ("Produto Intermediário", "Intermediate Product"),
        ],
        help="Brazil: Defines the fiscal classification of how the good or service is used in the transaction, which may impact tax calculation and invoice request."
    )
