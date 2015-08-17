# -*- coding: utf-8 -*-
from datetime import date
import membership
from openerp import api, models, fields, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError


class Partner(models.Model):
    _inherit = 'res.partner'
    associate_member_id = fields.Many2one('res.partner', 'Associate Member', help="A member with whom you want to associate your membership.It will consider the membership state of the associated member.")
    member_lines_ids = fields.One2many('membership.membership_line', 'partner_id', 'Membership')
    free_member = fields.Boolean('Free Member', help="Select if you want to give free membership.")
    membership_amount = fields.Float('Membership Amount', digits=(16, 2), help='The price negotiated by the partner')
    membership_state = fields.Selection(compute='_compute_get_membership_state', string='Current Membership Status', selection=membership.STATE, store=True,
                                        help='It indicates the membership state.\n'
                                        '-Non Member: A partner who has not applied for any membership.\n'
                                        '-Cancelled Member: A member who has cancelled his membership.\n'
                                        '-Old Member: A member whose membership date has expired.\n'
                                        '-Waiting Member: A member who has applied for the membership and whose invoice is going to be created.\n'
                                        '-Invoiced Member: A member whose invoice has been created.\n'
                                        '-Paying member: A member who has paid the membership fee.')
    membership_start = fields.Date(compute='_compute_membership_date', store=True, help='Date from which membership becomes active.')
    membership_stop = fields.Date(compute='_compute_membership_date', store=True, help='Date until which membership remains active.')
    membership_cancel = fields.Date(compute='_compute_membership_date', store=True, help='Date on which membership has been cancelled')

    @api.depends('free_member', 'member_lines_ids')
    def _compute_membership_date(self):
        """Return  date of membership"""
        if self.ids:
            ids_to_search = []
            for partner in self:
                if partner.associate_member_id:
                    ids_to_search.append(partner.associate_member_id.id)
                else:
                    ids_to_search.append(partner.id)
            self.env.cr.execute("""
                SELECT
                    p.id as id,
                    MIN(m.date_from) as membership_start,
                    MAX(m.date_to) as membership_stop,
                    MIN(CASE WHEN m.date_cancel is not null THEN 1 END) as membership_cancel
                FROM
                    res_partner p
                LEFT JOIN
                    membership_membership_line m
                    ON (m.partner_id = p.id)
                WHERE
                    p.id IN %s
                GROUP BY
                    p.id""", (tuple(ids_to_search), ))
            for record in self.env.cr.dictfetchall():
                partner = self.browse(record.pop('id')).update(record)

    @api.depends('member_lines_ids.account_invoice_id.state', 'membership_state', 'associate_member_id', 'free_member')
    def _compute_get_membership_state(self):
        return self._membership_state()

    @api.constrains('associate_member_id')
    def _check_recursion(self):
        """Check  Recursive  for Associated Members.
        """
        level = 100
        recursive_ids = self.ids
        while len(recursive_ids):
            self.env.cr.execute('SELECT DISTINCT associate_member_id FROM res_partner WHERE id IN %s', (tuple(recursive_ids),))
            recursive_ids = filter(None, map(lambda x: x[0], self.env.cr.fetchall()))
            if not level:
                raise UserError(_('Error ! You cannot create recursive associated members.'))
            level -= 1
        return

    @api.model
    def _cron_update_membership(self):
        partners = self.search([('membership_state', '=', 'paid')])
        if partners:
            partners._store_set_values(['membership_state'])

    @api.multi
    def _membership_state(self):
        """This Function return Membership State For Given Partner. """
        today_date = date.today()
        for partner_data in self:
            partner_data.membership_state = 'none'
            if partner_data.membership_cancel and today_date > fields.Date.from_string(partner_data.membership_cancel):
                partner_data.membership_state = 'free' if partner_data.free_member else 'canceled'
                continue
            if partner_data.membership_stop and today_date > fields.Date.from_string(partner_data.membership_stop):
                partner_data.membership_state = 'free' if partner_data.free_member else 'old'
                continue

            s = 4
            if partner_data.member_lines_ids:
                for mline in partner_data.member_lines_ids:
                    if fields.Date.from_string(mline.date_to) >= today_date:
                        if mline.account_invoice_line_id and mline.account_invoice_line_id.invoice_id:
                            mstate = mline.account_invoice_line_id.invoice_id.state
                            if mstate == 'paid':
                                s = 0
                                inv = mline.account_invoice_line_id.invoice_id
                                for payment in inv.payment_ids:
                                    if payment.invoice_ids and any(inv.type == 'out_refund' for inv in payment.invoice_ids):
                                        s = 2
                                break
                            elif mstate == 'open' and s != 0:
                                s = 1
                            elif mstate == 'cancel' and s != 0 and s != 1:
                                s = 2
                            elif (mstate == 'draft' or mstate == 'proforma') and s != 0 and s != 1:
                                s = 3
                if s == 4:
                    for mline in partner_data.member_lines_ids:
                        if fields.Date.from_string(mline.date_from) < today_date and fields.Date.from_string(mline.date_to) < today_date and mline.date_from <= mline.date_to and (mline.account_invoice_line_id and mline.account_invoice_line_id.invoice_id.state) == 'paid':
                            s = 5
                        else:
                            s = 6
                if s == 0:
                    partner_data.membership_state = 'paid'
                elif s == 1:
                    partner_data.membership_state = 'invoiced'
                elif s == 2:
                    partner_data.membership_state = 'canceled'
                elif s == 3:
                    partner_data.membership_state = 'waiting'
                elif s == 5:
                    partner_data.membership_state = 'old'
                elif s == 6:
                    partner_data.membership_state = 'none'
            if partner_data.free_member and s != 0:
                partner_data.membership_state = 'free'
            if partner_data.associate_member_id:
                partner_data.membership_state = partner_data.associate_member_id._membership_state()
            return partner_data.membership_state
            
    @api.multi
    def create_membership_invoice(self, product_id=None, datas=None):
        """ Create Customer Invoice of Membership for partners.
        @param datas: datas has dictionary value which consist Id of Membership product and Cost Amount of Membership.
                      datas = {'membership_product_id': None, 'amount': None}
        """
        AccountInv = self.env['account.invoice']
        InvoiceLine = self.env['account.invoice.line']
        product_id = product_id or datas.get('membership_product_id', False)
        amount = datas.get('amount', 0.0)
        invoice_list = []
        for partner in self:
            account_id = partner.property_account_receivable_id and partner.property_account_receivable_id.id or False
            fpos_id = partner.property_account_position_id and partner.property_account_position_id.id or False
            addr = partner.address_get(['invoice'])
            if partner.free_member:
                raise UserError(_("Partner is a free Member."))
            if not addr.get('invoice', False):
                raise UserError(_("Partner doesn't have an address to make the invoice."))

            invoice_id = AccountInv.create({
                'partner_id': partner.id,
                'account_id': account_id,
                'fiscal_position_id': fpos_id or False
            })
            line_values = {
                'product_id': product_id,
                'price_unit': amount,
                'invoice_id': invoice_id,
            }
            # create a record in cache, apply onchange then revert back to a dictionnary
            invoice_line = InvoiceLine.new(line_values)
            invoice_line._onchange_product_id()
            line_values = invoice_line._convert_to_write(invoice_line._cache)
            line_values['price_unit'] = amount
            invoice_id.write({'invoice_line_ids': [(0, 0, line_values)]})
            invoice_list.append(invoice_id.id)
            invoice_id.compute_taxes()
        return invoice_list
