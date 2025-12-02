# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    trade_registry = fields.Char()
    l10n_cz_tax_office_id = fields.Many2one(
        string="Tax Office (CZ)",
        comodel_name='l10n_cz.tax_office',
    )
    l10n_cz_economic_activity_code = fields.Selection(
        string="Economic Activity code",
        selection=[
            ("10000", "Plant and animal production, game management and related activities"),
            ("11000", "Cultivation of non-permanent crops"),
            ("11100", "Cultivation of cereals (except rice), legumes and oil seeds"),
            ("11200", "Cultivation of rice"),
            ("11300", "Cultivation of vegetables and melons, roots and tubers"),
            ("11400", "Cultivation of sugar cane"),
            ("11500", "Cultivation of tobacco"),
            ("11600", "Cultivation of fibre crops"),
            ("11900", "Cultivation of other non-permanent crops"),
            ("12000", "Cultivation of permanent crops"),
            ("12100", "Cultivation of wine grapes"),
            ("12200", "Cultivation of tropical and subtropical fruit"),
            ("12300", "Cultivation of citrus fruit"),
            ("12400", "Cultivation of pome and stone fruit"),
            ("12500", "Cultivation of other tree and bush fruit and nuts"),
            ("12600", "Cultivation of oil fruits"),
            ("12700", "Cultivation of beverage crops"),
            ("12800", "Cultivation of spices, aromatic, medicinal and pharmaceutical plants"),
            ("12900", "Cultivation of other permanent crops"),
            ("13000", "Plant propagation"),
            ("14000", "Animal production"),
            ("14100", "Raising of dairy cattle"),
            ("14200", "Raising of other cattle"),
            ("14300", "Raising of horses and other equines"),
            ("14400", "Raising of camels and camelids"),
            ("14500", "Raising of sheep and goats"),
            ("14600", "Raising of pigs"),
            ("14700", "Raising of poultry"),
            ("14900", "Raising of other animals"),
            ("14910", "Raising of small farm animals"),
            ("14920", "Raising of fur animals"),
            ("14930", "Raising of pet animals"),
            ("14990", "Raising of other animals, n.e.c."),
            ("15000", "Mixed farming"),
            ("16000", "Support activities for agriculture and post-harvest activities"),
            ("16100", "Support activities for crop production"),
            ("16200", "Support activities for animal production"),
            ("16300", "Post-harvest activities"),
            ("16400", "Seed processing for propagation"),
            ("17000", "Hunting and trapping of wild animals and related activities"),
            ("20000", "Forestry and logging"),
            ("21000", "Forest management and other forestry activities"),
            ("22000", "Logging"),
            ("23000", "Gathering of wild-growing non-wood products and materials"),
            ("24000", "Support activities for forestry"),
            ("30000", "Fishing and aquaculture"),
            ("31000", "Fishing"),
            ("31100", "Marine fishing"),
            ("31200", "Freshwater fishing"),
            ("32000", "Aquaculture")
        ],
        help="Code of the main economic activity, according to the official classification",
    )
    l10n_cz_person_authorized = fields.Many2one(
        'res.partner',
        'Authorized Person',
        check_company=True,
        help="Natural person authorized to sign the VAT Declaration, VIES Summary report and VAT Control Statement to the legal entity",
        domain=[('type', '=', 'contact'), ('is_company', '=', False)],
    )
    l10n_cz_relationship_person_authorized = fields.Char(
        'Relationship of Authorized Person',
        compute="_compute_l10n_cz_relationship_person_authorized",
        store=True,
        readonly=False,
        help="Relationship of the person authorized to sign to the legal entity",
    )

    @api.depends('l10n_cz_person_authorized')
    def _compute_l10n_cz_relationship_person_authorized(self):
        for company in self:
            if person_authorized := company.l10n_cz_person_authorized:
                company.l10n_cz_relationship_person_authorized = person_authorized.function
            else:
                company.l10n_cz_relationship_person_authorized = None


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    account_fiscal_country_id = fields.Many2one(related="company_id.account_fiscal_country_id")
    company_registry = fields.Char(related='company_id.company_registry')
