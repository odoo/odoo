# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    is_paid = fields.Boolean('Is Paid')
    payment_status = fields.Selection(string="Payment Status", selection=[
            ('to_pay', 'Not Paid'),
            ('paid', 'Paid'),
            ('free', 'Free'),
        ], compute="_compute_payment_status", compute_sudo=True)

    @api.depends('is_paid')
    def _compute_payment_status(self):
        for record in self:
            if not record._is_free():
                record.payment_status = 'free'
            elif record.is_paid:
                record.payment_status = 'paid'
            else:
                record.payment_status = 'to_pay'

    def _is_free(self):
        """
        Hook that check if the registration is linked to a sale (sale or pos order)
        """
        self.ensure_one()
        return True

    def _action_set_paid(self):
        self.write({'is_paid': True})

    def _get_registration_summary(self):
        res = super(EventRegistration, self)._get_registration_summary()
        res.update({
            'payment_status': self.payment_status,
            'payment_status_value': dict(self._fields['payment_status']._description_selection(self.env))[self.payment_status],
            'has_to_pay': self.payment_status == 'to_pay',
        })
        return res
