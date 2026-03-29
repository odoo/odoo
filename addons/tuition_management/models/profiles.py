# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StudentProfile(models.Model):
    _name = 'student.profile'
    _description = 'Student Profile'

    # Personal Information
    first_name = fields.Char(string='First Name', required=True)
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name', required=True)
    email = fields.Char(string='Email Address')
    phone = fields.Char(string='Phone Number')
    country_code = fields.Char(string='Country Code', default='+1')
    
    # Academic Information
    grade_id = fields.Many2one('grade.master', string='Grade')
    subjects_ids = fields.Many2many('subject.master', string='Subjects')
    
    # Address fields
    address_line_1 = fields.Char(string='Address Line 1')
    address_line_2 = fields.Char(string='Address Line 2')
    address_line_3 = fields.Char(string='Address Line 3')
    address_line_4 = fields.Char(string='Address Line 4')
    zip_code = fields.Char(string='Zip Code')


class TutorProfile(models.Model):
    _name = 'tutor.profile'
    _description = 'Tutor Profile'

    # Personal Information
    first_name = fields.Char(string='First Name', required=True)
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name', required=True)
    email = fields.Char(string='Email Address')
    phone = fields.Char(string='Phone Number')
    country_code = fields.Char(string='Country Code', default='+1')
    
    # Professional Information
    subjects_ids = fields.Many2many('subject.master', string='Subjects')
    
    # Address fields
    address_line_1 = fields.Char(string='Address Line 1')
    address_line_2 = fields.Char(string='Address Line 2')
    address_line_3 = fields.Char(string='Address Line 3')
    address_line_4 = fields.Char(string='Address Line 4')
    zip_code = fields.Char(string='Zip Code')


class ParentProfile(models.Model):
    _name = 'parent.profile'
    _description = 'Parent Profile'

    # Personal Information
    first_name = fields.Char(string='First Name', required=True)
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name', required=True)
    email = fields.Char(string='Email Address')
    phone = fields.Char(string='Phone Number')
    country_code = fields.Char(string='Country Code', default='+1')
    
    # Relationships
    student_ids = fields.Many2many('student.profile', string='Students', help='Students under this parent')
    
    # Address fields
    address_line_1 = fields.Char(string='Address Line 1')
    address_line_2 = fields.Char(string='Address Line 2')
    address_line_3 = fields.Char(string='Address Line 3')
    address_line_4 = fields.Char(string='Address Line 4')
    zip_code = fields.Char(string='Zip Code')


class SubjectMaster(models.Model):
    _name = 'subject.master'
    _description = 'Subject'

    name = fields.Char(required=True)
    code = fields.Char()
    description = fields.Text()


class GradeMaster(models.Model):
    _name = 'grade.master'
    _description = 'Grade'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
