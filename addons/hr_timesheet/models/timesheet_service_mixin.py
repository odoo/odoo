# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TimesheetServiceParentMixin(models.AbstractModel):
    _name = 'timesheet.parent.service.mixin'
    _description = 'Timesheet Parent Document'

    allow_timesheets = fields.Boolean("Allow timesheets", default=True, help="Enable timesheeting")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False, ondelete='set null',
        help="Analytic account to which this project is linked for financial management."
             "Use an analytic account to record cost and revenue on your project.")

    @api.onchange('analytic_account_id')
    def _onchange_analytic_account(self):
        if not self.analytic_account_id and self._origin:
            self.allow_timesheets = False

    @api.constrains('allow_timesheets', 'analytic_account_id')
    def _check_allow_timesheet(self):
        """ Can not be done is SQL beacause the default value of `allow_timesheet` is True """
        for record in self:
            if record.allow_timesheets and not record.analytic_account_id:
                raise ValidationError(_('To allow timesheet, your %s %s should have an analytic account set.' % (record._description, record.display_name,)))

    # ---------------------------------------------------------
    # CRUD and ORM Methods
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, list_values):
        """ Create an analytic account if record allow timesheet and don't provide one
            Note: create it before calling super() to avoid raising the ValidationError from _check_allow_timesheet
        """
        default_allow_timesheet = self.default_get(['allow_timesheets'])['allow_timesheets']
        for values in list_values:
            allow_timesheets = values['allow_timesheets'] if 'allow_timesheets' in values else default_allow_timesheet
            if allow_timesheets and not values.get('analytic_account_id'):
                analytic_account_values = self._create_analytic_account_convert_values(values)
                analytic_account = self.env['account.analytic.account'].create(analytic_account_values)
                values['analytic_account_id'] = analytic_account.id
        return super(TimesheetServiceParentMixin, self).create(list_values)

    @api.multi
    def write(self, values):
        # create the AA for record still allowing timesheet
        if values.get('allow_timesheets'):
            for record in self:
                if not record.analytic_account_id and not values.get('analytic_account_id'):
                    record._create_analytic_account()
        result = super(TimesheetServiceParentMixin, self).write(values)
        return result

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    def _create_analytic_account_convert_values(self, values):
        """ Extract value to create an analytic account from the `create` value of the record
            implementing the timesheet.parent.service.mixin
        """
        return {
            'name': values.get(self._rec_name, _('Unknown Analytic Account')),
        }

    @api.model
    def _init_data_analytic_account(self):
        self.search([('analytic_account_id', '=', False), ('allow_timesheets', '=', True)])._create_analytic_account()

    def _create_analytic_account(self):
        for record in self:
            values = record._create_analytic_account_prepare_values()
            analytic_account = self.env['account.analytic.account'].create(values)
            record.write({'analytic_account_id': analytic_account.id})

    def _create_analytic_account_prepare_values(self):
        """ Retrun the value required to create an analytic account from an existing record
            inheriting the parent.service.mixin
        """
        return {
            'name': self.display_name,
        }


class TimesheetServiceMixin(models.AbstractModel):
    _name = 'timesheet.service.mixin'
    _description = 'Timesheet Document'
    _timesheet_service_parent_field = 'project_id'

    timesheet_service_id = fields.Many2one('timesheet.service', string="Service")
    analytic_account_id = fields.Many2one('account.analytic.account', related='timesheet_service_id.analytic_account_id')

    # ---------------------------------------------------------
    # CRUD Methods
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, list_values):
        # get a map for project_id --> analytic_account_id
        parent_analytic_account_map = self._service_create_find_analytic_account(list_values)

        service_value_list = []
        service_parent_index = {}
        for index, vals in enumerate(list_values):
            if vals.get('project_id') and parent_analytic_account_map.get(vals['project_id']):
                service_value_list.append({
                    'name': vals.get(self._rec_name, "Unknown Service"),
                    'analytic_account_id': vals.get('analytic_account_id') or parent_analytic_account_map.get(vals['project_id']),
                    'res_model': self._name,
                })
                service_parent_index[index] = len(service_value_list) - 1

        services = self.env['timesheet.service'].create(service_value_list)

        for index, vals in enumerate(list_values):
            if service_parent_index.get(index):
                vals['timesheet_service_id'] = services[service_parent_index.get(index)].id

        return super(TimesheetServiceMixin, self).create(list_values)

    def write(self, values):
        # TODO JEM: should we change this method ?
        return super(TimesheetServiceMixin, self).write(values)

    # ---------------------------------------------------------
    # Business/Helpers Methods
    # ---------------------------------------------------------

    def _service_create(self):
        list_values = []
        for record in self:
            list_values.append(record._service_prepare_values())
        self.env['timesheet.service'].create(list_values)

    def _service_prepare_values(self):
        return {
            'name': self.display_name,
            'res_model': self._name,
            'analytic_account_id': self[self._timesheet_service_parent_field].analytic_account_id.id
        }

    def _service_create_find_analytic_account(self, list_values):
        parent_field_name = self._timesheet_service_parent_field
        parent_res_model = self._fields[parent_field_name].comodel_name

        parent_ids = [vals[parent_field_name] for vals in list_values if vals.get(parent_field_name)]
        parent_analytic_account_map = {record.id: record.analytic_account_id.id for record in self.env[parent_res_model].browse(parent_ids)}

        return parent_analytic_account_map
