# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo Module
#    Copyright (C) 2015 Inline Technology Services (http://www.inlinetechnology.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
import datetime
from openerp import tools
from openerp.osv import fields, osv, expression
from openerp.tools.translate import _

class hr_employee(osv.Model):
	_inherit="hr.employee"
	_columns={
        #Hire
	    'hire_application_date':fields.date("Application Date"),
	    'hire_driving_record_check':fields.date("Driving Record Check"),
	    'hire_pre_employment_drug_test':fields.date("Pre-Employment Drug Test"),
	    'hire_honesty_test':fields.date("Honesty Test"),
	    'hire_employee_handbook':fields.date("Employee Handbook"),
	    'hire_confidentially_agreement':fields.date("Confidentially Agreement"),
        'hire_no_cell_phone':fields.date("No Cell Phone Policy"),
        'hire_job_descriptions':fields.date("Job Descriptions"),
        'hire_tax_forms':fields.date("Tax Forms"),
        'hire_i9_documents':fields.date("I9 with Supporting Docs"),
        'hire_direct_deposit':fields.date("Direct Deposit"),
        'hire_OH_new_reporting':fields.date("OH New Employee Reporting"),
        'hire_auto_insurance':fields.date("Auto Insurance"),
        'hire_mailbox':fields.date("Mailbox"),
        'hire_credit_card_policy':fields.date("Credit Card Policy"),
        'hire_uniforms':fields.date("Uniforms"),
        'hire_keys':fields.date("Keys"),
        'hire_logins':fields.date("Cell Phone/Tablets/Logins"),
        'hire_picture_release':fields.date("Picture Release"),
        'hire_clc_card':fields.date("CLC Card"),
        
        #Benefits
        'hire_health_30':fields.date("Health Insurance, 30 Days"),
        'hire_dental_30':fields.date("Dental Insurance, 30 Days"),
        'hire_vision_30':fields.date("Vision Insurance, 30 Days"),
        'hire_life_90':fields.date("Life Insurance, 90 Days"),
        'hire_disability_90':fields.date("Disability Insurance, 90 Days"),
        'hire_401k_30':fields.date("401K, 30 days"),
        'hire_union':fields.date("Union"),
        'hire_safety_policy':fields.date("Safety Policy"),
        'hire_fire_exit':fields.date("Fire Extinguisher Video/Test"),
        'hire_hepatitis_vaccine':fields.date("Hepatitis Vaccine"),
        'hire_ppe':fields.date("PPE"),
        'hire_confined_trining':fields.date("Confined Space Training"),
        'hire_DOT_card':fields.date("DOT Medical Card"),
        'hire_DOT_card_duration':fields.integer("DOT Medical Card Duration"),
        'hire_CDL_tracking':fields.date("CDL Tracking"),
        'hire_training_tri':fields.date("Training at Tri-State"),

        #Terminate
        'terminate_auto_insurance':fields.date("Auto Insurance"),
        'terminate_mailbox':fields.date("Mailbox"),
        'terminate_credit_card_policy':fields.date("Credit Card Policy"),
        'terminate_uniforms':fields.date("Uniforms"),
        'terminate_keys':fields.date("Keys"),
        'terminate_logins':fields.date("Cell Phone/Tablets/Logins"),

        'terminate_health_30':fields.date("Health Insurance"),
        'terminate_dental_30':fields.date("Dental Insurance"),
        'terminate_vision_30':fields.date("Vision Insurance"),
        'terminate_life_90':fields.date("Life Insurance"),
        'terminate_disability_90':fields.date("Disability Insurance"),
        'terminate_401k_30':fields.date("401K"),
        'terminate_union':fields.date("Union"),
        'terminate_ppe':fields.date("PPE"),
        'terminate_training_tri':fields.date("Training at Tri-State"),
	}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
