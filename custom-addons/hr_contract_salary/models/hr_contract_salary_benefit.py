# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrContractSalaryBenefit(models.Model):
    _name = 'hr.contract.salary.benefit'
    _description = 'Salary Package Benefit'
    _order = 'sequence'

    def _get_field_domain(self):
        fields_ids = self.env['hr.contract']._get_benefit_fields(triggers=False)
        return [
            ('model', '=', 'hr.contract'),
            ('name', 'in', fields_ids),
            ('ttype', 'not in', ('one2many', 'many2one', 'many2many'))]

    def _get_binary_field_domain(self):
        return [
            ('model', '=', 'hr.contract'),
            ('ttype', '=', 'binary')]

    def _get_public_field_names(self):
        return [(field.id, field.field_description) for field in self.sudo().env['ir.model.fields']\
            .search(self._get_field_domain())]

    name = fields.Char(translate=True)
    show_name = fields.Boolean(string="Show Name", default=True, help='Whether the name should be displayed in the Salary Configurator')
    active = fields.Boolean(default=True)
    res_field_id = fields.Many2one(
        'ir.model.fields', string="Benefit Field", domain=_get_field_domain, ondelete='cascade', required=False,
        help='Contract field linked to this benefit')
    cost_res_field_id = fields.Many2one(
        'ir.model.fields', string="Cost Field", domain=_get_field_domain, ondelete='cascade',
        help="Contract field linked to this benefit cost. If not set, the benefit won't be taken into account when computing the employee budget.")
    # LUL rename into field and cost_field to be consistent with fold_field and manual_field?
    res_field_public = fields.Selection(
        selection="_get_public_field_names",
        string="Benefit Field",
        readonly=False,
        compute="_compute_res_field_public",
        inverse="_inverse_res_field_public"
    )
    cost_res_field_public = fields.Selection(
        selection="_get_public_field_names",
        string="Cost Field",
        readonly=False,
        compute="_compute_cost_res_field_public",
        inverse="_inverse_cost_res_field_public"
    )
    field = fields.Char(related="res_field_id.name", readonly=True)
    cost_field = fields.Char(related="cost_res_field_id.name", string="Cost Field Name", readonly=True, compute_sudo=True)
    sequence = fields.Integer(default=100)
    benefit_type_id = fields.Many2one(
        'hr.contract.salary.benefit.type', required=True, string="Related Type",
        default=lambda self: self.env.ref('hr_contract_salary.l10n_be_monthly_benefit', raise_if_not_found=False))
    benefit_ids = fields.Many2many(
        'hr.contract.salary.benefit', 'hr_contract_salary_benefit_rel', 'benefit_ids', 'mandatory_benefit_ids',
        help='All benefits in this field need to be selected, as a condition for the current one to be editable. Before edition, the current benefit is always set to false.',
        string="Mandatory Benefits", domain="[('id', '!=', id)]")
    folded = fields.Boolean()
    fold_label = fields.Char(translate=True)
    fold_res_field_id = fields.Many2one(
        'ir.model.fields', domain=_get_field_domain, ondelete='cascade',
        help='Contract field used to fold this benefit.')
    fold_field = fields.Char(related='fold_res_field_id.name', string="Fold Field Name", readonly=True)
    manual_res_field_id = fields.Many2one(
        'ir.model.fields', domain=_get_field_domain, ondelete='cascade',
        help='Contract field used to manually encode an benefit value.')
    manual_field = fields.Char(related='manual_res_field_id.name', string="Manual Field Name", readonly=True)
    country_id = fields.Many2one('res.country')
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type", required=True)
    icon = fields.Char()
    display_type = fields.Selection(selection=[
        ('always', 'Always Selected'),
        ('dropdown', 'Dropdown'),
        ('dropdown-group', 'Dropdown Group'),
        ('slider', 'Slider'),
        ('radio', 'Radio Buttons'),
        ('manual', 'Manual Input'),
        ('text', 'Text'),
    ])
    impacts_net_salary = fields.Boolean(default=True)
    description = fields.Html('Description', translate=True)
    slider_min = fields.Float()
    slider_max = fields.Float()
    slider_step = fields.Integer(default=1)
    value_ids = fields.One2many('hr.contract.salary.benefit.value', 'benefit_id')
    hide_description = fields.Boolean(help="Hide the description if the benefit is not taken.")
    requested_documents_field_ids = fields.Many2many('ir.model.fields', domain=_get_binary_field_domain, string="Requested Documents")
    requested_documents_fields_string = fields.Text('Requested Documents', compute="_compute_requested_fields_string", readonly=True)
    requested_documents = fields.Char(compute='_compute_requested_documents', string="Requested Documents Fields", compute_sudo=True)
    has_admin_access = fields.Boolean(compute='_compute_has_admin_access')

    uom = fields.Selection([
        ('days', 'Days'),
        ('percent', 'Percent'),
        ('currency', 'Currency')], string="Unit of Measure", default='currency')

    activity_type_id = fields.Many2one('mail.activity.type', string='Activity Type', help="The type of activity that will be created automatically on the contract if this benefit is chosen by the employee.")
    activity_creation = fields.Selection([
        ('running', 'Employee signs his contract'),
        ('countersigned', 'Contract is countersigned')], default='running',
        help='Choose when the activity is created:\n'
             '- Employee signs his contract: Activity is created as soon as the employee signed the contract\n'
             '- Contract is countersigned: HR responsible have signed the contract and conclude the process.')
    activity_creation_type = fields.Selection([
        ('always', 'When the benefit is set'),
        ('onchange', 'When the benefit is modified')], default='always',
        help='Define when the system creates a new activity:\n'
             '- When the benefit is set: Unique creation the first time the employee will take the benefit\n'
             '- When the benefit is modified: Activity will be created for each change regarding the benefit.')
    activity_responsible_id = fields.Many2one('res.users', 'Assigned to')
    sign_template_id = fields.Many2one('sign.template', string="Template to Sign", help="Documents selected here will be requested to the employee for additional signatures related to the benefit. eg: A company car policy to approve if you choose a company car.")
    sign_copy_partner_id = fields.Many2one('res.partner', string="Send a copy to", help="Email address to which to transfer the signature.")
    sign_frenquency = fields.Selection([
        ('onchange', 'When the benefit is set'),
        ('always', 'When the benefit is modified')], string="Sign Creation Type", default="onchange",
        help='Define when the system creates a new sign request:\n'
             '- When the benefit is set: Unique signature request the first time the employee will take the benefit\n'
             '- When the benefit is modified: Signature request will be created for each change regarding the benefit.')

    _sql_constraints = [
        (
            'required_fold_res_field_id',
            'check (folded = FALSE OR (folded = TRUE AND fold_res_field_id IS NOT NULL))',
            'A folded field is required'
        )
    ]

    @api.depends('res_field_id')
    def _compute_res_field_public(self):
        for record in self:
            record.res_field_public = record.res_field_id.id

    @api.depends('cost_res_field_id')
    def _compute_cost_res_field_public(self):
        for record in self:
            record.cost_res_field_public = record.cost_res_field_id.id

    def _inverse_res_field_public(self):
        for record in self:
            record.res_field_id = self.sudo().env['ir.model.fields'].browse(record.res_field_public)

    def _inverse_cost_res_field_public(self):
        for record in self:
            record.cost_res_field_id = self.sudo().env['ir.model.fields'].browse(record.cost_res_field_public)

    @api.depends_context('lang')
    @api.depends('requested_documents_field_ids')
    def _compute_requested_fields_string(self):
        self.requested_documents_fields_string = False
        for record in self:
            if record.requested_documents_field_ids:
                record.requested_documents_fields_string = ', '.join([f.field_description for f in record.sudo().requested_documents_field_ids])

    @api.depends('requested_documents_field_ids')
    def _compute_requested_documents(self):
        names = []
        for benefit in self:
            benefit.requested_documents = ','.join(benefit.requested_documents_field_ids.mapped('name'))
            names.extend(benefit.requested_documents_field_ids.mapped('name'))
        self._set_requested_documents_as_required(names)

    def _set_requested_documents_as_required(self, names):
        personal_infos = self.env['hr.contract.salary.personal.info'].search([('field', 'in', names)])
        if personal_infos:
            personal_infos.is_required = True

    @api.depends_context('uid')
    def _compute_has_admin_access(self):
        self.has_admin_access = self.env.user._is_system()

    @api.constrains('slider_min', 'slider_max')
    def _check_min_inferior_to_max(self):
        for record in self:
            if record.display_type == 'slider' and record.slider_min > record.slider_max:
                raise ValidationError(_('The minimum value for the slider should be inferior to the maximum value.'))

    @api.constrains('display_type', 'res_field_id')
    def _check_min_inferior_to_max(self):
        for record in self:
            if not record.res_field_id and record.display_type != 'always':
                raise ValidationError(_('Benefits that are not linked to a field should always be displayed.'))

class HrContractSalaryBenefitType(models.Model):
    _name = 'hr.contract.salary.benefit.type'
    _description = 'Contract Benefit Type'
    _order = 'sequence'

    name = fields.Char()
    periodicity = fields.Selection([
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ], default='monthly')
    sequence = fields.Integer(default=100)


class HrContractSalaryBenefitValue(models.Model):
    _name = 'hr.contract.salary.benefit.value'
    _description = 'Contract Benefit Value'
    _order = 'sequence'

    name = fields.Char(translate=True)
    sequence = fields.Integer(default=100)
    benefit_id = fields.Many2one('hr.contract.salary.benefit')
    value = fields.Float()
    color = fields.Selection(selection=[
        ('green', 'Green'),
        ('red', 'Red')], string="Color", default="green")
    hide_description = fields.Boolean()

    display_type = fields.Selection([
            ('line', 'Line'),
            ('section', 'Section'),
        ],
        default='line',
    )
