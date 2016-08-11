# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import decimal_precision as dp


class ResCompany(models.Model):
    _inherit = 'res.company'

    plafond_secu = fields.Float(string='Plafond de la Securite Sociale', digits=dp.get_precision('Payroll'))
    nombre_employes = fields.Integer(string='Nombre d\'employes')
    cotisation_prevoyance = fields.Float(string='Cotisation Patronale Prevoyance', digits=dp.get_precision('Payroll'))
    org_ss = fields.Char(string='Organisme de securite sociale')
    conv_coll = fields.Char(string='Convention collective')


class HrContract(models.Model):
    _inherit = 'hr.contract'

    qualif = fields.Char(string='Qualification')
    niveau = fields.Char()
    coef = fields.Char(string='Coefficient')


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    payment_mode = fields.Char(string='Mode de paiement')
