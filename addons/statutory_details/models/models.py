# -*- coding: utf-8 -*-

from openerp import models, fields, api

class statutory_details(models.Model):
	_inherit = 'sale.order'

	mycustomfield1 = fields.Char('My custom field 1 Label', default = 'My custom field 1 default value')


    # _inherit = 'res.partner'

    # tin = fields.Char()
    # ecc = fields.Char()

    

    # @api.depends('value')
    # def _value_pc(self):
    #     self.value2 = float(self.value) / 100