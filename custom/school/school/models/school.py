import time
from datetime import date, datetime
from odoo import models, fields, api
from odoo import modules
from odoo.tools.translate import _
from odoo.modules import get_module_resource
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError
try:
    from odoo.tools import image_colorize, image_resize_image_big
except ImportError:
    image_colorize = False
    image_resize_image_big = False


class AcademicYear(models.Model):
    _name = "school.academic.year"
    _description = "Academic Year"
    _order = "sequence"

    sequence = fields.Integer(string='Sequence',
                              required=True,
                              help="Sequence/Order you want to see this Academic year.")
    is_current = fields.Boolean("Current Academic Year",
                                default=False,
                                help="Check this box if this the current Academic year")
    name = fields.Char(string='Name',
                       required=True,
                       help='Name of this Academic year')
    code = fields.Char(string='Code',
                       required=True,
                       help='Code of this Academic year')
    date_start = fields.Date(string='Start Date',
                             required=True,
                             help='Starting date of this Academic year')
    date_stop = fields.Date(string='End Date',
                            required=True,
                            help='Ending date of this Academic year')
    term_ids = fields.One2many('school.academic.term',
                               'academic_year_id',
                               string='Terms',
                               help="Related Academic Terms",
                               domain=[('academic_year', '=', False)]
                               )
    grade_id = fields.Many2one('grade.master',
                               string="Grading Sequence")
    description = fields.Text(string='Description',
                              help="Description of this Academic year")

    @api.model
    def next_year(self, sequence):
        year_ids = self.search([('sequence', '>', sequence)], order='sequence ASC', limit=1)
        if year_ids:
            return year_ids.id
        return False

    @api.multi
    def name_get(self):
        res = []
        for acd_year_rec in self:
            name = "[" + acd_year_rec['code'] + "]" + acd_year_rec['name']
            res.append((acd_year_rec['id'], name))
        return res

    @api.constrains('date_start', 'date_stop')
    def _check_academic_year(self):
        obj_academic_ids = self.search([])
        academic_list = []
        for rec_academic in obj_academic_ids:
            academic_list.append(rec_academic.id)
        for current_academic_yr in self:
            academic_list.remove(current_academic_yr.id)
            data_academic_yr = self.browse(academic_list)
            for old_ac in data_academic_yr:
                if old_ac.date_start <= self.date_start <= old_ac.date_stop or \
                                        old_ac.date_start <= self.date_stop <= old_ac.date_stop:
                    raise Warning(_('Error! You cannot define overlapping academic years.'))

    @api.constrains('date_start', 'date_stop')
    def _check_duration(self):
        if self.date_stop and self.date_start and self.date_stop < self.date_start:
            raise Warning(_('Error! The duration of the academic year is invalid.'))

    _sql_constraints = [('sequence', 'unique(name)',
                         'Sequence must be unique!'),
                        ('code', 'unique(code)',
                         'Code must be unique!'),
                        ]


class AcademicTerm(models.Model):
    _name = "school.academic.term"
    _description = "Academic Term"
    _order = "date_start"

    name = fields.Char(string='Name',
                       required=True,
                       help='Name of this Academic Term')
    code = fields.Char(string='Code',
                       required=True,
                       help='Code of this Academic Term')
    date_start = fields.Date(string='Start of Term',
                             required=True,
                             help='Starting date of this Academic Term')
    date_stop = fields.Date(string='End of Term',
                            required=True,
                            help='Ending date of this Academic Term')
    academic_year_id = fields.Many2one('school.academic.year',
                                       string='Academic Year',
                                       required=True,
                                       help="Related Academic year ",
                                       ondelete='cascade',
                                       domain=[('term_ids', '=', False)])
    description = fields.Text('Description', help="Description of this Academic Term")

    @api.constrains('date_start', 'date_stop')
    def _check_duration(self):
        if self.date_stop and self.date_start and self.date_stop < self.date_start:
            raise Warning(_('Error ! The duration of the Month(s) is/are invalid.'))

    @api.constrains('academic_year_id', 'date_start', 'date_stop')
    def _check_year_limit(self):
        if self.academic_year_id and self.date_start and self.date_stop:
            if self.academic_year_id.date_stop < self.date_stop or \
                            self.academic_year_id.date_stop < self.date_start or \
                            self.academic_year_id.date_start > self.date_start or \
                            self.academic_year_id.date_start > self.date_stop:
                raise Warning(_('Invalid Months ! Some months overlap or \n'
                                'the date period is not in the scope of the academic year.'))

    _sql_constraints = [('name', 'unique(name)',
                         'Name must be unique!'),
                        ('code', 'unique(code)',
                         'Code must be unique!'),
                        ]


