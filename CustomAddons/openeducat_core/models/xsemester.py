# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.exceptions import ValidationError
import time
class Op_Xsemester(models.Model):
    _name = 'op.xsemester'
    _rec_name = 'pavadinimas'
 #   x_state = fields.Boolean('Aktyvus')
    pavadinimas = fields.Char('Pavadinimas', size=64 , required= True)
    start_date = fields.Date(
        'Semestro pradžios data', required=True, default=time.strftime('%Y-%m-28'))
    end_date = fields.Date(
        'Semestro pabaigos data', required=True, default=time.strftime('%Y-%m-28'))
    exam_start_date = fields.Date(
        'Sesijos pradžios data', required=True, default= time.strftime('%Y-%m-28') )
    exam_end_date = fields.Date(
        'Sesijos pabaigos data', required=True , default = time.strftime('%Y-%m-28')  )
    sezonas = fields.Selection(
        [('rudens' , 'Rudens'),('pavasario' , 'Pavasario')], 'Semestro sezonas', required= True)
    active = fields.Boolean('Aktyvus', default= True)
    einamasis = fields.Boolean('Einamasis', default = False)
    sekantis = fields.Boolean ('Sekantis', default = False)
    @api.constrains('start_datetime', 'end_datetime')
    def _check_date_time(self):
        if self.start_datetime > self.end_datetime:
            raise ValidationError(
                'End Time cannot be set before Start Time.')
            
    @api.constrains('exam_start_datetime', 'exam_end_datetime')
    def _check_date_time2(self):
        if self.exam_start_datetime > self.exam_end_datetime:
            raise ValidationError(
                'End Time cannot be set before Start Time.')   
#    subject_ids =fields.Many2many('op.subject' , 'semestras_dalykas')
#    faculty_ids = fields.Many2many('op.faculty', 'semestras_destytojas')
#    batch_ids = fields.Many2many('op.batch', 'semestras_grupe')
    #exams_ids
class OP_Xsemester_faculty(models.Model):
    _name = 'op.xsemester_faculty'
    _desciption = "Semestro dėstytojai"

    xsemester_id = fields.Many2one('op.xsemester','Semestras' , required=True , default=1)
    faculty_id = fields.Many2one('op.faculty', 'Dėstytojas' , required = True)
    
class OP_Xsemester_subject(models.Model):
    _name = 'op.xsemester.subject'
    _description = "Semestro dalykai"
    
    xsemester_id = fields.Many2one('op.xsemester', 'Semestras', required = True)
    subject_id = fields.Many2one('op.subject', 'Dalykas', required= True)
    exam= fields.Boolean('Egzaminas paskirtas')
    
    
        
