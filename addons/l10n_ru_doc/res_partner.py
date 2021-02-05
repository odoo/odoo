# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo
#    Copyright (C) 2014-2018 CodUP (<http://codup.com>).
#
##############################################################################

from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    inn = fields.Char('INN', size=12)
    kpp = fields.Char('KPP', size=9)
    okpo = fields.Char('OKPO', size=14)
