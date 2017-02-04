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

from openerp import models, fields, api
from openerp.exceptions import ValidationError


class OpFaculty(models.Model):
    _name = 'op.faculty'
    _rec_name= 'name'
    _order = 'name'

    first_name = fields.Char('Vardas', size=128, required= True)
    last_name = fields.Char('Pavardė', size=128, required=True)
    name = fields.Char(compute='comp_name', store=True)
    edu_title = fields.Selection(
        [('doc.','doc.'), ('lekt.','lekt.'), ('prof.','prof.'), ('dr.', 'dr.')],'Akademinis laipsnis', required=True)                         
    pageidavimai=fields.Text('Pageidavimai')
    birth_date = fields.Date('Gimimo data')
    nationality = fields.Many2one('res.country', 'Tautybė')
    photo = fields.Binary('Nuotrauka')
    active = fields.Boolean('Aktyvus', default= True)
   
    email= fields.Char(compute="_on_create_com_email", store=True, string='El. Paštas' )
    mobile= fields.Char('Mobilus tel.' , size= 12)
    phone=fields.Char('Darbo tel. nr.' , size=12) 
   
    @api.depends('first_name','last_name', 'edu_title')
    def comp_name(self):
        self.name = (self.last_name or '')+'.'+(self.first_name[0][0] or '')+ '.,'+ (self.edu_title)
    
    @api.constrains('first_name','last_name')
    def _on_create_com_name(self):
        self.name = (self.last_name or '')+'.'+(self.first_name[0][0] or '')+ '.,'+ (self.edu_title)  
    
    @api.constrains('first_name', 'last_name')
    def _on_create_com_email(self):
        self.email = self.first_name +'.'+ self.last_name+ '@khf.vu.lt'  

    @api.constrains('birth_date')
    def _check_birthdate(self):
        if self.birth_date > fields.Date.today():
            raise ValidationError(
                "Gimimo data negali būti vėlesnė nei šiandien diena!")



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
