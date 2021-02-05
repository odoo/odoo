# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo
#    Copyright (C) 2014-2018 CodUP (<http://codup.com>).
#
##############################################################################

from odoo import api, fields, models

class Company(models.Model):
    _inherit = 'res.company'

    inn = fields.Char(related='partner_id.inn', readonly=False)
    kpp = fields.Char(related='partner_id.kpp', readonly=False)
    okpo = fields.Char(related='partner_id.okpo', readonly=False)
    chief_id = fields.Many2one('res.users', 'Chief')
    accountant_id = fields.Many2one('res.users', 'General Accountant')
    print_facsimile = fields.Boolean('Print Facsimile', help="Check this for adding Facsimiles of responsible persons to documents.")
    print_stamp = fields.Boolean('Print Stamp', help="Check this for adding Stamp of company to documents.")
    stamp = fields.Binary("Stamp")
    print_anywhere = fields.Boolean('Print Anywhere', help="Uncheck this, if you want add Facsimile and Stamp only in email.", default=True)