class SchoolClass(models.Model):
    _name = 'school.class'
    _description = 'School Class'
    _rec_name = "class_name"
    _order = "sequence"

    @api.one
    @api.depends('sequence')
    def _compute_class_name(self):
        if self.school_level == 'nursery':
            self.class_name = "Nursery "+str(self.sequence)
        elif self.school_level == 'class':
            self.class_name = "Class " + str(self.sequence-3)

    @api.one
    def _compute_neighbor_class(self):
        next_seq = self.sequence + 1
        pre_seq = self.sequence - 1
        self.next_class_id = self.env['school.class'].search([('sequence', '=', next_seq)]).id
        self.previous_class_id = self.env['school.class'].search([('sequence', '=', pre_seq)]).id

    sequence = fields.Integer(string='Sequence',
                              required=True,
                              help='Sequence in which classes appear')
    subject_ids = fields.Many2many('school.subject',
                                   relation='subject_class_rel',
                                   column1='subject_id',
                                   column2='class_id',
                                   string='Subjects',
                                   help="Subjects offered in this class")
    student_ids = fields.One2many('school.student', 'class_id',
                                  string='Students In class',
                                  help="Students Currently in this class")
    next_class_id = fields.Many2one('school.class',
                                    string='Next class',
                                    compute='_compute_neighbor_class',
                                    readonly=True,
                                    help="Next class students will be promoted to")
    previous_class_id = fields.Many2one('school.class',
                                        string='Previous class',
                                        compute='_compute_neighbor_class',
                                        readonly=True,
                                        help="Previous class students got promoted from")
    teacher_id = fields.Many2one('hr.employee',
                                 string='Class Teacher',
                                 help="Class Teacher")
    public_exam_class = fields.Boolean(string='Public Exam Class',
                                       help='Check if this is a public exam class')
    public_exam_type = fields.Many2one('public.exam',
                                       string='Public Exam',
                                       help='Public Exam to be taken at this class')
    passing_mark = fields.Float(string='Passing Mark',
                                help="Percentage that determines promotion to next class",
                                required=True)
    class_name = fields.Char(string='Class Name',
                             compute='_compute_class_name',
                             readonly=True,
                             help="Class name")
    school_level = fields.Selection([('class', 'Class'),
                                     ('nursery', 'Nursery')],
                                    default='nursery',
                                    string='Level (Nursery/Class)',
                                    required=True,
                                    help="Specify level (Nursery or Class)")
    school_type = fields.Selection([('primary', 'Primary'),
                                    ('secondary', 'Secondary')],
                                   default=lambda obj: obj.env.user.company_id.school_type,
                                   required=True,
                                   readonly=True
                                   )

    _sql_constraints = [('class_name', 'unique(class_name)',
                         'Name must be unique!'),
                        ('sequence', 'unique(sequence)',
                         'Sequence must be unique!'),
                        ]


class SchoolForm(models.Model):
    _name = 'school.form'
    _description = 'School Forms'
    _rec_name = "form_name"
    _order = "sequence"

    @api.one
    @api.depends('sequence')
    def _compute_form_name(self):
        if self.school_level == 'jss':
            self.form_name = "JSS "+str(self.sequence)
        elif self.school_level == 'sss':
            self.form_name = "SSS " + str(self.sequence-3)

    @api.one
    def _compute_neighbor_form(self):
        next_seq = self.sequence + 1
        pre_seq = self.sequence - 1
        self.next_form_id = self.env['school.form'].search([('sequence', '=', next_seq)]).id
        self.previous_form_id = self.env['school.form'].search([('sequence', '=', pre_seq)]).id

    sequence = fields.Integer(string='Sequence',
                              required=True,
                              help="Sequence in which forms appear")
    subject_ids = fields.Many2many('school.subject',
                                   relation='subject_form_rel',
                                   column1='subject_id',
                                   column2='form_id',
                                   string='Subjects',
                                   help="Subjects offered in this form")
    student_ids = fields.One2many('school.student', 'form_id',
                                  string='Students In Form',
                                  help="Students currently in this form")
    next_form_id = fields.Many2one('school.form',
                                   string='Next Form',
                                   compute='_compute_neighbor_form',
                                   readonly=True,
                                   help="Next form Students will be promoted to")
    previous_form_id = fields.Many2one('school.form',
                                       string='Previous Form',
                                       compute='_compute_neighbor_form',
                                       readonly=True,
                                       help="Previous form Student got promoted from")
    teacher_id = fields.Many2one('hr.employee',
                                 string='Form Teacher',
                                 help="Form Teacher")
    public_exam_form = fields.Boolean(string='Public Exam Form',
                                      help='Check if this is a public exam Form')
    public_exam_type = fields.Many2one('public.exam',
                                       string='Public Exam',
                                       help='Public Exam to be taken at this form')
    passing_mark = fields.Float(string='Passing Mark',
                                help="Percentage that determines promotion to next Form",
                                required=True)
    form_name = fields.Char(string='Form Name',
                            compute='_compute_form_name',
                            readonly=True,
                            help="Form Name")
    school_level = fields.Selection([('jss', 'Jss'),
                                     ('sss', 'SSS')],
                                    default='jss',
                                    string='Form Level (JSS/SSS)',
                                    help="Level (JSS or SSS)")
    school_type = fields.Selection([('primary', 'Primary'),
                                    ('secondary', 'Secondary')],
                                   default=lambda obj: obj.env.user.company_id.school_type,
                                   required=True,
                                   readonly=True
                                   )

    _sql_constraints = [('form_name', 'unique(form_name)',
                         'Name must be unique!'),
                        ('sequence', 'unique(sequence)',
                         'Sequence must be unique!'),
                        ]


