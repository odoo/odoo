from base64 import b64encode
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class HrExportMixin(models.AbstractModel):
    _name = 'hr.export.mixin'
    _description = 'HR Export Mixin'

    @api.model
    def _country_restriction(self):
        return False

    @api.model
    def default_get(self, fields):
        country_restriction = self._country_restriction()
        if country_restriction and country_restriction not in self.env.companies.mapped('country_id.code'):
            raise UserError(self.env._(
                'You must be logged in a %(country_code)s company to use this feature',
                country_code=country_restriction
            ))
        return super().default_get(fields)

    def _get_company_domain(self):
        domain = Domain('id', 'in', self.env.companies.ids)
        if restriction := self._country_restriction():
            domain &= Domain('country_id.code', '=', restriction)
        return domain

    period_start = fields.Date('Period Start', compute='_compute_period_dates', store=True, readonly=False)
    period_stop = fields.Date('Period Stop', compute='_compute_period_dates', store=True, readonly=False)
    export_file = fields.Binary('Export File', readonly=True)
    export_filename = fields.Char('Export Filename', readonly=True)
    company_id = fields.Many2one(
        'res.company', domain=lambda self: self._get_company_domain(),
        default=lambda self: self.env.company, required=True)
    eligible_employee_line_ids = fields.One2many(
        'hr.export.employee.mixin', 'export_id',
        string='Eligible Employees')
    eligible_employee_count = fields.Integer(
        '#Employees', compute='_compute_eligible_employee_count')
    creation_date = fields.Date(
        string="Creation Date",
        compute="_compute_creation_date",
        store=False,
    )
    create_uid = fields.Many2one('res.users', index=True)

    @api.depends('eligible_employee_line_ids')
    def _compute_eligible_employee_count(self):
        for export in self:
            export.eligible_employee_count = len(export.eligible_employee_line_ids)

    def _compute_period_dates(self):
        for export in self:
            export.period_start = fields.Date.today().replace(day=1)
            export.period_stop = export.period_start + relativedelta(months=1, days=-1)

    def _compute_creation_date(self):
        for rec in self:
            rec.creation_date = rec.create_date.date() if rec.create_date else False

    def action_export_file(self):
        self.ensure_one()
        self._check_before_export()
        file_content = self._generate_export_file()
        filename = self._generate_export_filename()
        self.write({
            "export_file": b64encode(file_content),
            "export_filename": filename,
        })

    def _check_before_export(self):
        return True

    def _generate_export_file(self):
        raise NotImplementedError()

    def _generate_export_filename(self):
        raise NotImplementedError()

    def action_open_employees(self):
        self.ensure_one()
        return {
            'name': self.env._("Eligible Employees"),
            'type': "ir.actions.act_window",
            'res_model': self.eligible_employee_line_ids._name,
            'view_mode': "list",
            'domain': [('id', 'in', self.eligible_employee_line_ids.ids)],
            'context': dict(self.env.context, default_export_id=self.id),
        }

    def action_populate(self):
        raise NotImplementedError()


class HrExportEmployeeMixin(models.AbstractModel):
    _name = 'hr.export.employee.mixin'
    _description = 'HR Export Employee'

    export_id = fields.Many2one('hr.export.mixin', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='export_id.company_id', store=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', check_company=True)
