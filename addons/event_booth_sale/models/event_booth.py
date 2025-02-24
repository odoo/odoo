# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EventBooth(models.Model):
    _inherit = 'event.booth'

    # registrations
    event_booth_registration_ids = fields.One2many('event.booth.registration', 'event_booth_id')
    # sale information
    sale_order_line_registration_ids = fields.Many2many(
        'sale.order.line', 'event_booth_registration',
        'event_booth_id', 'sale_order_line_id', string='SO Lines with reservations',
        groups='sales_team.group_sale_salesman', copy=False)
    sale_order_line_id = fields.Many2one(
        'sale.order.line', string='Final Sale Order Line', ondelete='set null',
        readonly=False, index='btree_not_null',
        groups='sales_team.group_sale_salesman', copy=False)
    sale_order_id = fields.Many2one(
        related='sale_order_line_id.order_id', store='True', readonly=True, index='btree_not_null',
        groups='sales_team.group_sale_salesman')
    is_paid = fields.Boolean('Is Paid', copy=False)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_sale_order(self):
        booth_with_so = self.sudo().filtered('sale_order_id')
        if booth_with_so:
            raise UserError(_(
                'You can\'t delete the following booths as they are linked to sales orders: '
                '%(booths)s', booths=', '.join(booth_with_so.mapped('name'))))

    def action_set_paid(self):
        self.write({'is_paid': True})

    def action_view_sale_order(self):
        self.sale_order_id.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('sale.action_orders')
        action['views'] = [(False, 'form')]
        action['res_id'] = self.sale_order_id.id
        return action

    def _get_booth_multiline_description(self):
        return '%s : \n%s' % (
            self.event_id.display_name,
            '\n'.join(['- %s' % booth.name for booth in self])
        )
