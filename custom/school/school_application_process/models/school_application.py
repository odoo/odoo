import time
from datetime import datetime
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError
try:
    from odoo.tools import image_colorize, image_resize_image_big
except:
    image_colorize = False
    image_resize_image_big = False
import requests


class SchoolApplication(models.Model):
    _name = 'school.application'
    _inherit = ['ir.needaction_mixin', 'mail.thread']
    _description = 'Student Application'

    def send_app_notification(self):
        email_obj = self.env['mail.mail']
        if self.parent_email:
            subject = '%s Online Application' % self.env.user.company_id.name
            message = 'Your Application for %s ha been received successfully, we will contact you shortly' \
                      'Regards %s' % (self.name, self.env.user.company_id.name)
            mail = email_obj.create({
                'subject': subject,
                'body': message,
                'email_from': self.env.user.company_id.email,
                'email_to': self.parent_email
            })
            mail.send()
            return True
        if self.env.user.company_id.send_application_sms and self.parent_phone:
            api_key = self.env['ir.config_parameter'].get_param('sms.api_key')
            api_secret = self.env['ir.config_parameter'].get_param('sms.api_secret')
            to = str(self.parent_phone)
            sender = str(self.env.user.company_id.name)
            message = 'Your Application for %s ha been received successfully, we will contact you shortly' \
                      'Regards %s' % (self.name, self.env.user.company_id.name)
            post_data = {'api_key': api_key, 'api_secret': api_secret, 'to': to, 'from': sender,
                         'text': message
                         }
            requests.post('https://rest.nexmo.com/sms/json', data=post_data)
            return True

    @api.multi
    @api.depends('date_of_birth')
    def _compute_age(self):
        minimum_age = self.env.user.company_id.minimum_age
        maximum_age = self.env.user.company_id.maximum_age
        for rec in self:
            rec.age = 0
            if rec.date_of_birth:
                start = datetime.strptime(rec.date_of_birth,
                                          DEFAULT_SERVER_DATE_FORMAT)
                end = datetime.strptime(time.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                        DEFAULT_SERVER_DATE_FORMAT)
                age = ((end - start).days / 365)
                if age >= minimum_age and (age <= maximum_age):
                    rec.age = age
                else:
                    raise ValidationError('The minimum age for enrolling student is %s and the maximum age is %s' %
                                          (self.env.user.company_id.minimum_age, self.env.user.company_id.maximum_age))
                    return True

    @api.constrains('parent_phone')
    def _check_phone(self):
        try:
            int(self.parent_phone)
        except ValueError:
            raise ValidationError("Invalid Phone Number"
                                  " Only Numeric Values allowed")
        if len(self.parent_phone) != 11:
            raise ValidationError("Phone Number not in the required format"
                                  " use this format instead 23299473726")

    @api.model
    def create(self, vals):
        result = super(SchoolApplication, self).create(vals)
        result.send_app_notification()
        return result

    @api.constrains('parent_email')
    def _check_email(self):
        if self.parent_email:
            if "@" in self.parent_email:
                x, y = self.parent_email.split("@")
                if len(x) > 1 and "." in y:
                    a, b = y.split(".")
                    if len(a) > 1 and len(b) > 1:
                        return True
                    else:
                        raise ValidationError("Invalid Email Address")
            else:
                raise ValidationError("Invalid Email Address")

    @api.onchange('school_level')
    def onchange_school_level(self):
        if self.school_level == 'jss':
            self.stream_id = False
            if self.form_id.school_level != 'jss':
                self.form_id = False
        if self.school_level == 'sss':
            self.stream_id = False
            if self.form_id.school_level != 'sss':
                self.form_id = False

    @api.onchange('school_type')
    def onchange_school_type(self):
        if self.school_type == 'primary':
            self.form_id = False
            self.school_level = False
        if self.school_type == 'secondary':
            self.class_id = False
            self.p_school_level = False

    @api.one
    def create_admission(self):
        admission_obj = self.env['school.student']
        parent_obj = self.env['school.parent']
        previous_school_obj = self.env['student.previous.school']
        remark_obj = self.env['student.description']
        parent_id = parent_obj.create({'name': self.parent_name,
                                       'phone': self.parent_phone,
                                       'email': self.parent_email,
                                       'street': self.parent_address
                                       })
        student = admission_obj.create({
            'name': self.name,
            'gender': self.gender,
            'nationality_id': self.nationality.id,
            'date_of_birth': self.date_of_birth,
            'age': self.age,
            'p_school_level': self.p_school_level,
            'class_id': self.class_id,
            'form_id': self.form_id,
            'stream_id': self.stream_id,
            'street': self.street,
            'city': self.city,
            'district': self.district,
            'province': self.province,
            'mobile': self.student_modbile,
            'email': self.student_email,
            'contact_phone1': self.emergency_contact,
            'parent_id': parent_id.id,
            'doctor': self.doctor,
            'doctor_phone': self.doctor_phone,
            'blood_group': self.blood_group,
            'height': self.height,
            'weight': self.weight,
            'eye': self.eye,
            'ear': self.ear,
            'nose_throat': self.nose_throat,
            'respiratory': self.respiratory,
            'cardiovascular': self.cardiovascular,
            'neurological': self.neurological,
            'muskoskeletal': self.muskoskeletal,
            'dermatological': self.dermatological,
            'blood_pressure': self.blood_pressure,
            'remark': self.remark,
            'medical_note': self.medical_note
        })
        previous_school_obj.create({
            'student_id': student.id,
            'name': self.p_school_name,
            'admission_date': self.p_school_admit_date,
            'exit_date': self.p_school_exit_date,
        })

    school_type = fields.Selection([('primary', 'Primary'),
                                    ('secondary', 'Secondary')],
                                   default=lambda obj: obj.env.user.company_id.school_type,
                                   readonly=True
                                   )
    name = fields.Char(string="Name", required=True)
    stream_id = fields.Many2one('school.stream', "Stream")
    application_ref = fields.Char('Application Reference',  default=lambda obj:
    obj.env['ir.sequence'].get('school.application'),
                      help='Application Reference')
    photo = fields.Binary('Photo')
    nationality = fields.Many2one('res.country', string='Nationality', required=True)
    first_language = fields.Char(string='First Language')
    entry_academic_yr = fields.Many2one('academic.year', String='Entry Academic Year',
                                        domain=[('future', '=', True)])
    cast_id = fields.Many2one('student.cast', 'Religion')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')],
                              'Gender', required=True)
    date_of_birth = fields.Date('Date of Birth', required=True)
    age = fields.Integer('Age', compute='_compute_age', readonly=True)
    marital_status = fields.Selection([('unmarried', 'Unmarried'),
                                       ('married', 'Married')],
                                      'Marital Status')
    p_school_name = fields.Char('Previous School Name')
    p_school_admit_date = fields.Date('Admission Date')
    p_school_exit_date = fields.Date('Exit Date')
    class_id = fields.Many2one('school.class', 'Class')
    form_id = fields.Many2one('school.form', 'Form', help='Form')
    stage = fields.Selection([
                              ('primary', 'Primary'),
                              ('secondary', 'Secondary')],
                             string='Stage',
                             default='primary'
                             )
    emergency_contact = fields.Char('Emergency Contact Number')
    doctor = fields.Char('Doctor Name')
    doctor_phone = fields.Char('Phone')
    blood_group = fields.Char('Blood Group', )
    height = fields.Float('Height')
    weight = fields.Float('Weight')
    eye = fields.Boolean('Eyes')
    ear = fields.Boolean('Ears')
    nose_throat = fields.Boolean('Nose & Throat')
    respiratory = fields.Boolean('Respiratory')
    cardiovascular = fields.Boolean('Cardiovascular')
    neurological = fields.Boolean('Neurological')
    muskoskeletal = fields.Boolean('Musculoskeletal')
    dermatological = fields.Boolean('Dermatological')
    blood_pressure = fields.Boolean('Blood Pressure')
    remark = fields.Text('Remark')
    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirmed'),
                              ('accept', 'Accepted'),
                              ('reject', 'Rejected')
                              ],
                             'State', readonly=True, default='draft')
    description = fields.One2many('student.description', 'des_id',
                                  'Description')
    student_mobile = fields.Char('Mobile No.', default='232', size=11)
    student_email = fields.Char('Email')
    city = fields.Char('City', default='Freetown', required=True)

    parent_phone = fields.Char('Mobile No.', required=True, default='232', size=11)
    parent_email = fields.Char('Email')
    parent_address = fields.Char('Parent/Guardian Address')
    parent_name = fields.Char('Parent/Guardian Name')
    class_id = fields.Many2one('school.class', 'Class/Nursery')
    form_id = fields.Many2one('school.form', 'Form', help='Student Form')
    school_level = fields.Selection([('jss', 'JSS'),
                                     ('sss', 'SSS')],
                                    default='jss',
                                    string='Level (JSS/SSS)')
    p_school_level = fields.Selection([('class', 'Class'),
                                       ('nursery', 'Nursery')],
                                      default='nursery',
                                      string='Level (Nursery/Class)',
                                      required=True)
    cmp_id = fields.Many2one('res.company', 'Company',
                             default=lambda self: self.env.user.company_id,
                             ondelete='cascade')
    street = fields.Char(string='Address', required=True)
    district = fields.Selection([
        ('bo', 'Bo'),
        ('kenema', 'Kenema'),
        ('kailahun', 'Kailahun'),
        ('kono', 'Kono'),
        ('koinadugu', 'Koinadugu'),
        ('bombali', 'Bombali'),
        ('portloko', 'Portloko'),
        ('bonthe', 'Bonthe'),
        ('moyamba', 'Moyamba'),
        ('pujehun', 'Pujehum'),
        ('tonkolili', 'Tonkolili'),
        ('kambia', 'Kambia'),
        ('westernurban', 'Western Area Urban'),
        ('westernrural', 'Western Area Rutal'), ],
        'District',
        default='westernurban')

    province = fields.Selection([
        ('westernarea', 'Western Area'),
        ('southern', 'Southern'),
        ('northern', 'Northern'),
        ('eastern', 'Eastern'),
    ], string='Province', default='westernarea')

    medical_note = fields.Text(string="Medical Note/Comment")
    note = fields.Text(string="Note/Comment")

    @api.multi
    def set_to_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})
        return True

    @api.multi
    def set_confirm(self):
        self.ensure_one()
        self.write({'state': 'confirm'})
        return True

    @api.multi
    def set_accepted(self):
        self.ensure_one()
        self.write({'state': 'accept'})
        self.send_accept_notification()
        self.create_admission()
        return True

    @api.multi
    def set_rejected(self):
        self.ensure_one()
        self.write({'state': 'reject'})
        self.send_app_notification()
        return True
