# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    plafond_secu = fields.Float(related='company_id.plafond_secu',
    	related_sudo=False, string="Plafond de la Securite Sociale")
    nombre_employes = fields.Integer(related='company_id.nombre_employes',
    	related_sudo=False, string="Nombre d'employes")
    cotisation_prevoyance = fields.Float(related='company_id.cotisation_prevoyance',
    	related_sudo=False, string='Cotisation Patronale Prevoyance')
    org_ss = fields.Char(related='company_id.org_ss',
    	related_sudo=False, string="Organisme de securite sociale")
    conv_coll = fields.Char(related='company_id.conv_coll',
    	related_sudo=False, string="Convention collective")