class SchoolClassroom(models.Model):
    _name = 'school.classroom'
    _description = 'School Class Room'
    _rec_name = 'classroom_name'

    @api.one
    @api.depends('form_id', 'code', 'class_id')
    def _compute_name(self):
        if self.form_id:
            if self.form_id.school_level == 'jss':
                self.classroom_name = "JSS "+str(self.form_id.sequence)+str(self.code)
            elif self.form_id.school_level == 'sss':
                if self.stream_id:
                    self.classroom_name = "SSS " + str(self.form_id.sequence-3)+" "+str(self.stream_id.name)+" "+\
                                          str(self.code)
                else:
                    self.classroom_name = "SSS " + str(self.form_id.sequence-3)+" "+str(self.code)
        if self.class_id:
            if self.class_id.school_level == 'nursery':
                self.classroom_name = "Nursery " + str(self.class_id.sequence) + str(self.code)
            elif self.class_id.school_level == 'class':
                self.classroom_name = "Class " + str(self.class_id.sequence - 3) + str(self.code)

    @api.one
    @api.depends('student_ids', 'seat_no')
    def _compute_available_seats(self):
        self.available_seats = self.seat_no - len(self.student_ids)

    seat_no = fields.Integer(string='Seat Number',
                             required=True,
                             help="Number of students this classroom can accommodate")
    available_seats = fields.Integer(string='Available Seats',
                                     readonly=True,
                                     store=True,
                                     compute='_compute_available_seats',
                                     help="Currently available seats",)
    class_id = fields.Many2one('school.class',
                               string='Class',
                               help='Class allocated to this classroom')
    form_id = fields.Many2one('school.form',
                              string='Form',
                              help='Form allocated to this classroom')
    stream_id = fields.Many2one('school.stream',
                                string='Stream',
                                related='form_id.stream_id',
                                help='Stream (If Applicable')
    code = fields.Char(string='Code',
                       required=True,
                       help="Classroom Code")
    description = fields.Text(string='Description',
                              help="Description of classroom")
    classroom_name = fields.Char(string='Name',
                                 required=True,
                                 compute='_compute_name',
                                 store=True)
    student_ids = fields.One2many('school.student', 'classroom_id',
                                  string="Students in Classroom",
                                  help="Students in this classroom")
    school_level = fields.Selection([('jss', 'JSS'),
                                     ('sss', 'SSS')],
                                    default='jss',
                                    string='Form Level (JSS/SSS)')
    p_school_level = fields.Selection([('class', 'Class'),
                                       ('nursery', 'Nursery')],
                                      default='nursery',
                                      string='Level (Nursery/Class)')
    school_type = fields.Selection([('primary', 'Primary'),
                                    ('secondary', 'Secondary')],
                                   default=lambda obj: obj.env.user.company_id.school_type,
                                   required=True,
                                   readonly=True
                                   )

    @api.constrains
    @api.depends('student_ids', 'available_seats')
    def _check_seats(self):
        if len(self.student_ids) > self.available_seats:
            raise Warning(_('Error ! The number of Students has exceeds the number of available seats'
                            ' in the classroom.'))

    @api.onchange('school_type')
    def onchange_school_type(self):
        if self.school_type == 'primary':
            self.form_id = False
            self.school_level = False
        if self.school_type == 'secondary':
            self.class_id = False
            self.p_school_level = False


class PublicExam(models.Model):
    _name = 'public.exam'
    name = fields.Char(string="Name",
                       required=True,
                       help='Name of public exam ')
    description = fields.Char(string='Description',
                              help='Description of Public exam')
    _sql_constraints = [('name', 'unique(name)',
                         'Name must be unique!'),
                        ]


class SchoolStream(models.Model):
    _name = 'school.stream'
    name = fields.Char(string="Name",
                       required=True,
                       help='Name of stream')
    student_ids = fields.One2many('school.student', 'stream_id',
                                  String="Students",
                                  help='Students in this stream')
    _sql_constraints = [('name', 'unique(name)',
                         'Name must be unique!'),
                        ]
    subject_ids = fields.Many2many('school.subject',
                                   relation='subject_stream_rel',
                                   column1='subject_id',
                                   column2='stream_id',
                                   String="Subjects",
                                   help='Subjects related to this stream')
    _sql_constraints = [('name', 'unique(name)',
                         'Name must be unique!'),
                        ]


