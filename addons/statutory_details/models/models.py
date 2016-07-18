# -*- coding: utf-8 -*-

from openerp import models, fields, api

class statutory_details(models.Model):
	_inherit = 'res.partner'

	ecc_trading = fields.Char('ECC No. (Trading)', default = '')
	ecc_manufacturing = fields.Char('ECC No. (Manufacturing)', default = '')
	tin_no = fields.Char('TIN No.', default = '')
	service_tax_no = fields.Char('Service Tax No.', default = '')
	pan_no = fields.Char('Pan No.', default = '')
	


    # _inherit = 'res.partner'

    # tin = fields.Char()
    # ecc = fields.Char()

    

    # @api.depends('value')
    # def _value_pc(self):
    #     self.value2 = float(self.value) / 100