# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class HrEmployeePublic(models.Model):
    _name = "hr.employee.public"
    _inherit = ["hr.employee.base"]
    _description = 'Public Employee'
    _order = 'name'
    _auto = False
    _log_access = True # Include magic fields

    # Fields coming from hr.employee.base
    create_date = fields.Datetime(readonly=True)
    name = fields.Char(readonly=True)
    active = fields.Boolean(readonly=True)
    department_id = fields.Many2one(readonly=True)
    job_id = fields.Many2one(readonly=True)
    job_title = fields.Char(readonly=True)
    company_id = fields.Many2one(readonly=True)
    address_id = fields.Many2one(readonly=True)
    mobile_phone = fields.Char(readonly=True)
    work_phone = fields.Char(readonly=True)
    work_email = fields.Char(readonly=True)
    work_location = fields.Char(readonly=True)
    user_id = fields.Many2one(readonly=True)
    resource_id = fields.Many2one(readonly=True)
    resource_calendar_id = fields.Many2one(readonly=True)

    # hr.employee.public specific fields
    child_ids = fields.One2many('hr.employee.public', 'parent_id', string='Direct subordinates', readonly=True)
    image = fields.Binary("Photo", compute='_compute_image', readonly=True, compute_sudo=True)
    image_medium = fields.Binary("Medium-sized photo", compute='_compute_image', readonly=True, compute_sudo=True)
    image_small = fields.Binary("Small-sized photo", compute='_compute_image', readonly=True, compute_sudo=True)
    parent_id = fields.Many2one('hr.employee.public', 'Manager', readonly=True)
    coach_id = fields.Many2one('hr.employee.public', 'Coach', readonly=True)

    def _compute_image(self):
        for employee in self:
            # We have to be in sudo to have access to the images
            employee_id = self.sudo().env['hr.employee'].browse(employee.id)
            employee.image = employee_id.image
            employee.image_medium = employee_id.image_medium
            employee.image_small = employee_id.image_small

    @api.model
    def _get_fields(self):
        return ','.join('emp.%s' % name for name, field in self._fields.items() if field.store and field.type not in ['many2many', 'one2many'])

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            SELECT
                %s
            FROM hr_employee emp
        )""" % (self._table, self._get_fields()))
