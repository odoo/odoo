from odoo import fields, models, api, _
from odoo.exceptions import UserError


SA_EXEMPTION_REASON_CODES = [
    ('VATEX-SA-29', 'VATEX-SA-29 Financial services mentioned in Article 29 of the VAT Regulations | الخدمات المالية'),
    ('VATEX-SA-29-7', 'VATEX-SA-29-7 Life insurance services mentioned in Article 29 of the VAT Regulations | عقد تأمين على الحياة'),
    ('VATEX-SA-30', 'VATEX-SA-30 Real estate transactions mentioned in Article 30 of the VAT Regulations | التوريدات العقارية المعفاة من الضريبة'),
    ('VATEX-SA-32', 'VATEX-SA-32 Export of goods | صادرات السلع من المملكة'),
    ('VATEX-SA-33', 'VATEX-SA-33 Export of Services | صادرات الخدمات من المملكة'),
    ('VATEX-SA-34-1', 'VATEX-SA-34-1 The international transport of Goods | النقل الدولي للسلع'),
    ('VATEX-SA-34-2', 'VATEX-SA-34-2 The international transport of Passengers | النقل الدولي للركاب'),
    ('VATEX-SA-34-3', 'VATEX-SA-34-3 Services directly connected and incidental to a Supply of international passenger transport | الخدمات المرتبطة مباشرة أو عرضيا بتوريد النقل الدولي للركاب'),
    ('VATEX-SA-34-4', 'VATEX-SA-34-4 Supply of a qualifying means of transport | توريد وسائل نقل مؤهلة'),
    ('VATEX-SA-34-5', 'VATEX-SA-34-5 Any services relating to Goods or passenger transportation, as defined in article twenty five of these Regulations | الخدمات ذات الصلة بنقل السلع أو الركاب، وفقا ً للتعريف الوارد بالمادة الخامسة والعشرين من الالئحة التنفيذية لنظام ضريبة القيامة المضافة'),
    ('VATEX-SA-35', 'VATEX-SA-35 Medicines and medical equipment | الأدوية والمعدات الطبية'),
    ('VATEX-SA-36', 'VATEX-SA-36 Qualifying metals | المعادن المؤهلة'),
    ('VATEX-SA-EDU', 'VATEX-SA-EDU Private education to citizen | الخدمات التعليمية الخاصة للمواطنين'),
    ('VATEX-SA-HEA', 'VATEX-SA-HEA Private healthcare to citizen | الخدمات الصحية الخاصة للمواطنين'),
    ('VATEX-SA-MLTRY', 'VATEX-SA-MLTRY Supply of qualified military goods | توريد السلع العسكرية المؤهلة'),
    ('VATEX-SA-OOS', 'VATEX-SA-OOS Reason is free text, Exemption Reason will be used')
]


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_sa_is_retention = fields.Boolean("Is Retention", default=False,
                                          help="Determines whether or not a tax counts as a Withholding Tax")
    free_text_exemption_reason = fields.Char("Exemption Reason", help="Free text exemption reason for VATEX-SA-OOS")

    @api.onchange('amount')
    def onchange_amount(self):
        super().onchange_amount()
        self.l10n_sa_is_retention = False

    @api.constrains("l10n_sa_is_retention", "amount", "type_tax_use")
    def _l10n_sa_constrain_is_retention(self):
        for tax in self:
            if tax.amount >= 0 and tax.l10n_sa_is_retention and tax.type_tax_use == 'sale':
                raise UserError(_("Cannot set a tax to Retention if the amount is greater than or equal 0"))

    @api.depends('ubl_cii_tax_category_code')
    def _compute_ubl_cii_requires_exemption_reason(self):
        # EXTEND
        super()._compute_ubl_cii_requires_exemption_reason()
        for tax in self:
            if tax.country_code == 'SA':
                tax.ubl_cii_requires_exemption_reason = (
                    tax.type_tax_use == 'sale' and
                    tax.amount == 0
                )

    def _get_exemption_reason_code_selection(self):
        # EXTEND
        if self.env.company.country_id.code == 'SA':
            return SA_EXEMPTION_REASON_CODES
        return super()._get_exemption_reason_code_selection()

    def _compute_show_tax_category_code(self):
        # EXTEND
        super()._compute_show_tax_category_code()
        for tax in self:
            if tax.country_code == 'SA':
                tax.show_tax_category_code = False
