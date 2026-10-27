# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_it_exempt_reason = fields.Selection(
        selection=[
            ("N1", "[N1] Escluse ex art. 15"),
            ("N2", "[N2] Non soggette"),
            ("N2.1", "[N2.1] Non soggette ad IVA ai sensi degli artt. Da 7 a 7-septies del DPR 633/72"),
            ("N2.2", "[N2.2] Non soggette - altri casi"),
            ("N3", "[N3] Non imponibili"),
            ("N3.1", "[N3.1] Non imponibili - esportazioni"),
            ("N3.2", "[N3.2] Non imponibili - cessioni intracomunitarie"),
            ("N3.3", "[N3.3] Non imponibili - cessioni verso San Marino"),
            ("N3.4", "[N3.4] Non imponibili - operazioni assimilate alle cessioni all'esportazione"),
            ("N3.5", "[N3.5] Non imponibili - a seguito di dichiarazioni d'intento"),
            ("N3.6", "[N3.6] Non imponibili - altre operazioni che non concorrono alla formazione del plafond"),
            ("N4", "[N4] Esenti"),
            ("N5", "[N5] Regime del margine / IVA non esposta in fattura"),
            ("N6", "[N6] Inversione contabile (per le operazioni in reverse charge ovvero nei casi di autofatturazione per acquisti extra UE di servizi ovvero per importazioni di beni nei soli casi previsti)"),
            ("N6.1", "[N6.1] Inversione contabile - cessione di rottami e altri materiali di recupero"),
            ("N6.2", "[N6.2] Inversione contabile - cessione di oro e argento puro"),
            ("N6.3", "[N6.3] Inversione contabile - subappalto nel settore edile"),
            ("N6.4", "[N6.4] Inversione contabile - cessione di fabbricati"),
            ("N6.5", "[N6.5] Inversione contabile - cessione di telefoni cellulari"),
            ("N6.6", "[N6.6] Inversione contabile - cessione di prodotti elettronici"),
            ("N6.7", "[N6.7] Inversione contabile - prestazioni comparto edile esettori connessi"),
            ("N6.8", "[N6.8] Inversione contabile - operazioni settore energetico"),
            ("N6.9", "[N6.9] Inversione contabile - altri casi"),
            ("N7", "[N7] IVA assolta in altro stato UE (prestazione di servizi di telecomunicazioni, tele-radiodiffusione ed elettronici ex art. 7-octies, comma 1 lett. a, b, art. 74-sexies DPR 633/72)")
        ],
        string="Exoneration",
        help="Exoneration type",
    )
    l10n_it_law_reference = fields.Char(string="Law Reference", size=100)

    @api.constrains('l10n_it_exempt_reason',
                    'l10n_it_law_reference',
                    'amount',
                    'invoice_repartition_line_ids',
                    'refund_repartition_line_ids')
    def _l10n_it_edi_check_exoneration_with_no_tax(self):
        for tax in self:
            if tax.country_id.code == 'IT':
                if tax.amount_type == 'percent' and tax.amount == 0 and not (tax.l10n_it_exempt_reason and tax.l10n_it_law_reference):
                    raise ValidationError(_("If the tax amount is 0%, you must enter the exoneration code and the related law reference."))
                if tax.l10n_it_exempt_reason == 'N6' and tax._l10n_it_is_split_payment():
                    raise UserError(_("Split Payment is not compatible with exoneration of kind 'N6'"))

    def _l10n_it_get_tax_kind(self):
        if self.amount_type == 'percent' and self.amount >= 0:
            return 'vat'
        return None

    def _l10n_it_filter_kind(self, kind):
        """ Filters taxes depending on _l10n_it_get_tax_kind. """
        return self.filtered(lambda tax: tax._l10n_it_get_tax_kind() == kind)

    def _l10n_it_is_split_payment(self):
        """ Split payment means that the Public Administration buyer will pay VAT
            to the tax agency instead of the vendor
        """
        self.ensure_one()

        tax_tags = self.get_tax_tags(is_refund=False, repartition_type='tax') | self.get_tax_tags(is_refund=False, repartition_type='base')
        if not tax_tags:
            return False

        it_tax_report_ve38_lines = self.env['account.report.line'].search([
            ('report_id.country_id.code', '=', 'IT'),
            ('code', '=', 'VE38'),
        ])
        if not it_tax_report_ve38_lines:
            return False

        ve38_lines_tags = it_tax_report_ve38_lines.expression_ids._get_matching_tags()
        return bool(tax_tags & ve38_lines_tags)
