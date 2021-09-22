# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import random
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class Coupon(models.Model):
    _name = 'coupon.coupon'
    _description = "Coupon"
    _rec_name = 'code'

    @api.model
    def _generate_code(self):
        """Generate a 20 char long pseudo-random string of digits for barcode
        generation.

        A decimal serialisation is longer than a hexadecimal one *but* it
        generates a more compact barcode (Code128C rather than Code128A).

        Generate 8 bytes (64 bits) barcodes as 16 bytes barcodes are not
        compatible with all scanners.
         """
        return str(random.getrandbits(64))

    code = fields.Char(default=_generate_code, required=True, readonly=True)
    expiration_date = fields.Date('Expiration Date', compute='_compute_expiration_date')
    state = fields.Selection([
        ('reserved', 'Pending'),
        ('new', 'Valid'),
        ('sent', 'Sent'),
        ('used', 'Used'),
        ('expired', 'Expired'),
        ('cancel', 'Cancelled')
    ], required=True, default='new')
    partner_id = fields.Many2one('res.partner', "For Customer")
    program_id = fields.Many2one('coupon.program', "Program")
    discount_line_product_id = fields.Many2one('product.product', related='program_id.discount_line_product_id', readonly=False,
        help='Product used in the sales order to apply the discount.')

    _sql_constraints = [
        ('unique_coupon_code', 'unique(code)', 'The coupon code must be unique!'),
    ]

    @api.depends('create_date', 'program_id.validity_duration')
    def _compute_expiration_date(self):
        self.expiration_date = 0
        for coupon in self.filtered(lambda x: x.program_id.validity_duration > 0):
            coupon.expiration_date = (coupon.create_date + relativedelta(days=coupon.program_id.validity_duration)).date()

    def _get_default_template(self):
        return False

    def action_coupon_send(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        default_template = self._get_default_template()
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='coupon.coupon',
            default_res_id=self.id,
            default_use_template=bool(default_template),
            default_template_id=default_template and default_template.id,
            default_composition_mode='comment',
            custom_layout='mail.mail_notification_light',
            mark_coupon_as_sent=True,
            force_email=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def action_coupon_cancel(self):
        self.state = 'cancel'

    def cron_expire_coupon(self):
        self._cr.execute("""
            SELECT C.id FROM COUPON_COUPON as C
            INNER JOIN COUPON_PROGRAM as P ON C.program_id = P.id
            WHERE C.STATE in ('reserved', 'new', 'sent')
                AND P.validity_duration > 0
                AND C.create_date + interval '1 day' * P.validity_duration < now()""")

        expired_ids = [res[0] for res in self._cr.fetchall()]
        self.browse(expired_ids).write({'state': 'expired'})

    def _check_coupon_code(self, order_date, partner_id, **kwargs):
        """ Check the validity of this single coupon.
            :param order_date Date:
            :param partner_id int | boolean:
        """
        self.ensure_one()
        message = {}
        if self.state == 'used':
            message = {'error': _('This coupon has already been used (%s).') % (self.code)}
        elif self.state == 'reserved':
            message = {'error': _('This coupon %s exists but the origin sales order is not validated yet.') % (self.code)}
        elif self.state == 'cancel':
            message = {'error': _('This coupon has been cancelled (%s).') % (self.code)}
        elif self.state == 'expired' or (self.expiration_date and self.expiration_date < order_date):
            message = {'error': _('This coupon is expired (%s).') % (self.code)}
        elif not self.program_id.active:
            message = {'error': _('The coupon program for %s is in draft or closed state') % (self.code)}
        elif self.partner_id and self.partner_id.id != partner_id:
            message = {'error': _('Invalid partner.')}
        return message
