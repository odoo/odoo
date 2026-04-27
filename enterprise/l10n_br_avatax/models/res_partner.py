# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_br_activity_sector = fields.Selection(
        string="Main Activity Sector",
        selection=[
            ("armedForces", "armedForces"),
            ("auctioneer", "auctioneer"),
            ("audiovisualIndustry", "audiovisualIndustry"),
            ("bondedWarehouse", "bondedWarehouse"),
            ("broadcastingIndustry", "broadcastingIndustry"),
            ("construction", "construction"),
            ("coops", "coops"),
            ("distributor", "distributor"),
            ("distributionCenter", "distributionCenter"),
            ("electricityDistributor", "electricityDistributor"),
            ("energyGeneration", "energyGeneration"),
            ("extractor", "extractor"),
            ("farmCoop", "farmCoop"),
            ("filmIndustry", "filmIndustry"),
            ("finalConsumer", "finalConsumer"),
            ("fuelDistributor", "fuelDistributor"),
            ("generalWarehouse", "generalWarehouse"),
            ("importer", "importer"),
            ("industry", "industry"),
            ("itaipubiNacional", "itaipubiNacional"),
            ("maritimeService", "maritimeService"),
            ("mealSupplier", "mealSupplier"),
            ("nonProfitEntity", "nonProfitEntity"),
            ("pharmaDistributor", "pharmaDistributor"),
            ("publicAgency", "publicAgency"),
            ("religiousEstablishment", "religiousEstablishment"),
            ("retail", "retail"),
            ("ruralProducer", "ruralProducer"),
            ("securityPublicAgency", "securityPublicAgency"),
            ("service", "service"),
            ("stockWarehouse", "stockWarehouse"),
            ("telco", "telco"),
            ("transporter", "transporter"),
            ("waterDistributor", "waterDistributor"),
            ("wholesale", "wholesale"),
            ("commerce", "commerce"),
        ],
        help="Brazil: List of main Activity Sectors of the contact"
    )
    l10n_br_taxpayer = fields.Selection(
        string="ICMS Taxpayer Type",
        selection=[
            ("icms", "ICMS Taxpayer"),
            ("exempt", "Taxpayer Exempt"),
            ("non", "Non-Taxpayer"),
        ],
        help="Brazil: Taxpayer Type informs whether the contact is within the ICMS regime, if it is Exempt, or if it is a Non-Taxpayer"
    )
    l10n_br_tax_regime = fields.Selection(
        string="Tax Regime",
        selection=[
            ("realProfit", "realProfit"),
            ("estimatedProfit", "estimatedProfit"),
            ("simplified", "simplified"),
            ("simplifiedOverGrossthreshold", "simplifiedOverGrossthreshold"),
            ("simplifiedEntrepreneur", "simplifiedEntrepreneur"),
            ("notApplicable", "notApplicable"),
            ("individual", "individual"),
            ("variable", "variable"),
        ],
        help="Brazil: Contact FederalTax Regime"
    )
    l10n_br_subject_cofins = fields.Selection(
        [("T", "Taxable"), ("N", "Not Taxable"), ("Z", "Taxable With Rate=0.00"), ("E", "Exempt"), ("H", "Suspended")],
        string="COFINS Details",
        default="T",
        help="Brazil: There are cases where both seller, buyer, and items are taxable but a special situation forces the transaction to be exempt especially "
        "for PIS and COFINS. This attribute allows users to identify such scenarios and trigger the exemption despite all other settings.",
    )
    l10n_br_subject_pis = fields.Selection(
        [("T", "Taxable"), ("N", "Not Taxable"), ("Z", "Taxable With Rate=0.00"), ("E", "Exempt"), ("H", "Suspended")],
        string="PIS Details",
        default="T",
        help="Brazil: There are cases where both seller, buyer, and items are taxable but a special situation forces the transaction to be exempt especially for PIS "
        "and COFINS. This attribute allows users to identify such scenarios and trigger the exemption despite all other settings.",
    )
    l10n_br_is_subject_csll = fields.Boolean(
        "CSLL Taxable",
        default=True,
        help="Brazil: If not checked, then it will be treated as Exempt. There are cases where both seller, buyer, and items are taxable but a special situation "
        "forces the transaction to be CSLL exempt. This attribute allows users to identify such scenarios and trigger the exemption despite "
        "all other settings.",
    )
    l10n_br_iss_simples_rate = fields.Float(
        "ISS Simplified Rate",
        help="Brazil: In case the customer or the seller - company - is in the "
        "Simplified Regime, the seller - company - needs to inform the ISS rate.",
    )
