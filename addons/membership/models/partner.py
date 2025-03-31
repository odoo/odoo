# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from . import membership


class Partner(models.Model):
    _inherit = 'res.partner'

    associate_member = fields.Many2one('res.partner', string='Associate Member',
        help="A member with whom you want to associate your membership."
             "It will consider the membership state of the associated member.")
    member_lines = fields.One2many('membership.membership_line', 'partner', string='Membership')
    free_member = fields.Boolean(string='Free Member',
        help="Select if you want to give free membership.")
    membership_amount = fields.Float(string='Membership Amount', digits=(16, 2),
        help='The price negotiated by the partner')
    membership_state = fields.Selection(membership.STATE, compute='_compute_membership_state',
        string='Current Membership Status', store=True, recursive=True,
        help='It indicates the membership state.\n'
             '-Non Member: A partner who has not applied for any membership.\n'
             '-Cancelled Member: A member who has cancelled his membership.\n'
             '-Old Member: A member whose membership date has expired.\n'
             '-Waiting Member: A member who has applied for the membership and whose invoice is going to be created.\n'
             '-Invoiced Member: A member whose invoice has been created.\n'
             '-Paying member: A member who has paid the membership fee.')
    membership_start = fields.Date(compute='_compute_membership_state',
        string ='Membership Start Date', store=True,
        help="Date from which membership becomes active.")
    membership_stop = fields.Date(compute='_compute_membership_state',
        string ='Membership End Date', store=True,
        help="Date until which membership remains active.")
    membership_cancel = fields.Date(compute='_compute_membership_state',
        string ='Cancel Membership Date', store=True,
        help="Date on which membership has been cancelled")

    @api.depends('member_lines.account_invoice_line',
                 'member_lines.account_invoice_line.move_id.state',
                 'member_lines.account_invoice_line.move_id.payment_state',
                 'member_lines.account_invoice_line.move_id.partner_id',
                 'free_member',
                 'member_lines.date_to', 'member_lines.date_from',
                 'associate_member', 'associate_member.membership_state')
    def _compute_membership_state(self):
        today = fields.Date.today()
        for partner in self:
            partner.membership_start = self.env['membership.membership_line'].search([
                ('partner', 'in', (partner.associate_member or partner).ids), ('date_cancel', '=', False)
            ], limit=1, order='date_from').date_from
            partner.membership_stop = self.env['membership.membership_line'].search([
                ('partner', 'in', (partner.associate_member or partner).ids), ('date_cancel', '=', False)
            ], limit=1, order='date_to desc').date_to
            partner.membership_cancel = self.env['membership.membership_line'].search([
                ('partner', 'in', partner.ids)
            ], limit=1, order='date_cancel').date_cancel

            if partner.associate_member:
                partner.membership_state = partner.associate_member.membership_state
                continue

            if partner.free_member and partner.membership_state != 'paid':
                partner.membership_state = 'free'
                continue

            for mline in partner.member_lines:
                if (mline.date_to or date.min) >= today and (mline.date_from or date.min) <= today:
                    partner.membership_state = mline.state
                    break
                elif ((mline.date_from or date.min) < today and (mline.date_to or date.min) <= today and \
                      (mline.date_from or date.min) < (mline.date_to or date.min)):
                    if mline.account_invoice_id and mline.account_invoice_id.payment_state in ('in_payment', 'paid'):
                        partner.membership_state = 'old'
                    elif mline.account_invoice_id and mline.account_invoice_id.state == 'cancel':
                        partner.membership_state = 'canceled'
                    break
            else:
                partner.membership_state = 'none'

    @api.constrains('associate_member')
    def _check_recursion_associate_member(self):
        if self._has_cycle('associate_member'):
            raise ValidationError(_('You cannot create recursive associated members.'))

    @api.model
    def _cron_update_membership(self):
        partners = self.search([('membership_state', 'in', ['invoiced', 'paid'])])
        # mark the field to be recomputed, and recompute it
        self.env.add_to_compute(self._fields['membership_state'], partners)

    def create_membership_invoice(self, product, amount):
        """ Create Customer Invoice of Membership for partners.
        """
        invoice_vals_list = []
        for partner in self:
            addr = partner.address_get(['invoice'])
            if partner.free_member:
                raise UserError(_("Partner is a free Member."))
            if not addr.get('invoice', False):
                raise UserError(_("Partner doesn't have an address to make the invoice."))

            invoice_vals_list.append({
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'invoice_line_ids': [
                    (
                        0,
                        None,
                        {
                            'product_id': product.id,
                            'quantity': 1,
                            'price_unit': amount,
                            'tax_ids': [(6, 0, product.taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(self.env.company)).ids)]
                        }
                     )
                ]
            })

        return self.env['account.move'].create(invoice_vals_list)
