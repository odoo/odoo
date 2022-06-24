# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    event_booth_category_id = fields.Many2one('event.booth.category', string='Booths Category', ondelete='set null')
    event_booth_pending_ids = fields.Many2many(
        'event.booth', string='Pending Booths', search='_search_event_booth_pending_ids',
        compute='_compute_event_booth_pending_ids', inverse='_inverse_event_booth_pending_ids',
        help='Used to create registration when providing the desired event booth.'
    )
    event_booth_registration_ids = fields.One2many(
        'event.booth.registration', 'sale_order_line_id', string='Confirmed Registration')
    event_booth_ids = fields.One2many('event.booth', 'sale_order_line_id', string='Confirmed Booths')
    is_event_booth = fields.Boolean(compute='_compute_is_event_booth')

    @api.depends('product_id.type')
    def _compute_is_event_booth(self):
        for record in self:
            record.is_event_booth = record.product_id.detailed_type == 'event_booth'

    @api.depends('event_booth_ids')
    def _compute_name_short(self):
        wbooth = self.filtered(lambda line: line.event_booth_pending_ids)
        for record in wbooth:
            record.name_short = record.event_booth_pending_ids.event_id.name
        super(SaleOrderLine, self - wbooth)._compute_name_short()

    @api.depends('event_booth_registration_ids')
    def _compute_event_booth_pending_ids(self):
        for so_line in self:
            so_line.event_booth_pending_ids = so_line.event_booth_registration_ids.event_booth_id

    def _inverse_event_booth_pending_ids(self):
        for so_line in self:
            self.env['event.booth.registration'].create([{
                'event_booth_id': booth.id,
                'sale_order_line_id': so_line.id,
                'partner_id': so_line.order_id.partner_id.id
            } for booth in so_line.event_booth_pending_ids])

    def _search_event_booth_pending_ids(self, operator, value):
        return [('event_booth_registration_ids.event_booth_id', operator, value)]

    @api.constrains('event_booth_registration_ids')
    def _check_event_booth_registration_ids(self):
        if len(self.event_booth_registration_ids.event_booth_id.event_id) > 1:
            raise ValidationError(_('Registrations from the same Order Line must belong to a single event.'))

    @api.onchange('product_id')
    def _onchange_product_id_booth(self):
        """We reset the event when the selected product doesn't belong to any pending booths."""
        if self.event_id and (not self.product_id or self.product_id not in self.event_booth_pending_ids.product_id):
            self.event_id = None

    @api.onchange('event_id')
    def _onchange_event_id_booth(self):
        """We reset the pending booths when the event changes to avoid inconsistent state."""
        if self.event_booth_pending_ids and (not self.event_id or self.event_id != self.event_booth_pending_ids.event_id):
            self.event_booth_pending_ids = None

    @api.depends('event_booth_pending_ids')
    def _compute_name(self):
        """Override to add the compute dependency.

        The custom name logic can be found below in _get_sale_order_line_multiline_description_sale.
        """
        super()._compute_name()

    def _update_event_booths(self, set_paid=False):
        for so_line in self.filtered('is_event_booth'):
            if so_line.event_booth_pending_ids and not so_line.event_booth_ids:
                unavailable = so_line.event_booth_pending_ids.filtered(lambda booth: not booth.is_available)
                if unavailable:
                    raise ValidationError(
                        _('The following booths are unavailable, please remove them to continue : %(booth_names)s',
                          booth_names=''.join('\n\t- %s' % booth.display_name for booth in unavailable)))
                so_line.event_booth_registration_ids.sudo().action_confirm()
            if so_line.event_booth_ids and set_paid:
                so_line.event_booth_ids.sudo().action_set_paid()
        return True

    def _get_sale_order_line_multiline_description_sale(self):
        if self.event_booth_pending_ids:
            return self.event_booth_pending_ids._get_booth_multiline_description()
        return super()._get_sale_order_line_multiline_description_sale()

    def _get_display_price(self):
        if self.event_booth_pending_ids and self.event_id:
            company = self.event_id.company_id or self.env.company
            currency = company.currency_id
            total_price = sum([booth.price for booth in self.event_booth_pending_ids])
            return currency._convert(
                total_price, self.order_id.currency_id,
                self.order_id.company_id or self.env.company.id,
                self.order_id.date_order or fields.Date.today())
        return super()._get_display_price()
