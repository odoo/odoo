# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _
from odoo.exceptions import UserError

CANTONS = [
    ('AG', 'Argovie'),
    ('AI', 'Appenzell Rhodes-Intérieures'),
    ('AR', 'Appenzell Rhodes-Extérieures'),
    ('BE', 'Berne'),
    ('BL', 'Bâle-Campagne'),
    ('BS', 'Bâle-Ville'),
    ('FR', 'Fribourg'),
    ('GE', 'Genève'),
    ('GL', 'Glaris'),
    ('GR', 'Grisons'),
    ('JU', 'Jura'),
    ('LU', 'Lucerne'),
    ('NE', 'Neuchâtel'),
    ('NW', 'Nidwald'),
    ('OW', 'Obwald'),
    ('SG', 'Saint-Gall'),
    ('SH', 'Schaffhouse'),
    ('SO', 'Soleure'),
    ('SZ', 'Schwytz'),
    ('TG', 'Thurgovie'),
    ('TI', 'Tessin'),
    ('UR', 'Uri'),
    ('VD', 'Vaud'),
    ('VS', 'Valais'),
    ('ZG', 'Zoug'),
    ('ZH', 'Zurich'),
    ('EX', 'Foreign')
]


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_ch_canton = fields.Selection(selection=CANTONS, string="Canton", groups="hr.group_hr_user")
    l10n_ch_tax_scale = fields.Selection([
        ('A', 'Scale for single people'),
        ('B', 'Scale for married couples living in a common household with only one spouse is gainfully employed'),
        ('C', 'Scale for married couples with two incomes'),
        ('D', 'Scale for people whose AVS contributions are reimbursed'),
        ('E', 'Scale for income taxed under the procedure of simplified count'),
        ('F', 'Scale for Italian cross-border commuters whose spouse is working lucrative outside Switzerland'),
        ('G', 'Scale for income acquired as compensation which is paid to persons subject to withholding tax by a person other than that the employer'),
        ('H', 'Scale for single people living together with children or needy persons whom they take on maintenance essentials'),
        ('L', 'Scale for German cross-border commuters who fulfill the conditions of the scale A'),
        ('M', 'Scale for German cross-border commuters who fulfill the conditions of the scale B'),
        ('N', 'Scale for German cross-border commuters who fulfill the conditions of the scale C'),
        ('P', 'Scale for German cross-border commuters who fulfill the conditions of the scale H'),
        ('Q', 'Scale for German cross-border commuters who fulfill the conditions of the scale G'),
        ('R', 'Scale for Italian cross-border commuters who fulfill the conditions of the scale A'),
        ('S', 'Scale for Italian cross-border commuters who fulfill the conditions of the scale B'),
        ('T', 'Scale for Italian cross-border commuters who fulfill the conditions of the scale C'),
        ('U', 'Scale for Italian cross-border commuters who fulfill the conditions of the scale H'),
    ], string="Swiss Tax Scale", groups="hr.group_hr_user")
    l10n_ch_municipality = fields.Char(string="Municipality ID", groups="hr.group_hr_user")
    l10n_ch_religious_denomination = fields.Selection([
        ('romanCatholic', 'Roman Catholic'),
        ('christianCatholic', 'Christian Catholic'),
        ('reformedEvangelical', 'Reformed Evangelical'),
        ('jewishCommunity', 'Jewish Community'),
        ('otherOrNone', 'Other or None'),
    ], default='otherOrNone', string="Religious Denomination", groups="hr.group_hr_user")
    l10n_ch_church_tax = fields.Boolean(string="Swiss Church Tax", groups="hr.group_hr_user")
    l10n_ch_sv_as_number = fields.Char(
        string="SV-AS Number",
        groups="hr.group_hr_user",
        help="Thirteen-digit AS number assigned by the Central Compensation Office (CdC)")
    marital = fields.Selection(
        selection_add=[
            ("separated", "Separated"),
            ("registered_partnership", "Registered Partnership"),
            ("partnership_dissolved_by_law", "Partnership Dissolved By Law"),
            ("partnership_dissolved_by_death", "Partnership Dissolved By Law"),
            ("partnership_dissolved_by_declaration_of_lost", "Partnership Dissolved By Declaration of Lost"),
        ],
        ondelete={
            'separated': 'set default',
            'registered_partnership': 'set default',
            'partnership_dissolved_by_law': 'set default',
            'partnership_dissolved_by_death': 'set default',
            'partnership_dissolved_by_declaration_of_lost': 'set default',
        }, required=True)
    l10n_ch_marital_from = fields.Date(string="Marital Status Start Date", groups="hr.group_hr_user")
    l10n_ch_spouse_sv_as_number = fields.Char(string="Spouse SV-AS-Number", groups="hr.group_hr_user")
    l10n_ch_spouse_work_canton = fields.Selection(string="Spouse Work Canton", selection=CANTONS, groups="hr.group_hr_user")
    l10n_ch_spouse_work_start_date = fields.Date(string="Spouse Work Start Date", groups="hr.group_hr_user")
    l10n_ch_children = fields.One2many('l10n.ch.hr.employee.children', 'employee_id', groups="hr_payroll.group_hr_payroll_user")
    l10n_ch_has_withholding_tax = fields.Boolean(
        string="Pay Withholding Taxes", compute='_compute_l10n_ch_has_withholding_tax', store=True, readonly=False, groups="hr.group_hr_user")
    l10n_ch_residence_category = fields.Selection([
        ('shortTerm-L', 'Short Term (Cat. L)'),
        ('annual-B', 'Annual (Cat. B)'),
        ('settled-C', 'Settled (Cat. C)'),
        ('crossBorder-G', 'Cross Border (Cat. G)'),
        ('asylumSeeker-N', 'Asylum Seeker (Cat. N)'),
        ('needForProtection-S', 'Need For Protection (Cat. S)'),
        ('NotificationProcedureForShorttermWork90Days', 'Notification Procedure for Short Term Work (90 days)'),
        ('NotificationProcedureForShorttermWork120Days', 'Notification Procedure for Short Term Work (120 days)'),
        ('ProvisionallyAdmittedForeigners-F', 'Provisionally Admitted Foreigners (Cat. F)'),
        ('ResidentForeignNationalWithGainfulEmployment-Ci', 'Residence Permit with Gainful Employment (Ci)'),
        ('othersNotSwiss', 'Other (Without Swiss)'),
    ], string="Residence Category", groups="hr.group_hr_user")
    certificate = fields.Selection(selection_add=[
        ('universityMaster', 'Swiss: University College Master (university, ETH)'),
        ('universityBachelor', 'Swiss: University College Bachelor (university, ETH)'),
        ('higherEducationMaster', 'Swiss: University of Applied Sciences Master'),
        ('higherEducationBachelor', 'Swiss: University of Applied Sciences Bachelor'),
        ('higherVocEducation', 'Swiss: Higher Vocational Education'),
        ('higherVocEducationMaster', 'Swiss: Higher Vocational Education Master'),
        ('higherVocEducationBachelor', 'Swiss: Higher Vocational Education Bachelor'),
        ('teacherCertificate', 'Swiss: Teaching certificate at different levels'),
        ('universityEntranceCertificate', 'Swiss: Matura'),
        ('vocEducationCompl', 'Swiss: Complete learning attested by a federal certificate of capacity (CFC)'),
        ('enterpriseEducation', 'Swiss: In-company training only'),
        ('mandatorySchoolOnly', 'Swiss: Compulsory schooling, without full vocational training'),
        ('doctorate', 'Swiss: Doctorate, habilitation'),
    ], ondelete={
        'universityMaster': 'set default',
        'universityBachelor': 'set default',
        'higherEducationMaster': 'set default',
        'higherEducationBachelor': 'set default',
        'higherVocEducation': 'set default',
        'higherVocEducationMaster': 'set default',
        'higherVocEducationBachelor': 'set default',
        'teacherCertificate': 'set default',
        'universityEntranceCertificate': 'set default',
        'vocEducationCompl': 'set default',
        'enterpriseEducation': 'set default',
        'mandatorySchoolOnly': 'set default',
        'doctorate': 'set default'
    })
    # YTI TO Display on res.users + check 13 digits
    l10n_ch_retirement_insurance_number = fields.Char(
        string="Retirement insurance number", groups="hr.group_hr_user",
        help="The Central Compensation Office in Geneva assigns a retirement insurance (RI) number to all newborns and immigrants, which is valid for the rest of your life and remains the same even after a name change. Further information on the structure of the RI number can be found on theSwiss Federal Social Insurance Office website (in Germnan).")


    @api.depends('is_non_resident')
    def _compute_l10n_ch_has_withholding_tax(self):
        for employee in self:
            employee.l10n_ch_has_withholding_tax = employee.is_non_resident

    def _get_l10n_ch_declaration_marital(self):
        self.ensure_one()
        mapped_marital = {
            False: 'unknown',
            'single': 'single',
            'married': 'married',
            'widower': 'widowed',
            'divorced': 'divorced',
            'separated': 'separated',
            'registered_partnership': 'registeredPartnership',
            'partnership_dissolved_by_law': 'partnershipDissolvedByLaw',
            'partnership_dissolved_by_death': 'partnershipDissolvedByDeath',
            'partnership_dissolved_by_declaration_of_lost': 'partnershipDissolvedByDeclarationOfLost',
        }
        if self.marital not in mapped_marital:
            raise UserError(_('Invalid marital status for employee %s', self.name))
        return mapped_marital[self.marital]

    @api.constrains('l10n_ch_sv_as_number')
    def _check_sv_as_number(self):
        for employee in self:
            if not employee.l10n_ch_sv_as_number:
                continue
            if not employee.l10n_ch_sv_as_number.replace('.', '').isdigit() or len(employee.l10n_ch_sv_as_number) != 16:
                raise UserError(_('The SV-AS number should be a thirteen-digit number, comma-separated (eg: 756.1848.4786.64)'))

    @api.constrains('l10n_ch_spouse_sv_as_number')
    def _check_sv_as_number(self):
        for employee in self:
            if not employee.l10n_ch_spouse_sv_as_number:
                continue
            if not employee.l10n_ch_spouse_sv_as_number.replace('.', '').isdigit() or len(employee.l10n_ch_spouse_sv_as_number) != 16:
                raise UserError(_('The SV-AS number should be a thirteen-digit number, comma-separated (eg: 756.1848.4786.64)'))
