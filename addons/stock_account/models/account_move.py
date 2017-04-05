# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

class AccountMove(models.Model):
    _inherit = 'account.move.line'

    valuation_reception_state = fields.Selection(selection=[('received','Received'), ('waiting','Waiting for reception')], string='Reception state', help="Tells whether or not the goods related to this account.move have already been received.")
    #TODO OCO pas sûr que ce truc-machin soit nécessaire... Si les moves existent pour l'évaluation, c'est que le stock a été reçu.