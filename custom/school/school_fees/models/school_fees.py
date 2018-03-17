import time
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class SchoolFeesRegister(models.Model):
    # School fees Register
    _name = 'school.fees.register'
    _description = 'School fees Register'
    _order = "state desc"
    _rec_name = 'reference_number'

    @api.multi
    @api.depends('structure_ids', 'slip_lines')
    def _amount_paid(self):
        # Method to compute total amount paid
        for rec in self:
            if rec.slip_lines:
                total_amt = 0.0
                for line in rec.slip_lines:
                    if line.state == 'confirm':
                        total_amt += line.amount
                rec.amount_paid = total_amt

    @api.multi
    @api.depends('structure_ids')
    def _total_fee(self):
        # Method to compute total school fee# 
        for rec in self:
            total_amt = 0.0
            for line in rec.fees_structure_id.structure_ids:
                total_amt += line.amount
            rec.total_fee = total_amt

    @api.multi
    @api.depends('amount_paid', 'total_fee')
    def _amount_remain(self):
        # Method to compute total amount# 
        for rec in self:
            rec.amount_remain = rec.total_fee - rec.amount_paid

    @api.model
    def create(self, vals):
        student_pid = self.env['school.student'].search([('id', '=', vals['student_id'])]).pid
        structure_code = self.env['student.fees.structure'].search([('id', '=', vals['fees_structure_id'])]).code
        vals['unique_reference'] = str(student_pid)+str(structure_code)
        result = super(SchoolFeesRegister, self).create(vals)
        return result

    @api.multi
    def unlink(self):
        if self.state in ['progress', 'complete']:
            raise ValidationError("Cannot Delete a Fee Register that's in progress or completed")
        return super(SchoolFeesRegister, self).unlink()

    unique_reference = fields.Char('Unique Reference', readonly=True)
    student_id = fields.Many2one('school.student', 'Student', required=True)
    form_id = fields.Many2one('school.form', 'Form', related='student_id.form_id')
    date = fields.Date('Date', required=True,
                       help="Date of payment",
                       default=lambda * a: time.strftime('%Y-%m-%d'))
    reference_number = fields.Char('Reference Number', readonly=True,
                                   default=lambda obj: obj.env['ir.sequence'].
                                   next_by_code('school.fees.register'))
    structure_ids = fields.One2many('student.fees.structure.line', 'register_id',
                                    'Fees Structure', related='fees_structure_id.structure_ids')
    total_fee = fields.Float("Total Fee", compute="_total_fee",
                             store=True, readonly=True)
    amount_paid = fields.Float("Amount Paid", compute="_amount_paid",
                               store=True, readonly=True)
    amount_remain = fields.Float("Amount Remaining", compute="_amount_remain",
                                 store=True, readonly=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('progress', 'In Progress'),
                              ('complete', 'Fully Paid')],
                             'State',
                             readonly=True,
                             default='draft')
    academic_year_id = fields.Many2one('school.academic.year', 'Academic Year', default=lambda self: self.env.user.company_id.current_academic_year, required=True)

    fees_structure_id = fields.Many2one('student.fees.structure', 'Fees Structure',
                                        required=True,
                                        compute='_compute_fee_structure',
                                        store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', related='fees_structure_id.currency_id', readonly=True)
    slip_lines = fields.One2many('school.fees.slips', 'register_id', 'School Fee Slips')
    _sql_constraints = [('unique_reference_uniq', 'unique(unique_reference)',
                         'Error! You cant add a fee register for a student who '
                         'already has an existing register for this academic year and fee structure'),
                        ]

    @api.depends('student_id')
    def _compute_fee_structure(self):
        domain = ([('academic_year_id', '=', self.student_id.academic_year_id.id)])
        structures = self.env['student.fees.structure'].search(domain)
        if self.student_id.school_type == 'primary':
            for struc in structures:
                if self.student_id.class_id.id in [clas.id for clas in struc.related_classes]:
                    self.fees_structure_id = struc

        if self.student_id.school_type == 'secondary':
            for struc in structures:
                if self.student_id.form_id.id in [form.id for form in struc.related_classes]:
                    self.fees_structure_id = struc

    @api.multi
    def fees_register_draft(self):
        # Changes the state to draft# 
        for rec in self:
            rec.slip_lines = False
            rec.state = 'draft'
        return True

    @api.multi
    def fees_in_progress(self):
        # Method to change payslip to in progress# 
        for rec in self:
            rec.write({'state': 'progress'})

    @api.multi
    def fees_register_confirm(self):
        # Method to confirm payslip# 
        for rec in self:
            if rec.amount_paid >= rec.total_fee:
                rec.write({'state': 'complete'})
            else:
                raise ValidationError(_('You can only change state to Fully paid upon full payment'))
        return True


class StudentFeesSlip(models.Model):
    # Student Fees Structure Line# 
    _name = 'school.fees.slips'
    _description = 'School Fee Slips'

    paid_by = fields.Char('Paid by', required=True)
    phone_no = fields.Char('Contact #')
    date = fields.Date('Date', required=True)
    amount = fields.Float('Amount', digits=(16, 2), required=True)
    bank_slip_no = fields.Char('Bank Slip number', required=True)
    register_id = fields.Many2one('school.fees.register')
    student_id = fields.Many2one('school.student', 'Student', related='register_id.student_id', required=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirmed')],
                             string='State', default='draft')

    @api.multi
    def confirm(self):
        self.ensure_one()
        for rec in self:
            rec.write({'state': 'confirm'})
            rec.register_id._amount_paid()

    @api.multi
    def draft(self):
        self.ensure_one()
        for rec in self:
            rec.write({'state': 'draft'})
            rec.register_id._amount_paid()


class StudentFeesStructureLine(models.Model):
    # Student Fees Structure Line# 
    _name = 'student.fees.structure.line'
    _description = 'Student Fees Structure Line'
    _order = 'sequence'

    name = fields.Char('Name', required=True)
    amount = fields.Float('Amount', digits=(16, 2), required=True)
    sequence = fields.Integer('Sequence')
    structure_id = fields.Many2one('student.fees.structure')
    register_id = fields.Many2one('school.fees.register')
    currency_id = fields.Many2one('res.currency', 'Currency', related='structure_id.currency_id', readonly=True)


class SchoolClass(models.Model):
    _inherit = 'school.class'
    structure_ids = fields.Many2many('student.fees.structure', string='Fees Structure')


class SchoolForm(models.Model):
    _inherit = 'school.form'
    structure_ids = fields.Many2many('student.fees.structure', string='Fees Structure')


class StudentFeesStructure(models.Model):
    # Fees structure# 
    _name = 'student.fees.structure'
    _description = 'Student Fees Structure'

    @api.multi
    @api.depends('structure_ids')
    def _compute_total(self):
        for rec in self:
            total = 0.0
            for struc in rec.structure_ids:
                total += struc.amount
            rec.total = total

    name = fields.Char('Name', required=True, compute='_compute_name')
    code = fields.Char('Code', readonly=True, default=lambda obj: obj.env['ir.sequence'].
                       next_by_code('student.fees.structure'))
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda obj: obj.env.user.company_id.currency_id)
    academic_year_id = fields.Many2one('school.academic.year', 'Academic Year', required=True)
    structure_ids = fields.One2many('student.fees.structure.line', 'structure_id', 'Structures')
    total = fields.Float('Amount', digits=(16, 2), compute='_compute_total')
    related_classes = fields.Many2many('school.class', string='Classes')
    related_forms = fields.Many2many('school.form', string='Forms')
    school_type = fields.Selection([('primary', 'Primary'),
                                    ('secondary', 'Secondary')],
                                   default=lambda obj: obj.env.user.company_id.school_type,
                                   required=True,
                                   readonly=True
                                   )

    _sql_constraints = [('code_uniq', 'unique(code)',
                         'The code of the Fees Structure must'
                         'be unique !'), ('name_uniq', 'unique(name)',
                                          'The Name of the Fees Structure must '
                                          'be unique !'),
                        ]

    @api.depends('related_classes', 'related_forms')
    def _compute_name(self):
        for rec in self:
            if rec.related_classes:
                classes = rec.related_classes.sorted(key='id')
                y = ''
                for x in classes:
                    y += x.class_name+' '
                    rec.name = "Fee Structure for "+y
            if rec.related_forms:
                forms = rec.related_forms.sorted(key='id')
                y = ''
                for x in forms:
                    y += x.form_name+' '
                    rec.name = "Fee Structure for "+y
