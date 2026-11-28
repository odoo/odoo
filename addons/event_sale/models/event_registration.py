# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.tools import float_is_zero

# fields of a registration whose change can alter the option lines of its sales order
TICKET_OPTION_SYNC_FIELDS = {
    'ticket_option_product_ids', 'state', 'active', 'event_ticket_id', 'sale_order_line_id',
}


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    # TDE FIXME: maybe add an onchange on sale_order_id
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', ondelete='cascade', copy=False, index='btree_not_null')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sales Order Line', ondelete='cascade', copy=False, index='btree_not_null')
    state = fields.Selection(default=None, compute="_compute_registration_status", store=True, readonly=False, precompute=True)
    utm_campaign_id = fields.Many2one(compute='_compute_utm_campaign_id', readonly=False,
        store=True, ondelete="set null")
    utm_source_id = fields.Many2one(compute='_compute_utm_source_id', readonly=False,
        store=True, ondelete="set null")
    utm_medium_id = fields.Many2one(compute='_compute_utm_medium_id', readonly=False,
        store=True, ondelete="set null")

    def _has_order(self):
        return super()._has_order() or self.sale_order_id

    @api.depends('sale_order_id.state', 'sale_order_id.currency_id', 'sale_order_id.amount_total')
    def _compute_registration_status(self):
        for sale_order, registrations in self.filtered('sale_order_id').grouped('sale_order_id').items():
            cancelled_so_registrations = registrations.filtered(lambda reg: reg.sale_order_id.state == 'cancel')
            cancelled_so_registrations.state = 'cancel'
            cancelled_registrations = cancelled_so_registrations | registrations.filtered(lambda reg: reg.state == 'cancel')
            if float_is_zero(sale_order.amount_total, precision_rounding=sale_order.currency_id.rounding):
                registrations.sale_status = 'free'
                registrations.filtered(lambda reg: not reg.state or reg.state == 'draft').state = "open"
            else:
                sold_registrations = registrations.filtered(lambda reg: reg.sale_order_id.state == 'sale') - cancelled_registrations
                sold_registrations.sale_status = 'sold'
                (registrations - sold_registrations).sale_status = 'to_pay'
                sold_registrations.filtered(lambda reg: not reg.state or reg.state in {'draft', 'cancel'}).state = "open"
                (registrations - sold_registrations - cancelled_registrations).state = 'draft'
        super()._compute_registration_status()

        # set default value to free and open if none was set yet
        for registration in self:
            if not registration.sale_status:
                registration.sale_status = 'free'
            if not registration.state:
                registration.state = 'open'

    @api.depends('sale_order_id')
    def _compute_utm_campaign_id(self):
        for registration in self:
            if registration.sale_order_id.campaign_id:
                registration.utm_campaign_id = registration.sale_order_id.campaign_id
            elif not registration.utm_campaign_id:
                registration.utm_campaign_id = False

    @api.depends('sale_order_id')
    def _compute_utm_source_id(self):
        for registration in self:
            if registration.sale_order_id.source_id:
                registration.utm_source_id = registration.sale_order_id.source_id
            elif not registration.utm_source_id:
                registration.utm_source_id = False

    @api.depends('sale_order_id')
    def _compute_utm_medium_id(self):
        for registration in self:
            if registration.sale_order_id.medium_id:
                registration.utm_medium_id = registration.sale_order_id.medium_id
            elif not registration.utm_medium_id:
                registration.utm_medium_id = False

    def action_view_sale_order(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['views'] = [(False, 'form')]
        action['res_id'] = self.sale_order_id.id
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sale_order_line_id'):
                so_line_vals = self._synchronize_so_line_values(
                    self.env['sale.order.line'].browse(vals['sale_order_line_id'])
                )
                vals.update(so_line_vals)
        registrations = super(EventRegistration, self).create(vals_list)
        for registration in registrations:
            if registration.sale_order_id:
                registration.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': registration, 'origin': registration.sale_order_id},
                    subtype_xmlid='mail.mt_note',
                )
        registrations._sync_sale_order_ticket_options()
        return registrations

    def write(self, vals):
        if vals.get('sale_order_line_id'):
            so_line_vals = self._synchronize_so_line_values(
                self.env['sale.order.line'].browse(vals['sale_order_line_id'])
            )
            vals.update(so_line_vals)

        updated_fields_to_notify = []
        if vals.get('event_slot_id'):
            updated_fields_to_notify.append(('event.slot', 'event_slot_id'))
        if vals.get('event_ticket_id'):
            updated_fields_to_notify.append(('event.event.ticket', 'event_ticket_id'))
        for model, field in updated_fields_to_notify:
            self.filtered(
                lambda registration: registration[field] and registration[field].id != vals[field]
            )._sale_order_registration_data_change_notify(field, self.env[model].browse(vals[field]))

        sync_options = bool(vals.keys() & TICKET_OPTION_SYNC_FIELDS) and not self.env.context.get('event_ticket_option_sync')
        if sync_options:
            old_lines = self.sale_order_line_id
            old_options = {registration: registration.ticket_option_product_ids for registration in self}

        res = super(EventRegistration, self).write(vals)

        if sync_options:
            self._sync_sale_order_ticket_options(old_lines=old_lines, old_options=old_options)
        return res

    def _sync_sale_order_ticket_options(self, old_lines=None, old_options=None):
        """ Make the option lines of the sales orders follow the options chosen by these
        attendees (one batched sync per order).

        Orders that are cancelled or locked are not edited: their salesperson is notified instead
        of the changed options.

        :param old_lines: ticket lines the attendees had before a change, to be synchronized too
        :param old_options: ``{registration: options before the change}``, to notify the changes
        """
        if self.env.context.get('event_ticket_option_sync'):
            return
        ticket_lines = (self.sudo().sale_order_line_id | (old_lines or self.env['sale.order.line']).sudo()).filtered('event_ticket_id')
        for order, lines in ticket_lines.grouped('order_id').items():
            if order.state == 'cancel' or order.locked:
                for registration, options in (old_options or {}).items():
                    if registration.sale_order_id == order and options != registration.ticket_option_product_ids:
                        registration.sudo()._sale_order_registration_data_change_notify(
                            'ticket_option_product_ids', registration.ticket_option_product_ids, old_record=options)
                continue
            order._sync_event_ticket_option_lines(lines)

    def _synchronize_so_line_values(self, so_line):
        if so_line:
            return {
                # Avoid registering public users but respect the portal workflows
                'partner_id': False if self.env.user._is_public() and self.env.user.partner_id == so_line.order_id.partner_id else so_line.order_id.partner_id.id,
                'event_id': so_line.event_id.id,
                'event_slot_id': so_line.event_slot_id.id,
                'event_ticket_id': so_line.event_ticket_id.id,
                'sale_order_id': so_line.order_id.id,
                'sale_order_line_id': so_line.id,
            }
        return {}

    def _sale_order_registration_data_change_notify(self, new_record_field, new_record, old_record=None):
        fallback_user_id = self.env.user.id if not self.env.user._is_public() else self.env.ref("base.user_admin").id
        for registration in self:
            previous_record = registration[new_record_field] if old_record is None else old_record
            record_type = {
                'event_ticket_id': _('Ticket'),
                'ticket_option_product_ids': _('Optional Products'),
            }.get(new_record_field, _('Slot'))
            render_context = {
                'registration': registration,
                'record_type': record_type,
                'old_name': ', '.join(previous_record.mapped('display_name')),
                'new_name': ', '.join(new_record.mapped('display_name')),
            }
            user_id = registration.event_id.user_id.id or registration.sale_order_id.user_id.id or fallback_user_id
            registration.sale_order_id._activity_schedule_with_view(
                'mail.mail_activity_data_warning',
                user_id=user_id,
                views_or_xmlid='event_sale.event_registration_change_exception',
                render_context=render_context)

    def _compute_field_value(self, field):
        if field.name != 'state':
            return super()._compute_field_value(field)

        unconfirmed = self.filtered(lambda reg: reg.ids and reg.state in {'draft', 'cancel'})
        res = super()._compute_field_value(field)
        confirmed = unconfirmed.filtered(lambda reg: reg.state == 'open')
        if confirmed:
            confirmed._update_mail_schedulers()
        return res

    def _get_registration_summary(self):
        res = super(EventRegistration, self)._get_registration_summary()
        res.update({
            'sale_status': self.sale_status,
            'sale_status_value': self.sale_status and dict(self._fields['sale_status']._description_selection(self.env))[self.sale_status],
            'has_to_pay': self.sale_status == 'to_pay',
        })
        return res

    def _get_event_registration_ids_from_order(self):
        self.ensure_one()
        return self.sale_order_id.order_line.filtered(
            lambda line: line.event_id == self.event_id
        ).registration_ids.ids