class SubjectSubject(models.Model):
    _name = "school.subject"
    
    _description = "Subjects"
    name = fields.Char(string='Name',
                       required=True,
                       help='Name of subject eg. Mathematics')
    code = fields.Char(string='Code',
                       required=True,
                       help='Code of the subject')
    maximum_marks = fields.Float(string="Maximum mark",
                                 required=True,
                                 help='Maximum mark a student can score in this subject',
                                 default=100.0)
    minimum_marks = fields.Float(string="Minimum mark",
                                 required=True,
                                 help='Maximum mark a student can score in this subject',
                                 default=0.0)
    teacher_ids = fields.Many2many('hr.employee',
                                   relation='subject_teacher_rel',
                                   column1='subject_id',
                                   column2='teacher_id',
                                   string='Teachers',
                                   help="Teachers teaching this subject")
    class_ids = fields.Many2many('school.class',
                                 relation='subject_class_rel',
                                 column1='class_id',
                                 column2='subject_id',
                                 string='Classes',
                                 help="Classes this subject is offered")
    form_ids = fields.Many2many('school.form',
                                relation='subject_form_rel',
                                column1='form_id',
                                column2='subject_id',
                                string='Forms',
                                help="Forms this subject is offered")
    student_ids = fields.Many2many('school.student',
                                   relation='subject_student_rel',
                                   column1='student_id',
                                   column2='subject_id',
                                   string='Students',
                                   help='Students offering this subject')
    is_practical = fields.Boolean(string='Is Practical',
                                  help='Check this if subject is practical.')

    no_exam = fields.Boolean(string="Require Exam",
                             default=True,
                             help="Uncheck this if subject doesn't require an exam.")
    syllabus_ids = fields.One2many('subject.syllabus', 'subject_id',
                                   string='Syllabus',
                                   help="Subject's syllabus")
    school_level = fields.Selection([('jss', 'Jss'),
                                     ('sss', 'SSS')],
                                    string='Level Offered (JSS/SSS)',
                                    help='Level this subject is offered (JSS/SSS)')
    p_school_level = fields.Selection([('class', 'Class'),
                                       ('nursery', 'Nursery')],
                                      string='Level (Nursery/Class)',
                                      help='Level this subject is offered (Nursery/Class)')
    school_type = fields.Selection([('primary', 'Primary'),
                                    ('secondary', 'Secondary')],
                                   default=lambda obj: obj.env.user.company_id.school_type,
                                   required=True,
                                   readonly=True
                                   )
    stream_ids = fields.Many2many('school.stream',
                                  string="Stream(s)",
                                  help="Stream(s) this subject is related to")
    is_general = fields.Boolean(string='Is General',
                                help="Check this box if this is a general or compulsory "
                                     "subject and is offered by all students")
    is_elective = fields.Boolean(string='Is Elective',
                                 help="Check this box if this is an elective subject")
    _sql_constraints = [('name', 'unique(name)',
                         'Name must be unique!'),
                        ('code', 'unique(code)',
                         'Code must be unique!'),
                        ]

    @api.onchange('school_level', 'p_school_level')
    def check0(self):
        self.student_ids = False
        self.form_ids = False
        self.class_ids = False

    # TODO Fix Elective/General Switching

    @api.onchange('school_level', 'is_general',)
    def check1(self):
        if self.school_level == 'jss':
            self.stream_ids = False
        if self.is_general:
            self.is_elective = False
        if not self.is_general:
            self.is_elective = True

    @api.onchange('school_type')
    def check2(self):
        if self.school_type == 'primary':
            self.form_ids = False
            self.stream_ids = False
            self.school_level = False
        if self.school_type == 'secondary':
            self.class_ids = False
            self.p_school_level = False

    @api.onchange('is_elective')
    def check3(self):
        if self.is_elective:
            self.is_general = False
        if not self.is_elective:
            self.is_general = True

    def compute_forms(self):
        form_obj = self.env['school.form']
        domain = ('school_level', '=', self.school_level)
        self.form_ids = form_obj.search([domain])

    def compute_classes(self):
        form_obj = self.env['school.class']
        domain = ('school_level', '=', self.p_school_level)
        self.class_ids = form_obj.search([domain])

    @api.depends('school_level', 'p_school_level')
    def compute_students(self):
        """ This function will automatically computes the Students that
        offer this Subject."""
        student_obj = self.env['school.student']
        # For Secondary Schools
        if self.school_level == 'jss':
            student_ids = student_obj.search([('form_id', 'in', [form.id for form in self.form_ids]),
                                              ('status', '=', 'admitted')])
            self.student_ids += student_ids
        elif self.school_level == 'sss':
            domain = [('stream_id', 'in', [stream.id for stream in self.stream_ids]), ('school_level', '=', 'sss'),
                      ('status', '=', 'admitted')]
            self.student_ids += student_obj.search(domain)
        # For Primary Schools
        if self.p_school_level == 'class':
            student_ids = student_obj.search([('class_id', 'in', [clas.id for clas in self.class_ids]),
                                              ('status', '=', 'admitted'), ('p_school_level', '=', 'class')])
            self.student_ids += student_ids
        if self.p_school_level == 'nursery':
            student_ids = student_obj.search([('class_id', 'in', [clas.id for clas in self.class_ids]),
                                              ('status', '=', 'admitted'), ('p_school_level', '=', 'nursery')])
            self.student_ids += student_ids

    @api.constrains('is_general', 'stream_ids', 'student_ids')
    def constrain1(self):
        if self.student_ids:
            for student in self.student_ids:
                if student.status != 'admitted':
                    raise ValidationError("Error Adding Student please make sure the student(s) is/are admitted")


class SubjectSyllabus(models.Model):
    _name = "subject.syllabus"
    _description = "Syllabus"
    _rec_name = "duration"
    subject_id = fields.Many2one('school.subject',
                                 string='Subject',
                                 help="Subject related to this syllabus")
    duration = fields.Char(string="Period",
                           help="Specify the duration of this syllabus in text eg. First Term",
                           required=True)
    topic = fields.Text(name="Topics",
                        help="Specify the topics included in this syllabus")


class SchoolParent(models.Model):
    _name = 'school.parent'
    _table = "school_parent"
    _description = 'Parent Information'
    _inherits = {'res.users': 'user_id'}

    @api.constrains('phone')
    def _check_phone(self):
        try:
            self.phone and int(self.phone)
        except ValueError:
            raise ValidationError("Invalid Phone Number"
                                  " Only Numeric Values allowed")
        if self.phone and len(self.phone) < 11:
            raise ValidationError("Phone Number not in the required format"
                                  " use this format instead 23299473726")

    @api.constrains('email')
    def _check_email(self):
        if self.email:
            if "@" in self.email:
                x, y = self.email.split("@")
                if "." in y:
                    a, b = y.split(".")
                    if len(a) > 1 and len(b) > 1:
                        return True
                    else:
                        raise ValidationError("Invalid Email Address")
                else:
                    raise ValidationError("Invalid Email Address")
            else:
                raise ValidationError("Invalid Email Address")

    user_id = fields.Many2one('res.users',
                              string='User ID',
                              ondelete="cascade",
                              select=True,
                              required=True)
    student_ids = fields.One2many('school.student', 'parent_id',
                                  string='Children',
                                  help="Students related to this parent")
    login_access = fields.Boolean(string='Can Login',
                                  default=False,
                                  help="This box specify if a parent can login or not."
                                       "If checked, it means the parent have login access, "
                                       "if unchecked, this means the parent doesn't have login access")
    phone = fields.Char(string='Phone',
                        default='232',
                        size=19,
                        help="Phone number of parent/Guardian. " \
                             "Note! this is the number used by the system"
                             " to send out sms notifications to this selected parent."
                             "Number should be in this format 23276753455")
    email = fields.Char(string='Email',
                        help="Email  of parent/Guardian. " \
                             "Note! this is the emil used by the system"
                             " to send out email notifications to this selected parent."
                             "email should be in the correct format eg. effie@byteltd.com")
    can_login = fields.Boolean(string="Parent can Login",
                               default=True,
                               help="Check if this Parent/Guardian can login to view child/children records")

    def toggle_login(self):
        if not self.email or not self._check_email():
            raise ValidationError("Please Provide Correct Email address and Make sure the can login button is checked")
        else:
            if not self.login_access:
                parent_group_id = self.env.ref('school.group_school_parent').id
                if self.user_id.id not in [user.id for user in self.parent_group_id.users]:
                    parent_group_id.write({'users': [(4, self.user_id.id)]})
                    self.user_id.related_parent_id = self.id
                    self.login_access = True


