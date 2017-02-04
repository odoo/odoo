# -*- coding: utf-8 -*-
###############################################################################
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2009-TODAY Tech-Receptives(<http://www.techreceptives.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from openerp import models, fields


class OpClassroom(models.Model):
    _name = 'op.classroom'
    _rec_name = 'code'
    _order = 'code'

    name = fields.Char('Pavadinimas', size=32, required=True)
    code = fields.Char('Trumpinys', size=12, required=True)
    # course_id = fields.Many2one('op.course', 'Course', required=False)
    xcomputers = fields.Integer(string= 'Kompiuterinės darbo vietos')
    xmultimedia = fields.Boolean (string = "Multimedia")
    capacity = fields.Integer(string='Žmonių skaičius')
    facilities = fields.One2many(
        'op.facility.line', 'classroom_id', string='Auditorijos įranga')
    active= fields.Boolean(string ='Aktyvus' , default=True)


class OP_Classroom_facillity(models.Model):
    _name = 'op.classroom.facility'
    _description = "Klases iranga"

    classroom_id = fields.Many2one('op.classroom', 'Auditorija', required=True)
    facility_id = fields.Many2one('op.facility', 'Iranga', required=True)
    vnt = fields.Integer('Vnt.')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
