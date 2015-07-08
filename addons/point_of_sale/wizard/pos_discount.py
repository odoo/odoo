# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models, fields


class PosDiscount(models.TransientModel):
    _name = 'pos.discount'
    _description = 'Add a Global Discount'

    discount = fields.Float(string='Discount (%)', required=True, digits=(16, 2), default=5)

    @api.multi
    def apply_discount(self):
        """
         To give the discount of  product and check the.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return : nothing
        """
        self.ensure_one()
        Order = self.env['pos.order']
        record_id = self.env.context.get('active_id', False)
        if isinstance(record_id, (int, long)):
            record_id = [record_id]
        for order in Order.browse(record_id):
            order.lines.write({'discount': self.discount})
        return {}
