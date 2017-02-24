# -*- coding: utf-8 -*-
###############################################################################
from openerp import models, fields, api
from openerp.exceptions import ValidationError



class OpCathedral(models.Model):
    _name = 'op.cathedral'
    
    
    name = fields.Char('Pavadinimas', size=64, required=True)
 #   destytojai= fields.One2many('op.cathedral' , 'Dėstytjai')