# -*- coding: utf-8 -*-
from odoo import fields, models

class HrVersion(models.Model):
    _inherit = 'hr.version'

    # Extend access to version fields for custom Employee and Supervisor groups
    # Standard Odoo restricts these to hr.group_hr_user (Officer)
    
    date_version = fields.Date(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    employee_id = fields.Many2one(
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
    private_phone = fields.Char(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    private_email = fields.Char(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    ssnid = fields.Char(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    passport_id = fields.Char(
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    sex = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading")

    marital = fields.Selection(
        selection='_get_marital_status_selection',
        groups="hr.group_hr_user,KSW_base_security.group_hr_employee_subordinate,KSW_base_security.group_hr_employee_supervisor,KSW_base_security.group_hr_employee_supervisor_cascading"
    )
    children = fields.Integer(
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
