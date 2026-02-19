# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions  (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
import math
import re
import base64
from datetime import date
from barcode import EAN13
from barcode.writer import ImageWriter
from dateutil.relativedelta import *
from odoo import api, fields, models


class ResPartner(models.Model):
    """Inherited to add more fields and functions"""
    _inherit = 'res.partner'
    _description = 'Hospital Patients'

    date_of_birth = fields.Date(string='Date of Birth',
                                help='Date of birth of the patient')
    blood_group = fields.Selection(string='Blood Group',
                                   help='Blood group of the patient',
                                   selection=[('a', 'A'), ('b', 'B'),
                                              ('o', 'O'), ('ab', 'AB')])
    rh_type = fields.Selection(selection=[('-', '-ve'), ('+', '+ve')],
                               string='RH Type',
                               help='Rh type of the blood group')
    gender = fields.Selection(selection=[
        ('male', 'Male'), ('female', 'Female'), ('other', 'Other')
    ], string='Gender', help='Gender of the patient')
    marital_status = fields.Selection(selection=[
        ('married', 'Married'), ('unmarried', 'Unmarried'), ('widow', 'Widow'),
        ('widower', 'Widower'), ('divorcee', 'Divorcee')
    ], string='Marital Status', help='Marital status of patient')
    is_alive = fields.Selection(
        string='Status',
        selection=[('alive', 'Alive'), ('dead', 'Dead')],
        default='alive', help='True for alive patient')
    patient_seq = fields.Char(string='Patient No.',
                              help='Sequence number of the patient', copy=False,
                              readonly=True, index=True,
                              default=lambda self: 'New')
    notes = fields.Html(string='Note', help='Notes regarding the notes',
                        sanitize_style=True)
    patient_profession = fields.Char(string="Profession",
                                     help="Profession of patient")
    doctor_id = fields.Many2one('hr.employee',
                                domain=[('job_id.name', '=', 'Doctor')],
                                string="Family Doctor",
                                help='Family doctor of the patient')
    barcode = fields.Char(string='Barcode', help='Barcode for the patient')
    barcode_png = fields.Binary(string='Barcode PNG',
                                help='Image file of the barcode', readonly=True)
    group = fields.Selection(selection=[
        ('hindu', 'Hindu'), ('muslim', 'Muslim'), ('christian', 'Christian')],
        string="Ethnic Group", help="Specify your religion")
    risk = fields.Text(string="Genetic Risks",
                       help='Genetic risks of the patient')
    insurance_id = fields.Many2one('hospital.insurance',
                                   string="Insurance",
                                   help="Patient insurance")
    unique_id = fields.Char(string='Unique ID',
                            help="Unique identifier to fetch "
                                 "patient insurance data")
    family_ids = fields.One2many('hospital.family',
                                 'family_id',
                                 string="Family ID", help='Family of a patient')
    lab_test_ids = fields.One2many('patient.lab.test',
                                   'patient_id',
                                   string='Lab Test',
                                   help='Lab tests for the patient')
    prescription_ids = fields.One2many('prescription.line',
                                       'res_partner_id',
                                       string='Prescription',
                                       help='Prescription for patient')
    economic_level = fields.Selection(selection=[
        ('low', 'Lower Class'), ('middle', 'Middle Class'),
        ('upper', 'Upper Class')], string="Socioeconomic",
        help="Specify your economic status")
    education_level = fields.Selection(selection=[
        ('post', 'Post Graduation'), ('graduation', 'Graduation'),
        ('pre', 'Pre Graduation')], string="Education Level",
        help="Education status of patient")
    house_level = fields.Selection(selection=[
        ('good', 'Good'), ('bad', 'Bad'), ('poor', 'Poor')],
        string="House Condition", help="Specify your house's condition")
    work_home = fields.Boolean(string='Work At Home',
                               help='True if you are working from home')
    hours_outside = fields.Integer(string='Hours Stay Outside Home',
                                   help="Specify how many hours you stay away "
                                        "from home")
    hostile = fields.Boolean(string='Hostile Area',
                             help="Specify your house in a friendly "
                                  "neighbourhood ")
    income = fields.Monetary(string='Income', help="The in come of patient")
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  help='Currency in which invoices and payments'
                                       ' will be generated',
                                  default=lambda self: self.env.user.company_id
                                  .currency_id.id, required=True)
    sanitary = fields.Boolean('Sanitary Sewers',
                              help="A sewer or sewer system for carrying off "
                                   "wastewater, waste matter from a residence,"
                                   " business, etc")
    running = fields.Boolean(string='Running Water',
                             help="water that comes into a building through "
                                  "pipes. A cabin with hot and cold running "
                                  "water.")
    electricity = fields.Boolean(string='Electricity',
                                 help='True if you have electricity')
    gas = fields.Boolean(string='Gas Supply',
                         help='True if you have gas supply')
    trash = fields.Boolean(string='Trash Collection',
                           help='True if you have trash collection')
    home_phone = fields.Boolean(string='Telephone',
                                help='True if you have telephone')
    tv = fields.Boolean(string='Television', help='True if you have television')
    internet = fields.Boolean(string='Internet',
                              help='True if you have internet')
    help = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                            string="Family Help",
                            help="Specify whether your family is willing "
                                 "to help or not")
    discussion = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                  string="Family Discussion ",
                                  help="Specify your family have a good "
                                       "discussion at home ")
    ability = fields.Selection([('very', 'Very good'), ('good', 'Good'),
                                ('bad', 'Bad'), ('poor', 'Poor')],
                               string="Family Ability",
                               help="family status of the patient")
    time_sharing = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                    string=" Family Time Sharing ",
                                    help="Specify your family share time "
                                         "at home ")
    affection = fields.Selection([('very', 'Very good'),
                                  ('good', 'Good'),
                                  ('bad', 'Bad'), ('poor', 'Poor')],
                                 string="Family Affection ",
                                 help="Specify your family's affection ")
    single = fields.Boolean(string='Single Parent Family',
                            help='Whether single parent family or not')
    violence = fields.Boolean(string='Domestic Violence',
                              help='True if you are facing any domestic '
                                   'violence')
    children = fields.Boolean(string='Working Children',
                              help='Do you have working children')
    abuse = fields.Boolean(string='Sexual Abuse',
                           help='Do you faced any sexual abuse')
    drug = fields.Boolean(string='Drug Addiction',
                          help='Do you have drug addiction')
    withdrawal = fields.Boolean(string='Withdrawal',
                                help='Do you faced any withdrawal symptoms')
    in_prison = fields.Boolean(string='Has Been In Prison',
                               help='True if you had been in prison')
    current_prison = fields.Boolean(string='Currently In Prison',
                                    help='True if you are in prison currently')
    relative_prison = fields.Boolean(string='Relative In Prison',
                                     help='True if any of your relative is '
                                          'in prison')
    hospital_vaccination_ids = fields.One2many(
        'hospital.vaccination', 'patient_id',
        string='Vaccination', help='Vaccination details of '
                                   'patient')
    fertile = fields.Boolean(string='Fertile', help="""Capable of developing 
                                             into a complete organism; 
                                             fertilized. Capable of supporting 
                                             plant life; favorable to the 
                                             growth of crops and plants.""")
    menarche_age = fields.Integer(string='Menarche Age', help="""The first 
                                     menstrual period in a female adolescent""")
    pause = fields.Boolean(string='Menopause', help="""Menopause is a point in 
                                 time 12 months after a woman's last period""")
    pause_age = fields.Integer(string='Menopause Age',
                               help='Age at which menopause occurred')
    pap = fields.Boolean(string='PAP Test',
                         help="""
                         A procedure in which a small brush is used to gently 
                         remove cells from the surface of the cervix and the 
                         area around it so they can be checked under a 
                         microscope for cervical cancer or cell changes that
                         may lead to cervical cancer.""")
    colposcopy = fields.Boolean(string='Colposcopy', help=""" test to take a
                            closer look at your cervix""")
    self = fields.Boolean(string='Self breast examination',
                          help="A breast self-exam for breast awareness is "
                               "in inspection "
                               "of your breasts that women do on your own")
    mommography = fields.Boolean(string='Mommography',
                                 help="Mammograms can be used to look for "
                                      "breast cancer")
    last_pap = fields.Date(string="Last PAP Test",
                           help='The date on which last PAP test has been done')
    last_col = fields.Date(string="Last Colposcopy",
                           help='The date on which last colposcopy has been '
                                'done')
    deceased = fields.Boolean(string='Deceased during 1st week',
                              help='The family member deceased during first '
                                   'week')
    grandiva = fields.Boolean(string='Grandiva', help='True for grandiva')
    alive = fields.Boolean(string='Born Alive', help='Whether born alive or '
                                                     'not')
    premature = fields.Integer(string='Premature',
                               help="Premature birth is birth that happens too"
                                    "soon, before 37 weeks of pregnancy")
    abortions = fields.Integer(string='No Of Abortions', help='Number of '
                                                              'abortions of '
                                                              'patient')
    exercise = fields.Boolean(string='Exercise', help='True if patient doing '
                                                      'exercise regularly')
    minute = fields.Integer(string='Minute/Day', help='The duration of '
                                                      'exercise per day')

    day_sleep = fields.Boolean(string='Sleeps At Daytime', help='True if '
                                                                'sleeps at '
                                                                'daytime')
    sleep_hrs = fields.Integer(string='Sleep Hours', help='Duration of sleep')
    meals = fields.Integer(string='Meals/Day', help='Number of meals per day')
    alone = fields.Boolean(string='Eat Alone', help='True if eats alone')
    coffee = fields.Boolean(string='Coffee', help='True if you have a habit '
                                                  'of drinking coffee')
    cup = fields.Integer(string='Cups/Day', help='Number of cups of coffee '
                                                 'per day')
    drink = fields.Boolean(string='Soft Drink', help='True if you drinks soft '
                                                     'drinks')
    salt = fields.Boolean(string='Salt', help='True if you use salt')
    diet = fields.Boolean(string='Currently On Diet', help='True if you are '
                                                           'on diet currently')
    smoke = fields.Boolean(string='Smoker', help='True for smoker')
    ex_smoke = fields.Boolean(string='Ex-Smoker', help='True for ex-smoker')
    age_start = fields.Integer(string='Age of Started Smoking',
                               help='Age on which you started your smoking')
    cigarettes = fields.Integer(string='Cigarettes/Day',
                                help='Number of cigarettes per day')
    passive = fields.Boolean(string='Passive Smoker',
                             help='True for passive smokers')
    age_quit = fields.Integer(string='Age of Quitting',
                              help='Age at which you quit your smoking habit')
    alcoholic = fields.Boolean(string='Alcoholic', help='True for alcoholics')
    ex_alcoholic = fields.Boolean(string='Ex-Alcoholic', help='True for ex- '
                                                              'alcoholics')
    age_start_alco = fields.Integer(string='Age to Start Drinking',
                                    help='Age at which you started your '
                                         'drinking habit')
    beer = fields.Integer(string='Beer/Day',
                          help='Number of beers per day')
    liquor = fields.Integer(string='Liquor/Day',
                            help='Liquors per day')
    wine = fields.Integer(string='Wine/Day',
                          help='Number of wines per day')
    age_quit_alcoholic = fields.Integer(string='Age Of Quitting',
                                        help='Age at which you started your '
                                             'drinking habit')
    drugs = fields.Boolean(string='Drug User', help='True for drug users')
    ex_drugs = fields.Boolean(string='Ex-Drug User', help='True for Ex drug '
                                                          'user')
    iv_user = fields.Boolean(string='IV Drug User', help='True for IV drug '
                                                         'user')
    age_start_drug = fields.Integer(string='Age to Start Using Drugs',
                                    help='Age at which you started using drug')
    age_quit_drug = fields.Integer(string='Drug Quitting Age', help='Age of '
                                                                    'quitting '
                                                                    'drug')
    orientation = fields.Selection([('straight', 'Straight'),
                                    ('homo', 'Homosexual'),
                                    ('trans', 'Trans-Gender')],
                                   string="Orientation")
    age_sex = fields.Integer(string="Age of First Encounter",
                             help='Age of first sex encounter')
    partners = fields.Integer(string="No of Partners",
                              help='Number of sex partners')
    anti = fields.Selection(
        [('pills', 'Contraceptive Pills'), ('ring', 'Contraceptive Ring'),
         ('injection', 'Contraceptive Injection')],
        string="Contraceptive Methods", help='Choose your contraceptive method')
    oral = fields.Boolean(string='Oral Sex', help=("uttered by the mouth or in "
                                                   "words"))
    anal = fields.Boolean(string='Anal Sex', help="True if you are "
                                                  "encountering anal sex")
    prostitute = fields.Boolean(string='Prostitute', help='True for '
                                                          'prostitutes')
    prostitute_sex = fields.Boolean(string='Sex With Prostitute',
                                    help='True if you are encountered sex '
                                         'with prostitute')
    sex_notes = fields.Text(string='Notes', help='Write down the notes')
    rider = fields.Boolean(string='Motorcycle Rider', help='True for '
                                                           'motorcycle riders')
    helmet = fields.Boolean(string='Uses Helmet',
                            help='True if you regularly use helmet')
    laws = fields.Boolean(string='Obey Traffic Laws',
                          help='True if you obey traffic rules')
    revision = fields.Boolean(string='Car Revision', help='True if car '
                                                          'revision is done')
    belt = fields.Boolean(string='Seat Belt',
                          help='True if you uses seat belt regularly')
    safety = fields.Boolean(string='Car Child Safety',
                            help='True if you have car child safety')
    home = fields.Boolean(string='Home Safety', help='True for home safety')
    occupation = fields.Char(string='Occupation', help='Your occupation')

    @api.model
    def create(self, vals):
        """Inherits create function for sequence generation"""
        if vals.get('patient_seq', 'New') == 'New':
            vals['patient_seq'] = self.env['ir.sequence'].next_by_code(
                'patient.sequence') or 'New'
        return super().create(vals)

    def action_view_invoice(self):
        """Returns patient invoice"""
        self.ensure_one()
        return {
            'name': 'Patient Invoice',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('partner_id', '=', self.id)],
            'context': "{'create':False}"
        }

    def fetch_view_id(self):
        """Returns the view id of patient"""
        return self.env['ir.ui.view'].sudo().search([
            ('name', '=', 'hospital.patient.view.form')]).id

    def name_get(self):
        """Returns the patient name"""
        result = []
        for rec in self:
            result.append((rec.id, f'{rec.patient_seq} - {rec.name}'))
        return result

    def alive_status(self):
        """Function for setting the value of is_alive field"""
        if self.is_alive == 'alive':
            self.is_alive = 'dead'
        else:
            self.is_alive = 'alive'

    def action_schedule(self):
        """Returns form view of hospital appointment wizard"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.outpatient',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'views': [[False, 'form']],
            'context': {
                'default_patient_id': self.id
            }
        }

    @api.model
    def ean_checksum(self, eancode):
        """Returns the checksum of an ean string of length 13, returns -1 if
            the string has the wrong length"""
        if len(eancode) != 13:
            return -1
        odd_sum = 0
        even_sum = 0
        ean_value = eancode
        reverse_value = ean_value[::-1]
        final_ean = reverse_value[1:]
        for i in range(len(final_ean)):
            if i % 2 == 0:
                odd_sum += int(final_ean[i])
            else:
                even_sum += int(final_ean[i])
        total = (odd_sum * 3) + even_sum
        check = int(10 - math.ceil(total % 10.0)) % 10
        return check

    def check_ean(eancode):
        """Returns True if eancode is a valid ean13 string, or null"""
        if not eancode:
            return True
        if len(eancode) != 13:
            return False
        int(eancode)
        return eancode.ean_checksum(eancode) == int(eancode[-1])

    def generate_ean(self, ean):
        """Creates and returns a valid ean13 from an invalid one"""
        if not ean:
            return "0000000000000"
        ean = re.sub("[A-Za-z]", "0", ean)
        ean = re.sub("[^0-9]", "", ean)
        ean = ean[:13]
        if len(ean) < 13:
            ean = ean + '0' * (13 - len(ean))
            return ean[:-1] + str(self.ean_checksum(ean))

    def action_generate_patient_card(self):
        """Method for generating the patient card"""
        current_age = 0
        gender_caps = ''
        blood_caps = ''
        if not self.barcode:
            ean = self.sudo().generate_ean(str(self.id))
            self.sudo().write({'barcode': ean})
            number = self.barcode
            my_code = EAN13(number, writer=ImageWriter())
            my_code.save("code")
            with open('code.png', 'rb') as f:
                self.sudo().write({
                    'barcode_png': base64.b64encode(f.read())
                })
        if self.gender:
            gender_caps = self.gender.capitalize()
        if self.blood_group:
            blood_caps = self.blood_group.capitalize()
        if self.date_of_birth:
            today = date.today()
            dob = self.date_of_birth
            current_age = relativedelta(today, dob).years
        company = self.env['res.company'].sudo().search(
            [('id', '=', self.env.context['allowed_company_ids'])])
        data = {
            'name': self.name,
            'code': self.patient_seq,
            'age': current_age,
            'gender': gender_caps,
            'dob': self.date_of_birth,
            'blood': blood_caps + str(self.rh_type),
            'street': self.street,
            'street2': self.street2,
            'state': self.state_id.name,
            'country': self.country_id.name,
            'city': self.city,
            'phone': self.phone,
            'image': self.sudo().read(['image_1920'])[0],
            'barcode': self.sudo().read(['barcode_png'])[0],
            'company_name': company.name,
            'company_street': company.street,
            'company_street2': company.street2,
            'company_city': company.city,
            'company_state': company.state_id.name,
            'company_zip': company.zip,
        }
        return self.env.ref(
            'base_hospital_management.action_report_patient_card'
        ).report_action(None, data=data)

    @api.model
    def reception_op_barcode(self, kw):
        """Returns a patient based on the barcode"""
        values = {
            'name': '',
            'date_of_birth': '',
            'phone': '',
            'blood_group': '',
            'gender': '',
        }
        if kw['patient_data']:
            patient = self.sudo().search(
                ['|', ('patient_seq', '=', kw['patient_data']),
                 ('phone', '=', kw['patient_data'])])
            if patient:
                values = {
                    'name': patient.name,
                    'date_of_birth': patient.date_of_birth,
                    'phone': patient.phone,
                    'blood_group': patient.blood_group,
                    'gender': patient.gender,
                }
        return values

    @api.model
    def reception_op_phone(self, phone):
        """Returns a patient details having the phone number"""
        patient_phone = self.sudo().search(
            [('phone', '=', phone['patient-phone'])])
        values = {
            'patient_seq': patient_phone.patient_seq,
            'name': patient_phone.name,
            'date_of_birth': patient_phone.date_of_birth,
            'blood_group': patient_phone.blood_group,
            'gender': patient_phone.gender,
        }
        return values

    @api.model
    def action_get_patient_data(self, patient_id):
        """Method which returns patient details"""
        data = self.sudo().search([
            '|', ('patient_seq', '=', patient_id.upper()),
            ('barcode', '=', patient_id)
        ])
        patient_history = []
        for rec in self.env['hospital.outpatient'].sudo().search(
                [('patient_id', '=', data.id)]):
            patient_history.append(
                [rec.op_reference, str(rec.op_date),
                 rec.doctor_id.doctor_id.name])
        values = {
            'name': data.name,
            'unique': data.patient_seq,
            'email': data.email,
            'phone': data.phone,
            'dob': data.date_of_birth,
            'image_1920': data.image_1920,
            'status': data.marital_status,
            'history': patient_history,
        }
        if not data.name:
            values['name'] = 'Patient Not Found'
        if not data.patient_seq:
            values['unique'] = ''
        if data.blood_group:
            blood_caps = data.blood_group.capitalize()
            values['blood_group'] = blood_caps + str(data.rh_type)
        else:
            values['blood_group'] = ''
        if data.gender:
            gender_caps = data.gender.capitalize()
            values['gender'] = gender_caps
        else:
            values['gender'] = ''
        return values

    @api.model
    def create_sale_order_pharmacy(self, order):
        """Method for creating sale order for medicines"""
        medicine = []
        op_record = self.env['hospital.outpatient'].sudo().search(
            [('op_reference', '=', order), '|',
             ('active', 'in', [False, True])])
        for rec in op_record.prescription_ids:
            medicine.append([rec.medicine_id.id, rec.quantity])
        sale_order_pharmacy = self.env['sale.order'].sudo().create({
            'partner_id': op_record.patient_id.id,
        })
        for new in medicine:
            self.env['sale.order.line'].sudo().create({
                'product_id': new[0],
                'product_uom_qty': new[1],
                'order_id': sale_order_pharmacy.id,
            })

    @api.model
    def create_patient(self, post):
        """Method for creating a patient"""
        if post and not post['id']:
            patient = self.sudo().create({
                'name': post['op_name'],
                'blood_group': post['op_blood_group'],
                'gender': post['op_gender']
            })
            if 'op_dob' in post.keys():
                patient.sudo().write({'date_of_birth': post['op_dob']})
        else:
            patient = self.sudo().search([('patient_seq', '=', post['id'])])
        self.env['hospital.outpatient'].sudo().create({
            'patient_id': patient.id,
            'op_date': post['date'],
            'reason': post['reason'],
            'slot': post['slot'],
            'doctor_id': self.env['doctor.allocation'].sudo().browse(
                post['doctor']).id
        })

    def fetch_patient_data(self):
        """Method for returning patient data"""
        return self.sudo().search_read(
            [('patient_seq', 'not in', ['New', 'Employee', 'User'])])
