# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import UserError, ValidationError

import logging
# import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)


class account_payment(models.Model):
    _name = 'account.payment'
    _inherit = 'account.payment'

    check_id = fields.Many2one('check_managment.check', ondelete='set null', string="Check Details", index=True)
    payment_method_2 = fields.Selection([('cash', 'Cash'),('credit_card','Credit Card'),('bank_transfer','Bank Transfer'),('bank_deposit','Bank Deposit') ,('cheque','Cheque')], "Payment Method" ,  required =True)


    account = fields.Many2one('account.account', ondelete='set null', string="Account", index=True)

    @api.multi
    def _get_default_pay_rec_cash_account(self):
        conf = self.env['check_managment.payment_cofig'].search([('id', '>', 0)])
        conf_cash_account = conf.get_main_cash_default_account()
        return conf_cash_account or False

    @api.multi
    def _get_default_rec_credit_card_account(self):
        conf = self.env['check_managment.payment_cofig'].search([('id', '>', 0)])
        conf_merchant_account = conf.get_merchant_settlement_account()
        return conf_merchant_account or False

    @api.multi
    def _get_default_rec_credit_card_cc_fee_account(self):
        conf = self.env['check_managment.payment_cofig'].search([('id', '>', 0)])
        conf_credit_card__fee_account = conf.get_credit_card__fee_account()
        return conf_credit_card__fee_account or False

    @api.multi
    def _get_default_card_fee_percent(self):
        conf = self.env['check_managment.payment_cofig'].search([('id', '>', 0)])
        conf_credit_card__fee_percent= conf.get_card_fee_percent()
        return conf_credit_card__fee_percent or 0


    pay_rec_cash_account = fields.Many2one('account.account', ondelete='set null', string="Cash Account", index=True  )#, default=_get_default_pay_rec_cash_account)



    rec_credit_card_account = fields.Many2one('account.account', ondelete='set null', string="Credit card Account", index=True)# , default =_get_default_rec_credit_card_account )
    rec_credit_card_cc_fee_account = fields.Many2one('account.account', ondelete='set null', string="CC fee Account", index=True)# , default = _get_default_rec_credit_card_cc_fee_account)
    pay_credit_card_account = fields.Many2one('account.account', ondelete='set null', string="Credit card Account", index=True)
    pay_rec_bank_trans_account = fields.Many2one('account.account', ondelete='set null', string="Bank Trans Account", index=True)
    pay_rec_bank_deposit_account = fields.Many2one('account.account', ondelete='set null', string="Bank Deposit Account", index=True)

    card_fee_percent = fields.Float(string='Card fee % ' , default = _get_default_card_fee_percent)
    card_fee_amount = fields.Float(string='Card fee Amount'  ,compute='_compute_fee', readonly=True )

    extra_ids = fields.One2many('account.payment.extra', 'payment_id', string='Extras ', copy=True)

    # Default values that need to be set

    @api.multi
    @api.constrains(
        'card_fee_percent'
    )
    @api.depends('card_fee_percent')
    def check_validation(self):

        if self.card_fee_percent < 0 or self.card_fee_percent > 100:
            raise UserError(
                _('Credit card fees should fall between 0 - 100 '))


    @api.constrains(
        'card_fee_percent' ,
        'amount'
    )
    @api.depends('card_fee_percent','amount')
    @api.one
    def _compute_fee(self):
         if self.card_fee_percent == 0 or (self.card_fee_percent and self.card_fee_percent > 0 and self.card_fee_percent < 1001 and self.payment_method_2 == u'credit_card') :
             amount  =   (self.card_fee_percent /100) * self.amount ;
             self.card_fee_amount = amount
        # else :
         #    raise UserError(
          #       _('Credit card fees should fall between 0 - 100 '))

    @api.multi
    def get_default_pay_rec_cash_account(self):
         conf = self.env['check_managment.payment_cofig'].search([('id', '>', 0)])
         conf_cash_account = conf.get_main_cash_default_account()
         return conf_cash_account or False

    @api.multi
    @api.constrains(
        'check_id',
        'id'
    )
    @api.depends('check_id')
    def check_validation(self):
       if  self.check_id.id :
         same_check = self.search([('check_id', '=', self.check_id.id)])
         same_check -= self
         if same_check :
             raise UserError(
               _('This Cheque is Already used for other payment'))

    @api.multi
    @api.constrains(
        'payment_method_2'
    )
   ## @api.depends('payment_method_2')
    def pick_cof_accounts(self):
        conf = self.env['check_managment.payment_cofig'].search([('id', '>', 0)])
        if self.payment_method_2 == u'cash' :
            conf_cash_account = conf.get_main_cash_default_account()
            self.account = conf_cash_account
        if self.payment_method_2 == u'cheque':
            self.account = conf.get_merchant_settlement_account()
        if self.payment_method_2 == u'credit_card':
            self.account = conf.get_merchant_settlement_account()
        if self.payment_method_2 == u'bank_transfer':
            self.account = conf.get_merchant_settlement_account()
        if self.payment_method_2 == u'bank_deposit':
            self.account = conf.get_merchant_settlement_account()

    @api.multi
    def set_trasnacion_account(self):
        global account
        if self.payment_type == 'inbound' :
            if self.payment_method_2 == u'cash' :
               account =  self.pay_rec_cash_account
            if self.payment_method_2 == u'credit_card':
                account =  self.rec_credit_card_account
            if self.payment_method_2 == u'bank_transfer':
                account =  self.pay_rec_bank_trans_account
            if self.payment_method_2 == u'bank_deposit':
                account = self.pay_rec_bank_deposit_account


        if self.payment_type == 'outbound':
            if self.payment_method_2 == u'cash':
                account = self.pay_rec_cash_account
            if self.payment_method_2 == u'credit_card':
                account = self.pay_credit_card_account
            if self.payment_method_2 == u'bank_transfer':
                account = self.pay_rec_bank_trans_account
            if self.payment_method_2 == u'bank_deposit':
                account = self.pay_rec_bank_deposit_account

        if self.payment_type == 'transfer':

            if self.payment_method_2 == u'bank_transfer':
                account = self.pay_rec_bank_trans_account
            if self.payment_method_2 == u'bank_deposit':
                account = self.pay_rec_bank_deposit_account

        self.account = account


    def _get_counterpart_move_line_vals(self, invoice=False):

        if self.payment_type == 'transfer':
            name = self.name
        else:
            name = ''
            if self.partner_type == 'customer':
                if self.payment_type == 'inbound':
                    name += _("Customer Payment")
                elif self.payment_type == 'outbound':
                    name += _("Customer Refund")
            elif self.partner_type == 'supplier':
                if self.payment_type == 'inbound':
                    name += _("Vendor Refund")
                elif self.payment_type == 'outbound':
                    name += _("Vendor Payment")
            if invoice:
                name += ': '
                for inv in invoice:
                    if inv.move_id:
                        name += inv.number + ', '
                name = name[:len(name) - 2]
        vals = {
            'name': name,
            'account_id': self.destination_account_id.id,
            # 'account_id': self.check_id.initial_credit_account.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
            'payment_id': self.id,
        }
     # Utravel Code
        self.set_check_type()

        if self.payment_method_code in ('received_check', 'delivered_check')  :
           self.check_id.create_first_transaction()
           vals.update({
               'account_id': self.check_id.initial_credit_account.id

           })
        if self.payment_method_code in ('issue_check')  :
           self.check_id.create_first_transaction()
           vals.update({
               'account_id': self.check_id.initial_debit_account.id

           })

        return vals

    def set_check_type(self):
        if self.payment_method_code in ('received_check'):
            self.check_id.check_type = 1;
        if self.payment_method_code in ('delivered_check', 'issue_check'):
            self.check_id.check_type = 2;

    def _get_liquidity_move_line_vals(self, amount):
        name = self.name
        if self.payment_type == 'transfer':
            name = _('Transfer to %s') % self.destination_journal_id.name
        vals = {
            'name': name,
            'account_id': self.payment_type in ('outbound',
                                                'transfer') and self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id,
            'payment_id': self.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
        }

        # If the journal has a currency specified, the journal item need to be expressed in this currency
        if self.journal_id.currency_id and self.currency_id != self.journal_id.currency_id:
            amount = self.currency_id.with_context(date=self.payment_date).compute(amount, self.journal_id.currency_id)
            debit, credit, amount_currency, dummy = self.env['account.move.line'].with_context(
                date=self.payment_date).compute_amount_fields(amount, self.journal_id.currency_id,
                                                              self.company_id.currency_id)
            vals.update({
                'amount_currency': amount_currency,
                'currency_id': self.journal_id.currency_id.id,
            })

        # Utravel Code
        self.set_check_type()

        if self.payment_method_code in ('received_check' ):
                self.check_id.create_first_transaction()
                vals.update({
                    'account_id': self.check_id.initial_debit_account.id

                })
                self.check_id.amount = amount
        if self.payment_method_code in ( 'delivered_check', 'issue_check'):
            self.check_id.create_first_transaction()
            vals.update({
                        'account_id': self.check_id.initial_credit_account.id

                    })

            self.check_id.amount = amount
        # if (self.payment_method_2  == u'cash') :
        #     vals.update({
        #         'account_id': self.get_debit_account()
        #
        #     })


        return vals


    def _create_payment_entry_old(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoice_currency = False
        if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
            #if all the invoices selected share the same currency, record the paiement in that currency too
            invoice_currency = self.invoice_ids[0].currency_id
        debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id, invoice_currency)

        move = self.env['account.move'].create(self._get_move_vals())

        #Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)

        #Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and self.payment_difference:
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date).compute_amount_fields(self.payment_difference, self.currency_id, self.company_id.currency_id, invoice_currency)
            writeoff_line['name'] = _('Counterpart')
            writeoff_line['account_id'] = self.writeoff_account_id.id
            writeoff_line['debit'] = debit_wo
            writeoff_line['credit'] = credit_wo
            writeoff_line['amount_currency'] = amount_currency_wo
            writeoff_line['currency_id'] = currency_id
            writeoff_line = aml_obj.create(writeoff_line)
            if counterpart_aml['debit']:
                counterpart_aml['debit'] += credit_wo - debit_wo
            if counterpart_aml['credit']:
                counterpart_aml['credit'] += debit_wo - credit_wo
            counterpart_aml['amount_currency'] -= amount_currency_wo
        self.invoice_ids.register_payment(counterpart_aml)

        #Write counterpart lines
        if not self.currency_id != self.company_id.currency_id:
            amount_currency = 0
        liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
        aml_obj.create(liquidity_aml_dict)

        # Utravel Code
        self.set_check_type()

        if self.payment_method_code in ('received_check', 'delivered_check' ,'issue_check'):
             self.check_id.initial_move  =move

             self.check_id.partner_id = self.partner_id

             move.post()
             trans = self.check_id.create_first_transaction()
             trans.status = 1  # posted
        else :
            move.post()

        return move


    def get_debit_account(self):
        self.set_trasnacion_account()
        return  self.account.id





    def get_credit_account(self):

      #  conf = self.env['check_managment.payment_cofig'].search([('id', '>', 0)])
       # conf_cash_account = conf.get_main_cash_default_account()
        # cash with no extra

        if self.payment_method_2 == 'cash' and len(self.extra_ids) == 0:
            return self.destination_account_id.id
                # cash with extra


    def _create_payment_entry(self, amount):
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoice_currency = False
        if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
            # if all the invoices selected share the same currency, record the paiement in that currency too
            invoice_currency = self.invoice_ids[0].currency_id
        debit, credit, amount_currency, currency_id = aml_obj.with_context(
            date=self.payment_date).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id,
                                                          invoice_currency)

        move = self.env['account.move'].create(self._get_move_vals())

        # Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id})





        counterpart_aml = aml_obj.create(counterpart_aml_dict)


        # Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and self.payment_difference:
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(
                date=self.payment_date).compute_amount_fields(self.payment_difference, self.currency_id,
                                                              self.company_id.currency_id, invoice_currency)
            writeoff_line['name'] = _('Counterpart')
            writeoff_line['account_id'] = self.writeoff_account_id.id
            writeoff_line['debit'] = debit_wo
            writeoff_line['credit'] = credit_wo
            writeoff_line['amount_currency'] = amount_currency_wo
            writeoff_line['currency_id'] = currency_id
            writeoff_line = aml_obj.create(writeoff_line)
            if counterpart_aml['debit']:
                counterpart_aml['debit'] += credit_wo - debit_wo
            if counterpart_aml['credit']:
                counterpart_aml['credit'] += debit_wo - credit_wo
            counterpart_aml['amount_currency'] -= amount_currency_wo
        self.invoice_ids.register_payment(counterpart_aml)

        # Write counterpart lines
        if not self.currency_id != self.company_id.currency_id:
            amount_currency = 0
        liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))


        if(self.payment_method_2 != u'cheque') :
         liquidity_aml_dict.update({'account_id': self.get_debit_account()})

        if self.payment_method_2 == u'credit_card' and self.payment_type in ('inbound') :
            self.create_credit_card_journal(liquidity_aml_dict , aml_obj)
        else :
         if len(self.extra_ids) > 0 and self.payment_method_2 != u'cheque'  :
             self.update_extra_entries(liquidity_aml_dict , aml_obj)
         else :
           aml_obj.create(liquidity_aml_dict)

           # Utravel Code

           self.set_check_type()

           if self.payment_method_code in ('received_check', 'delivered_check', 'issue_check'):
               self.check_id.initial_move = move

               self.check_id.partner_id = self.partner_id

               move.post()
               trans = self.check_id.create_first_transaction()
               trans.status = 1  # posted
               return  move

        move = self.fix_currency_difference(move)
        move.post()
        return move

    def fix_currency_difference(self,move):
        debit = 0
        credit= 0

        if len(self.extra_ids) > 0:
         for line in move.line_ids :
            debit += line.debit
            credit += line.credit
         bigger = ''
         if debit == credit :
             return  move
         if debit > credit :
             diff = debit - credit
             bigger = 'debit'
         elif debit < credit :
             diff = credit -debit
             bigger = 'credit'
         if diff > 0 and diff <1 :
             if move.line_ids[0].credit > 0 :
                 if bigger== 'credit' :
                     move.line_ids[0].credit -= diff
                     return  move
                 if bigger== 'debit' :
                     move.line_ids[0].credit += diff
                     return  move
             if move.line_ids[0].debit > 0:
                 if bigger == 'credit':
                     move.line_ids[0].debit += diff
                     return move
                 if bigger == 'debit':
                     move.line_ids[0].debit -= diff
                     return move

        return  move


    def create_credit_card_journal(self,liquidity_aml_dict ,aml_obj):
        if liquidity_aml_dict['debit'] > 0:
           liquidity_aml_dict.update(
                {'debit': liquidity_aml_dict['debit'] - self.get_amount_in_def_currency(aml_obj,self.card_fee_amount) })
           if self.currency_id != self.company_id.currency_id :
            liquidity_aml_dict.update(
               {'amount_currency': liquidity_aml_dict['amount_currency'] - self.card_fee_amount})
        else:
            liquidity_aml_dict.update({'credit': liquidity_aml_dict['credit'] - self.get_amount_in_def_currency(aml_obj,self.card_fee_amount)})
            if self.currency_id != self.company_id.currency_id:
             liquidity_aml_dict.update(
                {'amount_currency': liquidity_aml_dict['amount_currency'] + self.card_fee_amount})

        if len(self.extra_ids) > 0:
            self.update_extra_entries(liquidity_aml_dict, aml_obj)
        else:
            aml_obj.create(liquidity_aml_dict)



        if self.payment_type == 'inbound' :
           liquidity_aml_dict.update({'account_id': self.rec_credit_card_cc_fee_account.id})
           liquidity_aml_dict.update(
                  {'debit': self.get_amount_in_def_currency(aml_obj,self.card_fee_amount)})
           if self.currency_id != self.company_id.currency_id:
            liquidity_aml_dict.update(
               {'amount_currency':  self.card_fee_amount})
           liquidity_aml_dict.update( {'credit': 0})
           liquidity_aml_dict.update({'name': 'credit card fees'})
        # commented as wasim said for the payment no credit card fees are required
        # if self.payment_type == 'outbound':
        #     liquidity_aml_dict.update({'account_id': self.rec_credit_card_accoun.idt})
        #     liquidity_aml_dict.update(
        #         {'debit':  self.card_fee_amount})
        #     liquidity_aml_dict.update({'debit': 0})

        aml_obj.create(liquidity_aml_dict)



