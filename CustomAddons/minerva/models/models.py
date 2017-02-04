# -*- coding: utf-8 -*-

from openerp import models, fields, api

class minerva(models.Model):
    _name = 'minerva.minerva'

    xsemester_id = fields.Many2one('op.xsemester', 'Semestras')
    faculty_id = fields.Many2one('op.faculty', 'Destytojas')
    #faculty_name = fields.Char(related='opfaculty_id.name')
    batch_id = fields.Many2one('op.batch', 'Grupe')
    subject_id = fields.Many2one('op.subject', 'Dalykas')
    classroom_id = fields.Many2one('op.classroom', 'Auditorija') 
    period_id = fields.Many2one('op.period', 'Paskaitos laikas')
    day = fields.Selection(
        [('1', 'Pirmadienis'), ('2', 'Antradienis'),
         ('3', 'Trečiadienis'), ('4', 'Ketvirtadienis'),
         ('5', 'Penktadienis'), ('6', 'Šeštadienis')], 'Diena')
    week = fields.Selection(
        [('1' , 'Pirma'), ('2', 'Antra') , ('0' , 'Abi')], 'Savaite' , default='0' , required=True)
    
    note= fields.Char('Komentaras' , size=128)
    name = fields.Char()
    value = fields.Integer()
    value2 = fields.Float(compute="_value_pc", store=True)
    description = fields.Text()

    @api.depends('value')
    def _value_pc(self):
        self.value2 = float(self.value) / 100