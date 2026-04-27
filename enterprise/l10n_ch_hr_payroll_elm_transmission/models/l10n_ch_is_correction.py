# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from .hr_employee import CANTONS

class L10nCHISMutationLine(models.Model):
    _inherit = 'hr.employee.is.line'
    _description = 'IS Entry / Withdrawals / Mutations'

    active = fields.Boolean(default=True)
    state = fields.Selection(selection=[("draft", "Draft"),
                                        ("pending", "Pending Correction"),
                                        ("confirmed", "Confirmed")], default="draft")
    correction_type = fields.Selection(selection=[("dpi", "Correction by the DPI"),
                                                  ("aci", "Correction by the ACI")], default="dpi", required=True)
    valid_as_of = fields.Date(required=False)
    correction_date = fields.Date(required=False)

    correction_method = fields.Selection(selection=[('auto', 'Automatic'),
                                                    ('manual', 'Manual')], default="auto", required=True, help="""
Pick wheter this correction should be performed automatically based on current employee information, or if you wish to enter all source tax values manually
""")

    payslips_to_correct = fields.Many2many('hr.payslip', readonly=False)
    is_ema_ids = fields.One2many("l10n.ch.is.mutation", "is_correction_id")
    manual_correction_ids = fields.One2many('hr.employee.is.line.correction', 'is_correction_id')
    is_log_line_ids = fields.One2many("hr.payslip.is.log.line", "is_correction_id")

    @api.depends('employee_id', 'reason')
    def _compute_display_name(self):
        for corr in self:
            corr.display_name = f"{corr.reason} - {corr.employee_id.name}"

    def action_pending(self):
        self.write({
            'state': 'pending'
        })

    def action_draft(self):
        self.write({
            'state': 'draft'
        })

    def action_done(self):
        self.write({
            'state': 'confirmed'
        })


class L10nCHIsCorrectionLine(models.Model):
    _name = "hr.employee.is.line.correction"
    _description = "Source-Tax Manual Correction"

    is_correction_id = fields.Many2one('hr.employee.is.line', required=True)
    employee_id = fields.Many2one(related='is_correction_id.employee_id')
    state = fields.Selection(related='is_correction_id.state')
    payslip_id = fields.Many2one('hr.payslip', required=True, domain="[('employee_id', '=', employee_id), ('state', 'in', ['done', 'paid'])]", help="Payslip you wish to correct")
    l10n_ch_tax_scale_type = fields.Selection(string="Tax Scale Type", required=True, selection=lambda self: self.env['hr.employee']._fields['l10n_ch_tax_scale_type']._description_selection(self.env))
    l10n_ch_tax_scale = fields.Selection(string="Tax Scale", selection=lambda self: self.env['hr.employee']._fields['l10n_ch_tax_scale']._description_selection(self.env))
    l10n_ch_pre_defined_tax_scale = fields.Selection(string="Predefined Tax Scale", selection=lambda self: self.env['hr.employee']._fields['l10n_ch_pre_defined_tax_scale']._description_selection(self.env))
    children = fields.Integer(string="Children Deduction")
    l10n_ch_open_tax_scale = fields.Char(string="Open Tax Scale")
    l10n_ch_church_tax = fields.Boolean(string="Church Tax")
    l10n_ch_source_tax_canton = fields.Selection(selection=CANTONS, compute="_compute_default_is_values", store=True, readonly=False, string="Source-Tax Canton")
    l10n_ch_source_tax_municipality = fields.Char(string="Source-Tax Municipality", required=True)

    insurance_days = fields.Float(compute="_compute_default_is_values", store=True, readonly=False)
    worked_days = fields.Float(compute="_compute_default_is_values", store=True, readonly=False)
    worked_days_in_switzerland = fields.Float(compute="_compute_default_is_values", store=True, readonly=False)
    source_tax_salary = fields.Float(compute="_compute_default_is_values", store=True, readonly=False)
    source_tax_periodic_determinant_salary = fields.Float(compute="_compute_default_is_values", store=True, readonly=False)
    source_tax_aperiodic_determinant_salary = fields.Float(compute="_compute_default_is_values", store=True, readonly=False)
    rate_determinant_salary = fields.Float(compute="_compute_default_is_values", store=True, readonly=False)
    source_tax_amount = fields.Float(compute="_compute_default_is_values", store=True, readonly=False)

    tax_code = fields.Char(string="Correction Source-Tax Code", compute="_compute_l10n_ch_tax_code")

    @api.depends('payslip_id')
    def _compute_default_is_values(self):
        for correction in self:
            log_lines = correction.payslip_id._get_is_log_lines(compute_total=True)["total"]
            for canton in log_lines:
                if log_lines[canton]['ASDAYS'] > 0:
                    correction.insurance_days = log_lines[canton]['ASDAYS']
                    correction.worked_days = log_lines[canton]['ISWORKEDDAYS']
                    correction.worked_days_in_switzerland = log_lines[canton]['ISWORKEDDAYSINCH']
                    correction.source_tax_salary = log_lines[canton]['ISSALARY']
                    correction.source_tax_periodic_determinant_salary = log_lines[canton]['ISDTSALARYPERIODIC']
                    correction.source_tax_aperiodic_determinant_salary = log_lines[canton]['ISDTSALARYAPERIODIC']
                    correction.rate_determinant_salary = log_lines[canton]['ISDTSALARY']
                    correction.source_tax_amount = log_lines[canton]['IS']
                    correction.source_tax_salary = log_lines[canton]['ISSALARY']
                    correction.l10n_ch_source_tax_canton = canton
                    break

    @api.depends('l10n_ch_tax_scale', 'l10n_ch_tax_scale_type', 'l10n_ch_pre_defined_tax_scale', 'l10n_ch_open_tax_scale', "children", "l10n_ch_church_tax")
    def _compute_l10n_ch_tax_code(self):
        for correction in self:
            if correction.l10n_ch_tax_scale_type == "TaxAtSourceCode" and correction.l10n_ch_tax_scale:
                correction.tax_code = f"{correction.l10n_ch_tax_scale}{max(0, min(correction.children, 9))}{'Y' if correction.l10n_ch_church_tax else 'N'}"
            elif correction.l10n_ch_tax_scale_type == "CategoryPredefined" and correction.l10n_ch_pre_defined_tax_scale:
                correction.tax_code = correction.l10n_ch_pre_defined_tax_scale
            elif correction.l10n_ch_tax_scale_type == "CategoryOpen":
                correction.tax_code = correction.l10n_ch_open_tax_scale
            else:
                correction.tax_code = False
