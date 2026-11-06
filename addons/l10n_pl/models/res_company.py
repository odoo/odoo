from odoo import fields, models

L10N_PL_LEGAL_FORMS = [
    # Codes of the legal form (TFormaPrawna) of the KRS financial statement structures
    ('FR', "Family foundation (fundacja rodzinna)"),
    ('48', "Foundation (fundacja)"),
    ('FI', "Investment fund (fundusz inwestycyjny)"),
    ('79', "Branch of a foreign entrepreneur (oddział przedsiębiorcy zagranicznego)"),
    ('73', "Employers' organisation (organizacja pracodawców)"),
    ('PA', "Simple joint-stock company (prosta spółka akcyjna)"),
    ('24', "State-owned enterprise (przedsiębiorstwo państwowe)"),
    ('80', "Foreign representative office (przedstawicielstwo zagraniczne)"),
    ('76A', "Economic and professional self-government (samorząd gospodarczy i zawodowy)"),
    ('76B', "Rural housewives' association (koło gospodyń wiejskich)"),
    ('39', "Cooperative savings and credit union (SKOK)"),
    ('40', "Housing cooperative (spółdzielnia mieszkaniowa)"),
    ('42', "European cooperative society (spółdzielnia europejska)"),
    ('16', "Joint-stock company (spółka akcyjna)"),
    ('19', "Civil law partnership (spółka cywilna)"),
    ('22', "European company (spółka europejska)"),
    ('18', "General partnership (spółka jawna)"),
    ('20', "Limited partnership (spółka komandytowa)"),
    ('21', "Limited joint-stock partnership (spółka komandytowo-akcyjna)"),
    ('15', "Professional partnership (spółka partnerska)"),
    ('17', "Limited liability company (spółka z ograniczoną odpowiedzialnością)"),
    ('55', "Association registered in the KRS (stowarzyszenie wpisane do KRS)"),
    ('00', "Association not registered in the KRS (stowarzyszenie niewpisane do KRS)"),
    ('34', "Mutual reinsurance society (towarzystwo reasekuracji wzajemnej)"),
    ('26', "Mutual insurance society (towarzystwo ubezpieczeń wzajemnych)"),
    ('85', "Housing community (wspólnota mieszkaniowa)"),
    ('74', "Employers' union (związek pracodawców)"),
    ('72', "Trade union (związek zawodowy)"),
    ('OG', "Sole proprietorship (osoba fizyczna prowadząca działalność gospodarczą)"),
    ('other', "Other"),
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pl_reports_tax_office_id = fields.Many2one('l10n_pl.l10n_pl_tax_office', string='Tax Office', groups="account.group_account_user")
    l10n_pl_legal_form = fields.Selection(selection=L10N_PL_LEGAL_FORMS, string="Legal Form")
    l10n_pl_legal_form_other = fields.Char(string="Other Legal Form")
    l10n_pl_county = fields.Char(string="County", compute='_compute_address', inverse='_inverse_l10n_pl_county')
    l10n_pl_municipality = fields.Char(string="Municipality", compute='_compute_address', inverse='_inverse_l10n_pl_municipality')

    def _get_company_address_field_names(self):
        return super()._get_company_address_field_names() + ['l10n_pl_county', 'l10n_pl_municipality']

    def _inverse_l10n_pl_county(self):
        for company in self:
            company.partner_id.l10n_pl_county = company.l10n_pl_county

    def _inverse_l10n_pl_municipality(self):
        for company in self:
            company.partner_id.l10n_pl_municipality = company.l10n_pl_municipality
