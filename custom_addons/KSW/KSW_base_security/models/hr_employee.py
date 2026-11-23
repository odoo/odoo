# -*- coding: utf-8 -*-
from odoo import fields, models

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Extend access to leave-related fields for custom Employee and Supervisor groups
    # Standard Odoo restricts these to hr.group_hr_user (Officer)
    
    current_leave_id = fields.Many2one(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    current_leave_state = fields.Selection(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    leave_date_from = fields.Date(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    allocation_count = fields.Float(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    allocations_count = fields.Integer(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    exceptional_location_id = fields.Many2one(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    version_id = fields.Many2one(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    version_ids = fields.One2many(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    versions_count = fields.Integer(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    date_start = fields.Date(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    date_end = fields.Date(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    contract_wage = fields.Monetary(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    currency_id = fields.Many2one(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    legal_name = fields.Char(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    private_phone = fields.Char(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    private_email = fields.Char(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    birthday = fields.Date(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    emergency_contact = fields.Char(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    emergency_phone = fields.Char(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    visa_no = fields.Char(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    visa_expire = fields.Date(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    permit_no = fields.Char(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    work_permit_expiration_date = fields.Date(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