class StudentStudent(models.Model):
    _name = 'school.student'
    _table = "school_student"
    _inherit = ['ir.needaction_mixin', 'mail.thread']
    _description = 'Student Information'
    _inherits = {'res.users': 'user_id'}
    _rec_name = 'display_name'

    @api.constrains
    def check_age(self):
        minimum_age = self.env.user.company_id.minimum_age
        maximum_age = self.env.user.company_id.maximum_age
        if maximum_age >= self.age <= minimum_age:
            raise ValidationError('Please make sure student age is minimum and maximum age range '
                                  ' defined in school setting')
            return True

    @api.multi
    @api.depends('date_of_birth')
    def _compute_age(self):
        for rec in self:
            rec.age = 0
            if rec.date_of_birth:
                start = datetime.strptime(rec.date_of_birth,
                                          DEFAULT_SERVER_DATE_FORMAT)
                end = datetime.strptime(time.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                        DEFAULT_SERVER_DATE_FORMAT)
                age = ((end - start).days / 365)
                rec.age = age

    @api.model
    def create(self, vals):
        if vals.get('pid', False):
            vals['login'] = vals['pid']
            vals['password'] = vals['pid']
        else:
            raise ValidationError('Error! PID not valid so record will not be saved.')
        result = super(StudentStudent, self).create(vals)
        return result

    @api.model
    def _get_img(self, is_company, colorize=False):
        avatar_img = modules.get_module_resource('base',
                                                         'static/src/img',
                                                         'avatar.png')
        image = image_colorize(open(avatar_img).read())
        return image_resize_image_big(image.encode('base64'))

    @api.model
    def _get_default_image(self, is_company, colorize=False):
        # added in try-except because import statements are in try-except
        try:
            img_path = get_module_resource('base', 'static/src/img',
                                           'avatar.png')
            with open(img_path, 'rb') as f:
                image = f.read()
            image = image_colorize(image)
            return image_resize_image_big(image.encode('base64'))
        except ImportError:
            return False

    @api.constrains('email')
    def _check_email(self):
        if self.email:
            if "@" in self.email:
                x, y = self.email.split("@")
                if not len(x) > 1 and "." in y:
                    raise ValidationError("Invalid Email Address")
                a, b = y.split(".")
                if len(a) >= 1 and len(b) > 1:
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
                self.classroom_id = False
        if self.school_level == 'sss':
            self.stream_id = False
            if self.form_id.school_level != 'sss':
                self.form_id = False
                self.classroom_id = False

    @api.onchange('school_type')
    def onchange_school_type(self):
        if self.school_type == 'primary':
            self.form_id = False
            self.school_level = False
            self.classroom_id = False
        if self.school_type == 'secondary':
            self.class_id = False
            self.classroom_id = False
            self.p_school_level = False

    @api.one
    @api.depends('name', 'pid')
    def _name_get_fnc(self):
        name = self.name
        if self.pid:
            name = self.name + ' (' + self.pid + ')'
        self.display_name = name

    @api.multi
    def name_get(self):
        self.ensure_one()
        result = []
        for student in self:
            result.append((student.id, student.display_name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        """
        Redefine the search to search by Student name and id.
        """
        if not name:
            name = '%'
        if not args:
            args = []
        args = args[:]
        records = self.search(
            [
                '|',
                ('pid', operator, name),
                ('name', operator, name),
            ] + args,
            limit=limit
        )
        return records.name_get()

    display_name = fields.Char(
                                compute='_name_get_fnc',
                                string='Name',
                                store=False
                            )
    subject_ids = fields.Many2many('school.subject')
    stream_id = fields.Many2one('school.stream', "Stream")

    user_id = fields.Many2one('res.users', 'User ID', ondelete="cascade",
                              select=True, required=True)
    pid = fields.Char('Student ID', required=True,
                      default=lambda obj: obj.env['ir.sequence'].get('school.student'),
                      help='Personal Identification Number')
    reg_code = fields.Char('Registration Code',
                           help='Student Registration Code')
    photo = fields.Binary('Photo',
                          default=lambda self: self._get_img(self._context.get('default_is_company', False)))
    admitted_year_id = fields.Many2one('school.academic.year', 'Academic Year',
                                       default=lambda self: self.env.user.company_id.current_academic_year,
                                       required=True)
    religion_id = fields.Many2one('student.cast', 'Religion')
    admission_date = fields.Date('Admission Date', default=date.today(), required=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')],
                              'Gender', required=True)
    date_of_birth = fields.Date('Date of Birth', required=True)
    mother_tongue_id = fields.Many2one('mother.tongue', "Mother Tongue")
    age = fields.Integer('Age', compute='_compute_age', readonly=True)
    marital_status = fields.Selection([('unmarried', 'Unmarried'),
                                       ('married', 'Married')],
                                      'Marital Status')
    reference_ids = fields.One2many('student.reference', 'reference_id',
                                    'References')
    previous_school_ids = fields.One2many('student.previous.school',
                                          'previous_school_id',
                                          'Previous School Detail')
    family_con_ids = fields.One2many('student.family.contact',
                                     'family_contact_id',
                                     'Family Contact Detail')
    emergency_contact = fields.Char('Emergency Contact Person')
    emergency_contact_no = fields.Char('Emergency Contact Number')
    designation = fields.Char('Designation')
    doctor = fields.Char("Doctor's Name")
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
    medical_note = fields.Text(string="Medical Note/Comment")
    status = fields.Selection([('draft', 'Draft'),
                              ('admitted', 'Admitted'),
                              ('alumni', 'Alumni'),
                              ('terminate', 'Terminated')
                              ],
                             'State', readonly=True, default='draft')
    history_ids = fields.One2many('student.history', 'student_id', 'History')
    certificate_ids = fields.One2many('student.certificate', 'student_id',
                                      'Certificate')
    student_discipline_ids = fields.One2many('student.descipline',
                                              'student_id', 'Discipline')
    document_ids = fields.One2many('student.document', 'doc_id', 'Documents')
    description_ids = fields.One2many('student.description', 'student_id',
                                  'Description')
    contact_phone = fields.Char('Phone No', related='student_id.phone')
    contact_mobile = fields.Char('Mobile No', related='student_id.mobile')
    student_id = fields.Many2one('school.student', 'Name', ondelete="cascade")
    can_take_exam = fields.Boolean('Can take exam', default=True)

    contact_email = fields.Char('Email', related='student_id.email',
                                readonly=True)
    city = fields.Char('City', default='Freetown', required=True)
    award_ids = fields.One2many('student.award', 'award_list_id', 'Award List')
    parent_id = fields.Many2one('school.parent', "Parent/Guardian", help="Parent/Guardian allowed to login")
    classroom_id = fields.Many2one('school.classroom', 'Classroom', help='Student Classroom')
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
    school_type = fields.Selection([('primary', 'Primary'),
                                    ('secondary', 'Secondary')],
                                   default=lambda obj: obj.env.user.company_id.school_type,
                                   required=True,
                                   readonly=True
                                   )
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
    ], 'Province', default='westernarea')

    login_access = fields.Boolean(string='Can Login', default=False)
    _sql_constraints = [('grn_unique', 'unique(grn_number)',
                         'GRN Number must be unique!'),
                        ('pid', 'unique(pid)',
                         'PID must be unique!'),
                        ('contact_email', 'unique(contact_email)',
                         'Contact Email must be unique!'),
                        ]

    @api.multi
    def set_to_draft(self):
        self.ensure_one()
        self.write({'status': 'draft'})
        return True

    @api.multi
    def set_alumni(self):
        self.ensure_one()
        self.write({'status': 'alumni'})
        return True

    @api.multi
    def set_terminate(self):
        self.ensure_one()
        self.write({'status': 'terminate'})
        return True

    @api.multi
    def set_done(self):
        self.ensure_one()
        self.write({'status': 'admitted'})
        return True

    @api.multi
    def admission_draft(self):
        self.ensure_one()
        self.write({'status': 'draft'})
        return True

    @api.multi
    def admission_done(self):
        self.ensure_one()
        minimum_age = self.env.user.company_id.minimum_age
        maximum_age = self.env.user.company_id.maximum_age
        for student_data in self:
            if not maximum_age <= student_data.age >= minimum_age:
                raise ValidationError('The student is not eligible. Age is not valid.')
            reg_code = self.env['ir.sequence'].get('student.registration')
            registation_code = (
                str('/') + str(student_data.name) +
                str('/') + str(reg_code))
        self.write({'status': 'admitted',
                    'admission_date': time.strftime('%Y-%m-%d'),
                    'reg_code': registation_code})
        return True

    def toggle_login(self, ):
        if not self.login_access:
            student_group_id = self.env.ref('school.group_school_student').id
            res_groups = self.env['res.groups'].search([('id', '=', student_group_id)])
            if student_group_id not in [g.id for g in self.groups_id]:
                res_groups.write({'users': [(4, self.user_id.id)]})
                self.login_access = True

    @api.constrains('classroom_id')
    def _constrains_classroom_detail(self):
        if self.classroom_id.available_seats <= -1:
            raise ValidationError('Warning This Classroom if Full. Please Try another Classroom.')
        if self.onchange_school_type == 'secondary':
            if self.classroom_id and self.classroom_id  .form_id.id != self.form_id.id:
                raise ValidationError("Error You cant add this student to this classroom."
                                      " Please check student's form.")
        if self.onchange_school_type == 'primary':
            if self.classroom_id and self.classroom_id.class_id.id != self.class_id.id:
                raise ValidationError("Error You cant add this student to this classroom. "
                                      "Please check student's Class.")


