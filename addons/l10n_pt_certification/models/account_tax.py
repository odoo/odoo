from odoo import api, fields, models
from odoo.exceptions import ValidationError

L10N_PT_TAX_REGIONS_SELECTION = [
    ('PT-ALL', 'All Regions'),
    ('PT', 'Mainland Portugal'),
    ('PT-MA', 'Madeira'),
    ('PT-AC', 'Azores'),
]

L10N_PT_TAX_CATEGORIES_SELECTION = [
    ('N', 'Normal'),
    ('I', 'Intermediate'),
    ('R', 'Reduced'),
    ('E', 'Exempt'),
]

# The AT table of VAT exemption reasons, v4.0 (2026-06-18), referenced by Portaria 302/2016: each code with
# the mention printed on the document and exported as the SAF-T TaxExemptionReason (6 to 60 characters).
# e-Fatura rejects a code outside the current table (FAQ 5002).
# https://info.portaldasfinancas.gov.pt/pt/apoio_ao_contribuinte/Negocios/Faturacao/Regras_mecanismos_comunicacao/e_Fatura/e_Fatura_Comunicacao_elementos_docs_faturacao_2022_seguintes/Documents/Tabela_Codigos_Motivo_Isencao.pdf
L10N_PT_TAX_EXEMPTION_MENTIONS = {
    "M01": "Artigo 16.º n.º 6 do CIVA",
    "M02": "Artigo 6.º do Decreto-Lei n.º 198/90, de 19 de junho",
    "M04": "Isento artigo 13.º do CIVA",
    "M05": "Isento artigo 14.º do CIVA",
    "M06": "Isento artigo 15.º do CIVA",
    "M07": "Isento artigo 9.º do CIVA",
    "M09": "IVA – não confere direito a dedução",
    "M10": "IVA – regime de isenção",
    "M11": "Regime particular do tabaco",
    "M12": "Regime da margem de lucro – Agências de viagens",
    "M13": "Regime da margem de lucro – Bens em segunda mão",
    "M14": "Regime da margem de lucro – Objetos de arte",
    # The table's own mention, with spaces around the dash, is 61 characters: one over the SAF-T's limit.
    "M15": "Regime da margem de lucro–Objetos de coleção e antiguidades",
    "M16": "Isento artigo 14.º do RITI",
    "M19": "Outras isenções",
    "M20": "IVA – regime forfetário",
    "M21": "IVA – não confere direito à dedução",
    "M25": "Mercadorias à consignação",
    "M26": "Isenção de IVA com direito à dedução no cabaz alimentar",
    "M30": "IVA – autoliquidação",
    "M31": "IVA – autoliquidação",
    "M32": "IVA – autoliquidação",
    "M33": "IVA – autoliquidação",
    "M34": "IVA – autoliquidação",
    "M35": "IVA – autoliquidação",
    "M40": "IVA – autoliquidação",
    "M41": "IVA – autoliquidação",
    "M42": "IVA – autoliquidação",
    "M43": "IVA – autoliquidação",
    "M44": "IVA – Regras específicas – artigo 6.º",
    "M45": "IVA – regime transfronteiriço de isenção",
    "M46": "IVA – e-TaxFree",
    "M99": "Não sujeito ou não tributado",
}

# The legal basis (the same table's "Norma aplicável") telling apart the codes that share a mention, shown
# where the code is chosen.
L10N_PT_TAX_EXEMPTION_LEGAL_BASES = {
    "M30": "art. 2.º n.º 1 i) CIVA",
    "M31": "art. 2.º n.º 1 j) CIVA",
    "M32": "art. 2.º n.º 1 l) CIVA",
    "M33": "art. 2.º n.º 1 m) CIVA",
    "M34": "art. 2.º n.º 1 n) CIVA",
    "M35": "art. 2.º n.º 1 j) CIVA, verba 2.42 da lista I, from 2026-07-01",
    "M40": "art. 6.º n.º 6 a) CIVA",
    "M41": "art. 8.º n.º 3 RITI",
    "M42": "DL 21/2007",
    "M43": "DL 362/99",
}

# The reason printed on the documents: the code and its mention, without the legal basis.
L10N_PT_TAX_EXEMPTION_PRINTED_REASONS = {code: f"{code} - {mention}" for code, mention in L10N_PT_TAX_EXEMPTION_MENTIONS.items()}

L10N_PT_TAX_EXEMPTION_REASONS_SELECTION = [
    (code, reason + (f" ({basis})" if (basis := L10N_PT_TAX_EXEMPTION_LEGAL_BASES.get(code)) else ""))
    for code, reason in L10N_PT_TAX_EXEMPTION_PRINTED_REASONS.items()
]


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_pt_tax_exemption_reason = fields.Selection(string="Tax Exemption Reason", selection=L10N_PT_TAX_EXEMPTION_REASONS_SELECTION)

    @api.constrains('l10n_pt_tax_exemption_reason', 'amount', 'amount_type', 'country_id')
    def _validate_l10n_pt_tax_exemption_reason(self):
        """
        According to Portugal's tax authority: "The program should ensure the enforceability for the user
        to present a reason for not assessing tax, if it is the case." (Despacho 8632/2014 3.2.6). Checked
        whenever the reason, rate, type or country changes, so a PT tax cannot become 0 % without one.
        """
        if taxes := self.filtered(lambda tax: tax._l10n_pt_lacks_exemption_reason()):
            raise ValidationError(self.env._(
                "Exempt taxes require an exemption reason: set one on %(taxes)s.",
                taxes=", ".join(taxes.mapped('name')),
            ))

    def _l10n_pt_lacks_exemption_reason(self):
        """Whether this PT tax charges nothing without saying why (a group of taxes charges its children)."""
        self.ensure_one()
        return (
            self.country_code == 'PT'
            and self.amount_type != 'group'
            and self.amount == 0
            and not self.l10n_pt_tax_exemption_reason
        )


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    l10n_pt_tax_region = fields.Selection(string="Region (PT)", selection=L10N_PT_TAX_REGIONS_SELECTION, default="PT")
    l10n_pt_tax_category = fields.Selection(string="Tax Category (PT)", selection=L10N_PT_TAX_CATEGORIES_SELECTION, default="N")
