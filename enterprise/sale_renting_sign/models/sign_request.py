# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SignRequest(models.Model):
    _inherit = "sign.request"

    def _get_linked_record_action(self, default_action=None):
        """ Override to display the sale.order rental record correctly
        """
        self.ensure_one()
        if self.reference_doc._name == 'sale.order' and self.reference_doc.is_rental_order:
            action = self.env['ir.actions.act_window']._for_xml_id('sale_renting.rental_order_action')
            action.update({
                "views": [(False, "form")],
                "view_mode":  'form',
                "res_id": self.reference_doc.id,
            })
            return action
        else:
            return super()._get_linked_record_action(default_action=default_action)