## for stting up the extra entries
    def update_extra_entries(self,liquidity_aml_dict ,aml_obj):
        if self.payment_method_2 in  ( u'cash' , u'bank_transfer' , u'bank_deposit' , u'credit_card' ) :
            if liquidity_aml_dict['debit'] > 0:
                liquidity_aml_dict.update(
                    {'debit': liquidity_aml_dict['debit'] + self.get_total_extras()})
                if self.currency_id != self.company_id.currency_id:
                 liquidity_aml_dict.update(
                    {'amount_currency': liquidity_aml_dict['amount_currency'] + self.get_total_extras_amount_currncy()})

            else:
                liquidity_aml_dict.update(
                    {'credit': liquidity_aml_dict['credit'] + self.get_total_extras()})
                if self.currency_id != self.company_id.currency_id:
                 liquidity_aml_dict.update(
                    {'amount_currency': liquidity_aml_dict['amount_currency'] - self.get_total_extras_amount_currncy()})


        aml_obj.create(liquidity_aml_dict)

        for extra in self.extra_ids:
         if self.payment_type == 'inbound' :
            if (extra.amount > 0):
                liquidity_aml_dict.update({'credit': self.get_extra_amount(extra.amount)})
                if self.currency_id != self.company_id.currency_id:
                 liquidity_aml_dict.update(
                    {'amount_currency':   extra.amount * -1})
                liquidity_aml_dict.update({'debit': 0})
                liquidity_aml_dict.update({'account_id': extra.account.id})
                liquidity_aml_dict.update({'name': extra.name})
                aml_obj.create(liquidity_aml_dict)
            if (extra.amount < 0):
                liquidity_aml_dict.update({'debit': self.get_extra_amount( extra.amount ) })
                if self.currency_id != self.company_id.currency_id:
                 liquidity_aml_dict.update(
                    {'amount_currency':  extra.amount  * -1})
                liquidity_aml_dict.update({'credit': 0})
                liquidity_aml_dict.update({'account_id': extra.account.id})
                liquidity_aml_dict.update({'name': extra.name})
                aml_obj.create(liquidity_aml_dict)
         if self.payment_type == 'outbound':
             if (extra.amount > 0):
                 liquidity_aml_dict.update({'debit': self.get_extra_amount(extra.amount)})
                 if self.currency_id != self.company_id.currency_id:
                  liquidity_aml_dict.update(
                     {'amount_currency': extra.amount })
                 liquidity_aml_dict.update({'credit': 0})
                 liquidity_aml_dict.update({'account_id': extra.account.id})
                 liquidity_aml_dict.update({'name': extra.name})
                 aml_obj.create(liquidity_aml_dict)
             if (extra.amount < 0):
                 liquidity_aml_dict.update({'credit':self.get_extra_amount( extra.amount )})
                 if self.currency_id != self.company_id.currency_id:
                  liquidity_aml_dict.update(
                     {'amount_currency':  extra.amount })
                 liquidity_aml_dict.update({'debit': 0})
                 liquidity_aml_dict.update({'account_id': extra.account.id})
                 liquidity_aml_dict.update({'name': extra.name})
                 aml_obj.create(liquidity_aml_dict)

    def get_total_extras(self):
        total = 0;
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoice_currency = False
        if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
            # if all the invoices selected share the same currency, record the paiement in that currency too
            invoice_currency = self.invoice_ids[0].currency_id


        for extra in self.extra_ids:
            debit, credit, amount_currency, currency_id = aml_obj.with_context(
                date=self.payment_date).compute_amount_fields(extra.amount, self.currency_id, self.company_id.currency_id,
                                                       invoice_currency)
            if (debit > credit):
                total += debit
            else:
                total -= credit

        return  total

    def get_total_extras_amount_currncy(self):
        total = 0;

        for extra in self.extra_ids:

                total += extra.amount

        return total

    def get_extra_amount(self,extra_amount):
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoice_currency = False
        if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
            # if all the invoices selected share the same currency, record the paiement in that currency too
            invoice_currency = self.invoice_ids[0].currency_id
        debit, credit, amount_currency, currency_id = aml_obj.with_context(
            date=self.payment_date).compute_amount_fields(extra_amount, self.currency_id, self.company_id.currency_id,
                                                          invoice_currency)
        if(debit > credit) :
            return  debit
        else:
            return credit

    def get_amount_in_def_currency(self ,aml_obj, amount):
        invoice_currency = False
        if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
            # if all the invoices selected share the same currency, record the paiement in that currency too
            invoice_currency = self.invoice_ids[0].currency_id
        debit, credit, amount_currency, currency_id = aml_obj.with_context(
            date=self.payment_date).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id,
                                                          invoice_currency)
        if (debit > credit):
            return debit
        else:
            return credit


class account_payment_extra(models.Model):
    _name = 'account.payment.extra'

    payment_id =  fields.Many2one('account.payment', ondelete='set null', string="payment", index=True , readonly = True)
    amount =  fields.Float(string='Amount' ,required =True)
    account = fields.Many2one('account.account', ondelete='set null', string="Account", index=True , required =True)
    name = fields.Char(string='Description' , required =True)


    def get_total_extra_amount_currency(self):
        total = 0 ;
        for rec in self :
            total += rec.amount

        return  total


