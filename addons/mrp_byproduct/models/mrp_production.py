# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from odoo.tools import float_round


class MrpProduction(models.Model):
    _description = 'Production'
    _inherit = 'mrp.production'

    @api.multi
    def _generate_finished_moves(self):
        """ Generates moves and work orders
        @return: Newly generated picking Id.
        """
        res = super(MrpProduction, self)._generate_finished_moves()

        return res


class MrpProductProduce(models.TransientModel):
    _name = "mrp.product.produce"
    _description = "Record Production"
    _inherit = "mrp.product.produce"
