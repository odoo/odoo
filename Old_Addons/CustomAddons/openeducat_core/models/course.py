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


class OpCourse(models.Model):
    _name = 'op.course'
    _order = 'code'
    name = fields.Char('Pavadinimas', size=64, required=True)
    code = fields.Char('Kodas', size=8, required=True)
 #   cathedral_id = fields.One2many('op.cathedral', size=32, required=True)
 #   xbatch_ids= fields.One2many('op.batch', string='Studijų programo grupės' ) ##MaNY TO MANY???
    subject_ids = fields.Many2many('op.subject', string='Studijų programos dalykai') ##MANY TO MANY?
    pakopa = fields.Selection(
        [('pirmoji', 'Pirmoji'), ('antroji', 'Antroji'), ('pokol','Pokoleginės')],
        'Pakopa', default= "pirmoji", required= True)
    active = fields.Boolean('Aktyvus', default= True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
