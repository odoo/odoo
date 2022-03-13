# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class PosPaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    carrier_ids = fields.Many2many(string='Allowed with carriers', comodel_name='delivery.carrier')
    is_onsite_acquirer = fields.Boolean(default=False, required=True)

    @api.model
    def _get_compatible_acquirers(self, *args, sale_order_id=None, **kwargs):
        """ Override of payment to update the base criteria with POS specific data

        Base requirements are the same, but only carriers linked to a POS can be chosen

        :param int sale_order_id: The sale order to be paid, if any, as a `sale.order` id
        :return: All compatible acquirers
        """
        compatible_acquirers = super()._get_compatible_acquirers(
            *args, sale_order_id=sale_order_id, **kwargs
        )
        onsite_acquirer = self.env.ref('payment_onsite.payment_acquirer_onsite', raise_if_not_found=False)
        sale_order = self.env['sale.order'].browse(sale_order_id).exists()
        if sale_order.carrier_id.delivery_type == 'onsite':
            return compatible_acquirers & onsite_acquirer
        return compatible_acquirers | onsite_acquirer
