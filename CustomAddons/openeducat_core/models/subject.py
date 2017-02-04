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


class OpSubject(models.Model):
    _name = 'op.subject'
    _order = 'name'

    name = fields.Char('Pavadinimas', size=128, required=True)
    course_id = fields.Many2one('op.course', 'Course')
    type = fields.Selection(
        [('privalomas', 'Privalomas'), ('pasirenkamas', 'Pasirenkamas'),
         ('laisvas', 'Laisvas'), ('kita', 'Kitas')],
        'Tipas', default="privalomas", required=True)
    xsemester_id = fields.Many2many('op.xsemester', 'semestras_dalykai')
    active = fields.Boolean('Aktyvus', default= True)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