class StudentGrn(models.Model):
    _name = "student.grn"
    _inherit = ['ir.needaction_mixin', 'mail.thread']
    _rec_name = "grn_no"

    def _compute_grn_no(self):
        for stud_grn in self:
            grn_no1 = " "
            grn_no2 = " "
            grn_no1 = stud_grn['grn']
            if stud_grn['prefix'] == 'static':
                grn_no1 = stud_grn['static_prefix'] + stud_grn['grn']
            elif stud_grn['prefix'] == 'school':
                a = stud_grn.schoolprefix_id.name
                grn_no1 = a + stud_grn['grn']
            elif stud_grn['prefix'] == 'year':
                grn_no1 = time.strftime('%Y') + stud_grn['grn']
            elif stud_grn['prefix'] == 'month':
                grn_no1 = time.strftime('%m') + stud_grn['grn']
            grn_no2 = grn_no1
            if stud_grn['postfix'] == 'static':
                grn_no2 = grn_no1 + stud_grn['static_postfix']
            elif stud_grn['postfix'] == 'school':
                b = stud_grn.schoolpostfix_id.name
                grn_no2 = grn_no1 + b
            elif stud_grn['postfix'] == 'year':
                grn_no2 = grn_no1 + time.strftime('%Y')
            elif stud_grn['postfix'] == 'month':
                grn_no2 = grn_no1 + time.strftime('%m')
            self.grn_no = grn_no2

    grn = fields.Char('GR no', help='General Reg Number', readonly=True,
                      default=lambda obj:
                      obj.env['ir.sequence'].get('student.grn'))
    name = fields.Char('GRN Format Name', required=True)
    prefix = fields.Selection([('school', 'School Name'),
                               ('year', 'Year'), ('month', 'Month'),
                               ('static', 'Static String')], 'Prefix')
    schoolprefix_id = fields.Many2one('res.company',
                                      'School Name For Prefix')
    schoolpostfix_id = fields.Many2one('res.company',
                                       'School Name For Suffix')
    postfix = fields.Selection([('school', 'School Name'),
                                ('year', 'Year'), ('month', 'Month'),
                                ('static', 'Static String')], 'Suffix')
    static_prefix = fields.Char('Static String for Prefix')
    static_postfix = fields.Char('Static String for Suffix')
    grn_no = fields.Char('Generated GR No.', compute='_compute_grn_no')


