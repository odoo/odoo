# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    plafond_secu = fields.Float(related='company_id.plafond_secu', string="Plafond de la Securite Sociale", readonly=False)
    nombre_employes = fields.Integer(related='company_id.nombre_employes', string="Nombre d'employes", readonly=False)
    cotisation_prevoyance = fields.Float(related='company_id.cotisation_prevoyance', string='Cotisation Patronale Prevoyance', readonly=False)
    org_ss = fields.Char(related='company_id.org_ss', string="Organisme de securite sociale", readonly=False)
    conv_coll = fields.Char(related='company_id.conv_coll', string="Convention collective", readonly=False)
