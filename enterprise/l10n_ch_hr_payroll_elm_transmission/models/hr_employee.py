# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import re
import uuid

CANTONS_WITH_EX = [
    ('EX', 'EX - Foreign'),
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
]

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
]


tax_id_pattern = r"[A-Z]{6}[0-9]{2}(A|B|C|D|E|H|L|M|P|R|S|T)[0-9]{2}[A-Z]{1}[0-9]{3}[A-Z]{1}"


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_ch_legal_first_name = fields.Char(string="First Name", compute="_compute_l10n_ch_legal_name", store=True, readonly=False, tracking=True, groups="hr.group_hr_user")
    l10n_ch_legal_last_name = fields.Char(string="Last Name", compute="_compute_l10n_ch_legal_name", store=True, readonly=False, tracking=True, groups="hr.group_hr_user")
    l10n_ch_country_id_code = fields.Char(string="Nationality Country Code", related='country_id.code', groups="hr.group_hr_user")
    l10n_ch_po_box = fields.Char(string="PO. Box", groups="hr.group_hr_user", tracking=True)

    l10n_ch_no_nationality = fields.Selection(selection=[("11", "11 - Unknown"),
                                                         ("22", "22 - Stateless")], string="Special Nationality Status", groups="hr.group_hr_user", tracking=True)

    l10n_ch_tax_scale_type = fields.Selection(string="Tax Scale Type", selection=[('TaxAtSourceCode', 'Tariff Code'),
                                                                                  ('CategoryPredefined', "Predefined Category"),
                                                                                  ('CategoryOpen', "Open")], default="TaxAtSourceCode", groups="hr.group_hr_user", tracking=True)
    l10n_ch_pre_defined_tax_scale = fields.Selection(string="Predefined Tax Scale",
                                                     selection=[('NON', "NON - Not Subject to Source Tax, without Church Tax"),
                                                                ('NOY', "NOY - Not Subject to Source Tax, with Church Tax"),
                                                                ('HEN', "HEN - Honorary Board of Directors residing abroad, without Church tax"),
                                                                ('HEY', "HEY - Honorary Board of Directors residing abroad, with Church tax"),
                                                                ('MEN', "MEN - Monetary Value Services residing abroad, without Church tax"),
                                                                ('MEY', "MEY - Monetary Value Services residing abroad, with Church tax"),
                                                                ('SFN', "SFN - Special Agreement with France Tariff")
                                                                ], groups="hr.group_hr_user", tracking=True)
    l10n_ch_open_tax_scale = fields.Char(string="Open Tax Scale", groups="hr.group_hr_user", tracking=True)
    l10n_ch_tax_specially_approved = fields.Boolean(string="Specially Approved by the ACI", groups="hr.group_hr_user", tracking=True)
    l10n_ch_tax_code = fields.Char(string="Source Tax Code", compute="_compute_l10n_ch_tax_code", groups="hr.group_hr_user", tracking=True)
    l10n_ch_source_tax_canton = fields.Char(string="Source Tax Canton", compute="_compute_l10n_ch_source_tax_canton", groups="hr.group_hr_user")
    l10n_ch_source_tax_municipality = fields.Char(string="Source Tax Municipality", compute="_compute_l10n_ch_source_tax_municipality", groups="hr.group_hr_user")
    l10n_ch_concubinage = fields.Selection(string="Concubinage", selection=[("NoConcubinage", "No"),
                                                                            ("SoleCustody", "Yes with the sole custody"),
                                                                            ("ShareCustodyAndHigherIncome", "Yes with a shared custody and higher income"),
                                                                            ("AdultChildAndHigherIncome", "Yes, with an Adult Child and higher income")], default="NoConcubinage", groups="hr.group_hr_user", tracking=True)
    l10n_ch_spouse_first_name = fields.Char(string="Spouse First Name", groups="hr.group_hr_user", tracking=True)
    l10n_ch_spouse_last_name = fields.Char(string="Spouse Last Name", groups="hr.group_hr_user", tracking=True)
    l10n_ch_spouse_birthday = fields.Date(string="Spouse Birthday", groups="hr.group_hr_user", tracking=True)
    l10n_ch_spouse_street = fields.Char(groups="hr.group_hr_user", tracking=True)
    l10n_ch_spouse_zip = fields.Char(groups="hr.group_hr_user", tracking=True, string="Spouse Residence ZIP-Code",)
    l10n_ch_spouse_city = fields.Char(string="Spouse Residence City", groups="hr.group_hr_user", tracking=True)
    l10n_ch_spouse_country_id = fields.Many2one('res.country', groups="hr.group_hr_user", tracking=True, string="Spouse Residence Country",)
    l10n_ch_spouse_revenues = fields.Boolean(string="Spouse Has Income", groups="hr.group_hr_user", tracking=True)
    l10n_ch_spouse_work_end_date = fields.Date(groups="hr.group_hr_user", tracking=True)
    l10n_ch_spouse_residence_canton = fields.Selection(string="Spouse Residence Canton", selection=CANTONS_WITH_EX, groups="hr.group_hr_user", tracking=True)
    l10n_ch_cross_border_commuter = fields.Boolean(string="Cross Border Commuter", groups="hr.group_hr_user")
    l10n_ch_foreign_tax_id = fields.Char(string="Foreign Tax-ID", groups="hr.group_hr_user", tracking=True)
    l10n_ch_cross_border_start = fields.Date(string="Cross Border Commuter Start Date", groups="hr.group_hr_user", tracking=True)

    l10n_ch_agricole_company = fields.Boolean(related="company_id.l10n_ch_agricole_company", tracking=True, groups="hr.group_hr_user")
    l10n_ch_relationship_ceo = fields.Selection(string="Degree of Relationship with the owner",
                                                selection=[("unknown", "Unknown"),
                                                           ("unrelated", "Unrelated to the owner"),
                                                           ("OwnerWife", "Wife of the owner"),
                                                           ("OwnerHusband", "Husband of the owner"),
                                                           ("OwnerBloodRelation", "Blood relative with the owner"),
                                                           ("OwnerSiblings", "Siblings with the owner"),
                                                           ("OwnerFosterChild", "Foster Child of the owner")], tracking=True, default="unknown", groups="hr.group_hr_user")

    l10n_ch_other_employment = fields.Boolean(string="Other Employment", tracking=True, groups="hr.group_hr_user")
    l10n_ch_total_activity_type = fields.Selection(string="Other Employment Details", selection=[("unknown", "Unknown"),
                                                                                                 ("percentage", "Total Percentage"),
                                                                                                 ("gross", "Total Gross Monthly Income")], default="unknown", tracking=True, groups="hr.group_hr_user")
    l10n_ch_other_activity_percentage = fields.Float(string="Total Percentage", tracking=True, groups="hr.group_hr_user")
    l10n_ch_other_activity_gross = fields.Float(string="Total Income", tracking=True, groups="hr.group_hr_user")
    l10n_ch_working_days_in_ch = fields.Float(string="Working Days in Switzerland", default=20, tracking=True, groups="hr.group_hr_user")
    l10n_ch_residence_type = fields.Selection(string="Kind of residence", selection=[("Daily", "Daily"),
                                                                                     ("Weekly", "Weekly")],
                                              default="Daily", groups="hr.group_hr_user",
                                              help="""
Daily: 
For PIS (Persons subject to Source tax) who do not have a residence or a place of stay in Switzerland, 
the registered office or permanent establishment of the company is decisive. 
This also applies notably to predefined categories (e.g., board member fees, exported employee participations, and special agreements with France).

Weekly: 
For PIS who do not have a residence but have a weekly place of stay in Switzerland, 
the canton and municipality of the weekly stay (based on the address of the weekly stay) are decisive.
""", tracking=True)
    l10n_ch_weekly_residence_canton = fields.Selection(string="Weekly Residence Canton", selection=CANTONS, compute="_compute_weekly_residence_autocomplete", store=True, readonly=False, tracking=True, groups="hr.group_hr_user")
    l10n_ch_weekly_residence_municipality = fields.Char(string="Weekly Residence Municipality", compute="_compute_weekly_residence_autocomplete", store=True, readonly=False, tracking=True, groups="hr.group_hr_user")

    l10n_ch_weekly_residence_address_street = fields.Char(string="Weekly Residence Street", tracking=True, groups="hr.group_hr_user")
    l10n_ch_weekly_residence_address_city = fields.Char(string="Weekly Residence City", compute="_compute_weekly_residence_autocomplete", store=True, readonly=False, tracking=True, groups="hr.group_hr_user")
    l10n_ch_weekly_residence_address_zip = fields.Char(string="Weekly Residence ZIP-Code", tracking=True, groups="hr.group_hr_user")

    l10n_ch_flex_profiling = fields.Char("Flex Profiling", help="""
This variable can only be provided if a prior agreement has been established between the OFS and the company as part of the Profiling process. 
It involves additional information required to account for the specific characteristics of certain companies (e.g., to define the staff included).
""", tracking=True, groups="hr.group_hr_user")

    l10n_ch_is_mutations = fields.One2many('l10n.ch.is.mutation', 'employee_id', groups="hr.group_hr_user")
    l10n_ch_salary_certificate_profiles = fields.One2many("l10n.ch.salary.certificate.profile", "employee_id", groups="hr.group_hr_user")

    l10n_ch_canton = fields.Selection(compute="_compute_autocomplete_private_address", store=True, readonly=False)
    l10n_ch_municipality = fields.Char(compute="_compute_autocomplete_private_address", store=True, readonly=False)
    private_city = fields.Char(compute="_compute_autocomplete_private_address", store=True, readonly=False)
    certificate = fields.Selection(default="mandatorySchoolOnly")
    registration_number = fields.Char(default=lambda self: str(uuid.uuid4().hex))

    @api.constrains('l10n_ch_municipality', 'l10n_ch_weekly_residence_municipality', 'private_country_id')
    def _check_swiss_address(self):
        for record in self:
            if record.private_country_id.code == 'CH':
                if record.l10n_ch_municipality and not record.l10n_ch_municipality.isdigit():
                    raise ValidationError(_('The residence Municipality must contain only numbers for Switzerland.'))
                if record.l10n_ch_weekly_residence_municipality and not record.l10n_ch_weekly_residence_municipality.isdigit():
                    raise ValidationError(_('The weekly residence municipality must contain only numbers for Switzerland.'))

    @api.depends('l10n_ch_legal_first_name', 'l10n_ch_legal_last_name')
    def _compute_legal_name(self):
        ch_employees = self.filtered(lambda e: e.company_id.country_code == 'CH')
        for employee in ch_employees:
            if employee.l10n_ch_legal_first_name and employee.l10n_ch_legal_last_name:
                employee.legal_name = f'{employee.l10n_ch_legal_first_name} {employee.l10n_ch_legal_last_name}'
            else:
                employee.legal_name = employee.name
        super(HrEmployee, self - ch_employees)._compute_legal_name()

    @api.constrains("l10n_ch_foreign_tax_id")
    def _check_l10n_ch_foreign_tax_id(self):
        pattern = r"[A-Z]{6}[0-9]{2}(A|B|C|D|E|H|L|M|P|R|S|T)[0-9]{2}[A-Z]{1}[0-9]{3}[A-Z]{1}"
        for emp in self:
            if emp.private_country_id.code == "IT" and emp.l10n_ch_foreign_tax_id:
                match = re.match(pattern, emp.l10n_ch_foreign_tax_id)
                if not match:
                    raise ValidationError(_("Invalid Italian Tax-ID pattern"))

    @api.onchange('private_country_id')
    def _onchange_private_country_id(self):
        if self.private_country_id.code != 'CH':
            self.l10n_ch_canton = "EX"
            self.l10n_ch_municipality = False

    @api.constrains('birthday')
    def _check_birthday(self):
        today = fields.Datetime.now().date()
        for employee in self:
            if employee.birthday and employee.birthday > today:
                raise ValidationError(_("Employee's Birthday cannot be greater than today."))

    def write(self, vals):
        vals = super().write(vals)
        # Recompute open payslips automatically on each update since almost all fields cause a change in computation
        pending_computation_slips = self.slip_ids.filtered(lambda p: p.state in ['draft', 'verify'] and p.struct_id.code == "CHMONTHLYELM")
        if pending_computation_slips:
            pending_computation_slips.action_refresh_from_work_entries()
        else:
            self._create_or_update_snapshot()
        return vals

    @api.depends('l10n_ch_tax_scale', 'l10n_ch_tax_scale_type', 'l10n_ch_pre_defined_tax_scale', 'l10n_ch_open_tax_scale', "children", "l10n_ch_church_tax", 'l10n_ch_has_withholding_tax')
    def _compute_l10n_ch_tax_code(self):
        for employee in self:
            if employee.l10n_ch_has_withholding_tax:
                if employee.l10n_ch_tax_scale_type == "TaxAtSourceCode" and employee.l10n_ch_tax_scale:
                    employee.l10n_ch_tax_code = f"{employee.l10n_ch_tax_scale}{max(0, min(employee.children, 9))}{'Y' if employee.l10n_ch_church_tax else 'N'}"
                elif employee.l10n_ch_tax_scale_type == "CategoryPredefined" and employee.l10n_ch_pre_defined_tax_scale:
                    employee.l10n_ch_tax_code = employee.l10n_ch_pre_defined_tax_scale
                elif employee.l10n_ch_tax_scale_type == "CategoryOpen":
                    employee.l10n_ch_tax_code = employee.l10n_ch_open_tax_scale
                else:
                    employee.l10n_ch_tax_code = False
            else:
                employee.l10n_ch_tax_code = False

    @api.depends('contract_id', 'l10n_ch_canton', 'l10n_ch_residence_type', 'l10n_ch_weekly_residence_canton', 'l10n_ch_has_withholding_tax', 'contract_id.l10n_ch_location_unit_id')
    def _compute_l10n_ch_source_tax_canton(self):
        for employee in self:
            if employee.l10n_ch_has_withholding_tax:
                if employee.l10n_ch_canton != "EX":
                    employee.l10n_ch_source_tax_canton = employee.l10n_ch_canton
                else:
                    if employee.l10n_ch_residence_type == "Daily":
                        employee.l10n_ch_source_tax_canton = employee.contract_id.l10n_ch_location_unit_id.canton
                    else:
                        employee.l10n_ch_source_tax_canton = employee.l10n_ch_weekly_residence_canton
            else:
                employee.l10n_ch_source_tax_canton = False

    @api.depends('contract_id', 'l10n_ch_canton', 'l10n_ch_residence_type', 'l10n_ch_weekly_residence_municipality', 'l10n_ch_has_withholding_tax')
    def _compute_l10n_ch_source_tax_municipality(self):
        for employee in self:
            if employee.l10n_ch_has_withholding_tax:
                if employee.l10n_ch_canton != "EX":
                    employee.l10n_ch_source_tax_municipality = employee.l10n_ch_municipality
                else:
                    if employee.l10n_ch_residence_type == "Daily":
                        employee.l10n_ch_source_tax_municipality = employee.contract_id.l10n_ch_location_unit_id.municipality
                    else:
                        employee.l10n_ch_source_tax_municipality = employee.l10n_ch_weekly_residence_municipality
            else:
                employee.l10n_ch_source_tax_municipality = False
    @api.depends("name")
    def _compute_l10n_ch_legal_name(self):
        for employee in self:
            if employee.name:
                first_name = ' '.join(re.sub(r"\([^()]*\)", "", employee.name).strip().split()[:-1])
                last_name = re.sub(r"\([^()]*\)", "", employee.name).strip().split()[-1]
                if not employee.l10n_ch_legal_last_name:
                    employee.l10n_ch_legal_last_name = last_name
                if not employee.l10n_ch_legal_first_name:
                    employee.l10n_ch_legal_first_name = first_name

    @api.model
    def _create_or_update_snapshot(self):
        swiss_employees = self.filtered(lambda e: e.company_id.country_id.code == "CH")
        if not swiss_employees:
            return

        self.env.flush_all()

        ref_date = self.env.context.get('l10n_ch_reference_date') or fields.Date.context_today(self)

        month = ref_date.month
        year = ref_date.year

        existing_snapshots = self.sudo().env["l10n.ch.employee.yearly.values"].search([
            ('year', '=', year),
            ('employee_id', 'in', swiss_employees.ids)
        ])
        snapshots_to_update = existing_snapshots.mapped('employee_id')
        snapshots_to_create = swiss_employees - snapshots_to_update
        vals = []
        for employee in snapshots_to_create:
            vals.append({
                'employee_id': employee.id,
                'year': year
            })

        if vals:
            existing_snapshots += self.env['l10n.ch.employee.yearly.values'].create(vals)

        existing_snapshots += self.env["l10n.ch.employee.yearly.values"].search([
            ('year', '>', year),
            ('employee_id', 'in', self.ids)
        ])

        unlock_pay_period = self.env.context.get('unlock_pay_period')

        # Mutation insensitive informations, these have to be updated even if the payroll month is closed
        monthly_persons_to_update = existing_snapshots.monthly_value_ids.filtered(lambda s: not s.payroll_month_closed or (s.month >= month and s.year >= year)).sorted(lambda s: (s.year, s.month))
        self.env.add_to_compute(self.env['l10n.ch.employee.monthly.values']._fields['person'], monthly_persons_to_update)
        monthly_persons_to_update._recompute_recordset(['person'])

        # Mutation sensitive informations, these should not be recomputed once payroll month is closed
        monthly_values_to_update = existing_snapshots.monthly_value_ids.filtered(lambda s: not s.payroll_month_closed or (s.month >= month and s.year >= year and unlock_pay_period)).sorted(lambda s: (s.year, s.month))

        if self.env.context.get('update_salaries'):
            self.env.add_to_compute(self.env['l10n.ch.employee.monthly.values']._fields['bvg_lpp_annual_basis'], monthly_values_to_update)
            monthly_values_to_update._recompute_recordset(['bvg_lpp_annual_basis'])

        self.env.add_to_compute(self.env['l10n.ch.employee.monthly.values']._fields['employee_meta_data'], monthly_values_to_update)
        self.env.add_to_compute(self.env['l10n.ch.employee.monthly.values']._fields['additional_particular'], monthly_values_to_update)
        monthly_values_to_update._recompute_recordset(['employee_meta_data', 'additional_particular'])

        self.env.add_to_compute(self.env['l10n.ch.employee.monthly.values']._fields['lpp_mutations'], monthly_values_to_update)
        self.env.add_to_compute(self.env['l10n.ch.employee.monthly.values']._fields['is_mutations'], monthly_values_to_update)
        monthly_values_to_update._recompute_recordset(['lpp_mutations', 'is_mutations'])

        self.env.add_to_compute(self.env['l10n.ch.employee.monthly.values']._fields['monthly_statistics'], monthly_values_to_update)
        monthly_values_to_update._recompute_recordset(['monthly_statistics'])

        existing_snapshots._toggle_pay_period_lock()

    def action_absence_swiss_employee(self):
        return {
            'name': _('Absences'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave',
            'views': [[self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_leave_employee_view_dashboard').id, 'calendar']],
            'domain': [('employee_id', 'in', self.ids)],
            'context': {
                'employee_id': self.ids,
            },
        }

    def action_view_wages(self):
        self.ensure_one()
        if self.contract_id:
            return self.contract_id.action_view_wages()
        else:
            raise UserError(_("Oops, this employee has no contract yet."))

    def action_open_contract(self):
        self.ensure_one()
        action = super().action_open_contract()
        action['target'] = 'current'
        return action

    @api.depends('private_zip')
    def _compute_autocomplete_private_address(self):
        ZIP_DATA = self.env['hr.rule.parameter']._get_parameter_from_code("l10n_ch_bfs_municipalities", fields.Date.today(), raise_if_not_found=False)
        if ZIP_DATA:
            for record in self:
                if record.private_zip:
                    data = ZIP_DATA.get(record.private_zip)
                    if data:
                        record.private_city = data[0]
                        record.l10n_ch_municipality = data[1]
                        record.l10n_ch_canton = data[2]

    @api.depends('l10n_ch_weekly_residence_address_zip')
    def _compute_weekly_residence_autocomplete(self):
        ZIP_DATA = self.env['hr.rule.parameter']._get_parameter_from_code("l10n_ch_bfs_municipalities", fields.Date.today(), raise_if_not_found=False)
        if ZIP_DATA:
            for record in self:
                if record.l10n_ch_weekly_residence_address_zip:
                    data = ZIP_DATA.get(record.l10n_ch_weekly_residence_address_zip)
                    if data:
                        record.l10n_ch_weekly_residence_address_city = data[0]
                        record.l10n_ch_weekly_residence_municipality = data[1]
                        record.l10n_ch_weekly_residence_canton = data[2]
