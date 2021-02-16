# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api
from math import floor


class Student(models.Model):
    _name = 'rfp.student'
    _description = 'Student Data'


    name = fields.Char(string='Student Name', size=20, required=True)
    about = fields.Text(string='About', size=200, required=True)
    dob = fields.Date(string='Birthdate', required=True)
    age = fields.Integer('Age', compute='_compute_age', default=0, store=True)
    subject = fields.Many2many('rfp.subject','student_subject_rel', string="Subject")
    course = fields.Many2one('rfp.courses', string="Courses")

    @api.depends('dob')
    def _compute_age(self):
        for i in self:
            if i.dob:
                current_day = date.today()
                year = floor(abs((current_day - i.dob).days) / 365)
                self.write({
                    'age': year,
                })

    @api.onchange('course')
    def onchange_subject_action(self):
        for rec in self:
            rec.subject = rec.course.subject_ids

'''
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'),
                              ('cancel', 'Cancel')], required=True, default='draft')
    
    def button_done(self):
        for _ in self:
            self.write({
                'state': 'done'
            })

    def button_reset(self):
        for _ in self:
            self.write({
                'state': 'draft'
            })

    def button_cancel(self):
        for _ in self:
            self.write({
                'state': 'cancel'
            })
<!--                <header>-->
<!--                    <button class="oe_highlight" name="button_done" states="draft" string="Done" type="object"/>-->
<!--                    <button class="oe_highlight" name="button_reset" states="done,cancel" string="Reset to Draft" type="object"/>-->
<!--                    <button name="button_cancel" states="draft,done" string="Cancel" type="object"/>-->
<!--                    <field name="state" statusbar_visible="draft,done" widget="statusbar"/>-->
<!--                </header>-->
'''
