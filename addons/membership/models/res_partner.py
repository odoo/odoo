# -*- coding: utf-8 -*-

from openerp import _, api, fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    def _get_partner_id(self, cr, uid, ids, context=None):
        member_line_obj = self.pool.get('membership.membership_line')
        res_obj =  self.pool.get('res.partner')
        data_inv = member_line_obj.browse(cr, uid, ids, context=context)
        list_partner = []
        for data in data_inv:
            list_partner.append(data.partner.id)
        ids2 = list_partner
        while ids2:
            ids2 = res_obj.search(cr, uid, [('associate_member', 'in', ids2)], context=context)
            list_partner += ids2
        return list_partner

    def _get_invoice_partner(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get('account.invoice')
        res_obj = self.pool.get('res.partner')
        data_inv = inv_obj.browse(cr, uid, ids, context=context)
        list_partner = []
        for data in data_inv:
            list_partner.append(data.partner_id.id)
        ids2 = list_partner
        while ids2:
            ids2 = res_obj.search(cr, uid, [('associate_member', 'in', ids2)], context=context)
            list_partner += ids2
        return list_partner

    def _membership_state(self, cr, uid, ids, name, args, context=None):
        """This Function return Membership State For Given Partner.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Partner IDs
        @param name: Field Name
        @param context: A standard dictionary for contextual values
        @param return: Dictionary of Membership state Value
        """
        res = {}
        # for id in ids:
        #     res[id] = 'none'
        # today = time.strftime('%Y-%m-%d')
        # for id in ids:
        #     partner_data = self.browse(cr, uid, id, context=context)
        #     if partner_data.membership_cancel and today > partner_data.membership_cancel:
        #         res[id] = 'canceled'
        #         continue
        #     if partner_data.membership_stop and today > partner_data.membership_stop:
        #         res[id] = 'old'
        #         continue
        #     s = 4
        #     if partner_data.member_lines:
        #         for mline in partner_data.member_lines:
        #             if mline.date_to >= today:
        #                 if mline.account_invoice_line and mline.account_invoice_line.invoice_id:
        #                     mstate = mline.account_invoice_line.invoice_id.state
        #                     if mstate == 'paid':
        #                         s = 0 -> 'paid'
        #                         inv = mline.account_invoice_line.invoice_id
        #                         for payment in inv.payment_ids:
        #                             if payment.invoice.type == 'out_refund':
        #                                 s = 2 -> 'canceled'
        #                         break
        #                     elif mstate == 'open' and s!=0:
        #                         s = 1 -> 'invoiced'
        #                     elif mstate == 'cancel' and s!=0 and s!=1:
        #                         s = 2 -> 'canceled'
        #                     elif  (mstate == 'draft' or mstate == 'proforma') and s!=0 and s!=1:
        #                         s = 3 -> 'waiting'
        #         if s==4:
        #             for mline in partner_data.member_lines:
        #                 if mline.date_from < today and mline.date_to < today and mline.date_from <= mline.date_to and (mline.account_invoice_line and mline.account_invoice_line.invoice_id.state) == 'paid':
        #                     s = 5 -> 'old'
        #                 else:
        #                     s = 6 -> 'none'
        #         if s==0:
        #             res[id] = 'paid'
        #         elif s==1:
        #             res[id] = 'invoiced'
        #         elif s==2:
        #             res[id] = 'canceled'
        #         elif s==3:
        #             res[id] = 'waiting'
        #         elif s==5:
        #             res[id] = 'old'
        #         elif s==6:
        #             res[id] = 'none'
        #     if partner_data.free_member and s!=0:
        #         res[id] = 'free'
        #     if partner_data.associate_member:
        #         res_state = self._membership_state(cr, uid, [partner_data.associate_member.id], name, args, context=context)
        #         res[id] = res_state[partner_data.associate_member.id]
        return res

    def _membership_date(self, cr, uid, ids, name, args, context=None):
        """Return  date of membership"""
        name = name[0]
        res = {}
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.browse(cr, uid, ids, context=context):
            if partner.associate_member:
                 partner_id = partner.associate_member.id
            else:
                 partner_id = partner.id
            res[partner.id] = {
                 'membership_start': False,
                 'membership_stop': False,
                 'membership_cancel': False
            }
            if name == 'membership_start':
                line_id = member_line_obj.search(cr, uid, [('partner', '=', partner_id),('date_cancel','=',False)],
                            limit=1, order='date_from', context=context)
                if line_id:
                        res[partner.id]['membership_start'] = member_line_obj.read(cr, uid, [line_id[0]],
                                ['date_from'], context=context)[0]['date_from']

            if name == 'membership_stop':
                line_id1 = member_line_obj.search(cr, uid, [('partner', '=', partner_id),('date_cancel','=',False)],
                            limit=1, order='date_to desc', context=context)
                if line_id1:
                      res[partner.id]['membership_stop'] = member_line_obj.read(cr, uid, [line_id1[0]],
                                ['date_to'], context=context)[0]['date_to']

            if name == 'membership_cancel':
                if partner.membership_state == 'canceled':
                    line_id2 = member_line_obj.search(cr, uid, [('partner', '=', partner.id)], limit=1, order='date_cancel', context=context)
                    if line_id2:
                        res[partner.id]['membership_cancel'] = member_line_obj.read(cr, uid, [line_id2[0]], ['date_cancel'], context=context)[0]['date_cancel']
        return res

    def _get_partners(self, cr, uid, ids, context=None):
        ids2 = ids
        while ids2:
            ids2 = self.search(cr, uid, [('associate_member', 'in', ids2)], context=context)
            ids += ids2
        return ids

    def __get_membership_state(self, *args, **kwargs):
        return self._membership_state(*args, **kwargs)

    associate_member_id = fields.Many2one(
        'res.partner', 'Associate Member',
        oldname='associate_member',
        help="A member with whom you want to associate your membership.It will consider the membership state of the associated member.")
    membership_line_ids = fields.One2many('membership.line', 'partner_id', 'Membership', oldname='member_lines')
    free_member = fields.Boolean('Free Member', help="Select if you want to give free membership.")
    membership_amount = fields.Float('Membership Amount', digits=(16, 2), help = 'The price negotiated by the partner')
    membership_state = fields.Selection(
        [('none', 'Non Member'), ('canceled', 'Cancelled Member'),
         ('old', 'Old Member'), ('waiting', 'Waiting Member'),
         ('invoiced', 'Invoiced Member'), ('free', 'Free Member'),
         ('paid', 'Paid Member')],
        comput='__get_membership_state',
        string='Current Membership Status',
        help='It indicates the membership state.\n'
             '-Non Member: A partner who has not applied for any membership.\n'
             '-Cancelled Member: A member who has cancelled his membership.\n'
             '-Old Member: A member whose membership date has expired.\n'
             '-Waiting Member: A member who has applied for the membership and whose invoice is going to be created.\n'
             '-Invoiced Member: A member whose invoice has been created.\n'
             '-Paying member: A member who has paid the membership fee.')
    membership_start = fields.Date(
        'Membership Start Date', compute='_membership_date', store=True,
        help="Date from which membership becomes active.")
    membership_stop = fields.Date(
        'Membership End Date', compute='_membership_date', store=True,
        help="Date until which membership remains active.")
    membership_cancel = fields.Date(
        'Cancel Membership Date', compute='_membership_date', store=True,
        help="Date on which membership has been cancelled")

    @api.one
    @api.constrains('associate_member_id')
    def _check_recursion(self):
        """Check  Recursive  for Associated Members.
        """
        level = 100
        while len(ids):
            cr.execute('SELECT DISTINCT associate_member FROM res_partner WHERE id IN %s', (tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    # _constraints = [
    #     (_check_recursion, 'Error ! You cannot create recursive associated members.', ['associate_member'])
    # ]

    def create_membership_invoice(self, cr, uid, ids, product_id=None, datas=None, context=None):
        """ Create Customer Invoice of Membership for partners.
        @param datas: datas has dictionary value which consist Id of Membership product and Cost Amount of Membership.
                      datas = {'membership_product_id': None, 'amount': None}
        """
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        invoice_tax_obj = self.pool.get('account.invoice.tax')
        product_id = product_id or datas.get('membership_product_id', False)
        amount = datas.get('amount', 0.0)
        invoice_list = []
        if type(ids) in (int, long,):
            ids = [ids]
        for partner in self.browse(cr, uid, ids, context=context):
            account_id = partner.property_account_receivable and partner.property_account_receivable.id or False
            fpos_id = partner.property_account_position and partner.property_account_position.id or False
            addr = self.address_get(cr, uid, [partner.id], ['invoice'])
            if partner.free_member:
                raise osv.except_osv(_('Error!'),
                        _("Partner is a free Member."))
            if not addr.get('invoice', False):
                raise osv.except_osv(_('Error!'),
                        _("Partner doesn't have an address to make the invoice."))
            quantity = 1
            line_value =  {
                'product_id': product_id,
            }

            line_dict = invoice_line_obj.product_id_change(cr, uid, {},
                            product_id, False, quantity, '', 'out_invoice', partner.id, fpos_id, price_unit=amount, context=context)
            line_value.update(line_dict['value'])
            line_value['price_unit'] = amount
            if line_value.get('invoice_line_tax_id', False):
                tax_tab = [(6, 0, line_value['invoice_line_tax_id'])]
                line_value['invoice_line_tax_id'] = tax_tab

            invoice_id = invoice_obj.create(cr, uid, {
                'partner_id': partner.id,
                'account_id': account_id,
                'fiscal_position': fpos_id or False
                }, context=context)
            line_value['invoice_id'] = invoice_id
            invoice_line_id = invoice_line_obj.create(cr, uid, line_value, context=context)
            invoice_obj.write(cr, uid, invoice_id, {'invoice_line': [(6, 0, [invoice_line_id])]}, context=context)
            invoice_list.append(invoice_id)
            if line_value['invoice_line_tax_id']:
                tax_value = invoice_tax_obj.compute(cr, uid, invoice_id).values()
                for tax in tax_value:
                       invoice_tax_obj.create(cr, uid, tax, context=context)
        #recompute the membership_state of those partners
        self.pool.get('res.partner').write(cr, uid, ids, {})
        return invoice_list