class MotherTongue(models.Model):
    _name = 'mother.tongue'

    name = fields.Char("Mother Tongue")


class StudentAward(models.Model):
    _name = 'student.award'
    award_list_id = fields.Many2one('school.student', 'School Student')
    name = fields.Char('Award Name')
    description = fields.Char('Description')


class StudentDocument(models.Model):
    _name = 'student.document'
    _rec_name = "doc_type"

    doc_id = fields.Many2one('school.student', 'Related Student')
    file_no = fields.Char('File No', readonly="1", default=lambda obj:
    obj.env['ir.sequence'].get('student.document'))
    submitted_date = fields.Date('Submitted Date')
    doc_type = fields.Many2one('document.type', 'Document Type', required=True)
    file_name = fields.Char('File Name', )
    return_date = fields.Date('Return Date')
    new_datas = fields.Binary('Attachments')


class DocumentType(models.Model):
    _name = "document.type"
    _description = "Document Type"
    _rec_name = "doc_type"
    _order = "seq_no"

    seq_no = fields.Char('Sequence', readonly=True, default=lambda obj:
    obj.env['ir.sequence'].get('document.type'))
    doc_type = fields.Char('Document Type', required=True)


class StudentDiscipline(models.Model):
    _name = 'student.discipline'
    student_id = fields.Many2one('school.student', 'Related Student')
    teacher_id = fields.Many2one('hr.employee', 'Teacher')
    date = fields.Date('Date')
    form_id = fields.Many2one('school.form', 'Form', help='Form')
    class_id = fields.Many2one('school.class', 'Class',help='Class')
    note = fields.Text('Note')
    action_taken = fields.Text('Action Taken')


class StudentDescription(models.Model):
    _name = 'student.description'
    student_id = fields.Many2one('school.student', 'Description')
    name = fields.Char('Name')
    description = fields.Char('Description')


class StudentHistory(models.Model):
    _name = "student.history"
    student_id = fields.Many2one('school.student', 'Related Student')
    academic_year_id = fields.Many2one('school.academic.year', 'Academic Year',
                                       required=True)
    class_id = fields.Many2one('school.class', 'Class')
    form_id = fields.Many2one('school.form', 'Form', help='Form')
    percentage = fields.Float("Percentage", readonly=True)
    result = fields.Char('Result', readonly=True, store=True)


class StudentCertificate(models.Model):
    _name = "student.certificate"
    student_id = fields.Many2one('school.student', 'Related Student')
    description = fields.Char('Description')
    certificate = fields.Binary('Upload Certificate')


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = 'hr.employee'
    _description = 'Teacher Information'

    def _compute_subject(self):
        subject_obj = self.env['school.subject']
        subject_ids = subject_obj.search([('teacher_ids', '=', self.id)])
        sub_list = []
        for sub_rec in subject_ids:
            sub_list.append(sub_rec.id)
        self.subject_ids = sub_list

    subject_ids = fields.Many2many('school.subject', 'hr_employee_rel',
                                   'Subjects', compute='_compute_subject')
    is_school_teacher = fields.Boolean('Is A Teacher')


class StudentReference(models.Model):
    _name = "student.reference"
    _description = "Student Reference"
    student_id = fields.Many2one('school.student', 'Related Student')
    full_name = fields.Char('Full Name', required=True)
    designation = fields.Char('Designation', required=True)
    phone = fields.Char('Phone')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')],
                              'Gender')


