# -*- coding: utf-8 -*-
##############################################################################
#
#    ODOO Open Source Management Solution
#
#    ODOO Addon module by Sprintit Ltd
#    Copyright (C) 2018 Sprintit Ltd (<http://sprintit.fi>).
#
##############################################################################

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    company_registry = fields.Char('Company Registry', size=64,)
    einvoice_address = fields.Char('eInvoice', size=20, help='For eInvoice address')
    einvoice_operator = fields.Char('eInvoice Operator', size=20, help='For eInvoice operator address')


# link partner fields to company as well
class ResCompany(models.Model):
    _inherit = 'res.company'

    company_registry = fields.Char(related='partner_id.company_registry', readonly=False)
    einvoice_address = fields.Char(related='partner_id.einvoice_address', readonly=False)
    einvoice_operator = fields.Char(related='partner_id.einvoice_operator', readonly=False)
