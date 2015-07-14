# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

class ke_res_company(models.Model):
	_inherit = ["res.company"]
	
	facebook = fields.Char('Facebook Id')
	twitter = fields.Char('Twitter Handle')
	googleplus = fields.Char('Google-Plus Id')
	