class StudentPreviousSchool(models.Model):
    _name = "student.previous.school"
    _description = "Student Previous School"
    previous_school_id = fields.Many2one('school.student', 'Related Student')
    name = fields.Char('Name', required=True, help='Name of the previous school')
    registration_no = fields.Char('Registration No.', help='Registration # or Student ID from previous school ')
    admission_date = fields.Date('Admission Date', help='Date Student gained admission into the previous school')
    exit_date = fields.Date('Exit Date', help='Date Student left the previous school')
    stage = fields.Char('Stage', help='Stage student left the school Eg: Class 3')


class StudentFamilyContact(models.Model):
    _name = "student.family.contact"
    _description = "Student Family Contact"

    family_contact_id = fields.Many2one('school.student', 'Student related to')
    student = fields.Many2one('school.student', 'Student related to')
    rel_name = fields.Selection([('exist', 'Link to Existing Student'),
                                 ('new', 'Create New Relative Name')],
                                'Related Student', help="Select Name",
                                required=True)
    relation_name = fields.Char('Name')
    relation = fields.Many2one('student.relation.master', 'Relation',
                               required=True)
    phone = fields.Char('Phone')
    email = fields.Char('E-Mail')

    @api.depends('family_contact_id')
    def _compute_name(self):
        if self.family_contact_id:
            self.relation_name = self.family_contact_id.name


class GradeMaster(models.Model):
    _name = 'grade.master'

    name = fields.Char('Grade',  required=True)
    grade_ids = fields.One2many('grade.line', 'grade_id', 'Grade Name')


class GradeLine(models.Model):
    _name = 'grade.line'

    from_mark = fields.Integer('From Marks', required=True,
                               help='The grade will starts from this marks.')
    to_mark = fields.Integer('To Marks', required=True,
                             help='The grade will ends to this marks.')
    grade = fields.Char('Grade', required=True, help="Grade")
    sequence = fields.Integer('Sequence', help="Sequence order of the grade.")
    fail = fields.Boolean('Fail', help='If fail field is set to True,\
                                  it will allow you to set the grade as fail.')
    grade_id = fields.Many2one("grade.master", 'Grade')
    name = fields.Char('Name')


class StudentNews(models.Model):
    _name = 'student.news'
    _description = 'Student News'
    _rec_name = 'subject'

    subject = fields.Char('Subject', required=True,
                          help='Subject of the news.')
    description = fields.Text('Description', help="Description")
    date = fields.Datetime('Expiry Date', help='Expiry date of the news.')
    user_ids = fields.Many2many('res.users', 'user_news_rel', 'id', 'user_ids',
                                'User News',
                                help='Name to whom this news is related.')
    color = fields.Integer('Color Index', default=0)

    @api.multi
    def news_update(self):
        emp_obj = self.env['hr.employee']
        obj_mail_server = self.env['ir.mail_server']
        mail_server_ids = obj_mail_server.search([])
        if not mail_server_ids:
            raise ValidationError('Mail Error No mail outgoing mail server specified!')
        mail_server_record = mail_server_ids[0]
        email_list = []
        for news in self:
            if news.user_ids:
                for user in news.user_ids:
                    if user.email:
                        email_list.append(user.email)
                if not email_list:
                    raise ValidationError("User Email Configuration Email not found in users !")
            else:
                for employee in emp_obj.search([]):
                    if employee.work_email:
                        email_list.append(employee.work_email)
                    elif employee.user_id and employee.user_id.email:
                        email_list.append(employee.user_id.email)
                if not email_list:
                    raise ValidationError('Mail Error Email not defined!')
            t = datetime.strptime(news.date, '%Y-%m-%d %H:%M:%S')
            body = 'Hi,<br/><br/> \
                    This is a news update from <b>%s</b>posted at %s<br/><br/>\
                    %s <br/><br/>\
                    Thank you.' % (self._cr.dbname,
                                   t.strftime('%d-%m-%Y %H:%M:%S'),
                                   news.description)
            smtp_user = mail_server_record.smtp_user
            notification = 'Notification for news update.'
            message = obj_mail_server.build_email(email_from=smtp_user,
                                                  email_to=email_list,
                                                  subject=notification,
                                                  body=body,
                                                  body_alternative=body,
                                                  email_cc=None,
                                                  email_bcc=None,
                                                  reply_to=smtp_user,
                                                  attachments=None,
                                                  references=None,
                                                  object_id=None,
                                                  subtype='html',
                                                  subtype_alternative=None,
                                                  headers=None)
            obj_mail_server.send_email(message=message,
                                       mail_server_id=mail_server_ids[0].id)
        return True


class StudentReminder(models.Model):
    _name = 'student.reminder'

    stu_id = fields.Many2one('school.student', 'Student Name', required=True)
    name = fields.Char('Title')
    date = fields.Date('Date')
    description = fields.Text('Description')
    color = fields.Integer('Color Index', default=0)


class StudentCast(models.Model):
    _name = "student.cast"
    name = fields.Char("Name", required=True)


class ResUsers(models.Model):
    _inherit = 'res.users'
    related_parent_id = fields.Many2one('school.parent')

    @api.model
    def create(self, vals):
        vals.update({'employee_ids': False})
        res = super(ResUsers, self).create(vals)
        return res


class ResPartner(models.Model):
    _inherit = 'res.partner'
    student_id = fields.Many2one('school.student', 'Related Student')
    parent_id = fields.Many2one('school.parent')
