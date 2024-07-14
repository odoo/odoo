# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

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
