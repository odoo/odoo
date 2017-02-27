# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayrollConfigSettings(models.TransientModel):
    _inherit = 'hr.payroll.config.settings'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        copy=False, default=lambda self: self.env['res.company']._company_default_get())
    plafond_secu = fields.Float(related='company_id.plafond_secu', string="Plafond de la Securite Sociale")
    nombre_employes = fields.Integer(related='company_id.nombre_employes', string="Nombre d'employes")
    cotisation_prevoyance = fields.Float(related='company_id.cotisation_prevoyance', string='Cotisation Patronale Prevoyance')
    org_ss = fields.Char(related='company_id.org_ss', string="Organisme de securite sociale")
    conv_coll = fields.Char(related='company_id.conv_coll', string="Convention collective")
