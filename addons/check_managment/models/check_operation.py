from openerp import fields, models, api ,_
from openerp.exceptions import UserError, ValidationError

class check_operation(models.Model):
    _name = 'check_managment.check_operation'
  
    name = fields.Char(related='operation')
    operation  = fields.Char(string='Operation' ,required =True)
    use_for = fields.Selection([('paid', 'Paid cheque'),('recieved', 'Recieved Cheque')], "Used For" ,required =True)
    initial_operation = fields.Boolean(string = 'Initial Operation')
    final_operation = fields.Boolean(string = 'Final Operation')
    
    
    previous_status = fields.Many2one('check_managment.check_operation', ondelete='set null', string="Previous Operation", index=True)  
    
    has_account_impact = fields.Boolean(string = 'Has account Impact')    
     
    debit = fields.Selection([(1, 'Partner'),(2,'Issuing Bank'),(3,'Other'),(4,'Clearing Bank')], "Debit")
    debit_account = fields.Many2one('account.account', ondelete='set null', string="Debit account", index=True)  
    
    credit = fields.Selection([(1, 'Partner'),(2,'Issuing Bank'),(3,'Other'),(4,'Clearing Bank')], "Credit")
    credit_account = fields.Many2one('account.account', ondelete='set null', string="Credit account", index=True)   
    
    journal_type = fields.Many2one('account.journal', ondelete='set null', string="Journal Type", index=True)

    @api.multi
    @api.constrains(
        'use_for',
        'initial_operation',
        'final_operation'
    )
    @api.depends('initial_operation' , 'final_operation' , 'use_for' )
    def check_validation(self):

        if self.final_operation ==  self.initial_operation and self.final_operation :
            raise UserError(
                _('The Operation should be Unique per Type'))
        if self.final_operation == self.initial_operation and not self.final_operation:
            return True

        else:
            same_op = self.search([('use_for', '=', self.use_for),('initial_operation', '=', self.initial_operation) ,
                                  ('final_operation', '=', self.final_operation)])
            same_op -= self
            if same_op:
              raise UserError(
                _('The Operation should be Unique per Type'))
    
class check(models.Model):
    _name = 'check_managment.check'

    name = fields.Char(related='number')
    number  = fields.Char(string='Ch. Number' ,required =True)
    check_type = fields.Selection([(1, 'Recieved'), (2, 'Paid')], "Check Type")
    issue_date =  fields.Date(string = 'Issue date' ,required =True)
    due_date =  fields.Date(string = 'Due date' ,required =True)
    partner_id = fields.Many2one('res.partner', ondelete='set null', string="Partner", index=True)

    #issue_bank = fields.Many2one('res.bank', ondelete='set null', string="Issue Bank", index=True)
    issue_bank = fields.Many2one('account.journal', ondelete='set null', string="Issue Bank", index=True)
    #clearing_bank = fields.Many2one('res.bank', ondelete='set null', string="Clearing Bank", index=True)
    clearing_bank =  fields.Many2one('account.journal', ondelete='set null', string="Clearing Bank", index=True)
    amount =  fields.Float(string="Amount", decimal_places=2, max_digits=12)
    trasnaction_ids = fields.One2many('check_managment.check_transaction', 'check_id', string='transactions ',
        readonly=False, copy=True)
    initial_debit_account = fields.Many2one('account.account', ondelete='set null', string="Debit account", index=True)
    initial_credit_account = fields.Many2one('account.account', ondelete='set null', string="Debit account", index=True)
    initial_move = fields.Many2one('account.move', ondelete='set null', string="initial move", index=True)
    last_transaction_id = fields.Integer(compute='_last_transaction')
    need_posting  =  fields.Boolean(compute='_need_posting')
    last_operation =  fields.Char(string='Status')
    @api.onchange('issue_date', 'due_date')
    def onchange_date(self):
        if (
                        self.issue_date and self.due_date and
                        self.issue_date > self.due_date):
            self.due_date = False
            raise UserError(
                _('Check Payment Date must be greater than Issue Date'))

    @api.multi
    @api.constrains(
        'check_type',
        'number',
        'issue_bank',
    )
    def _check_unique(self):
        for rec in self:
            if rec.check_type == 'issue_check':
                same_checks = self.search([
                    ('number', '=', rec.number),
                    ('check_type', '=', rec.check_type),
                    ('issue_bank', '=', rec.issue_bank),
                ])
                same_checks -= self
                if same_checks:
                    raise ValidationError(_(
                        'Check Number (%s) must be unique ') % (
                        rec.number))

        return True

    def create_first_transaction(self):
        trans = False
        if self.check_type == 1 : # recieved
           op = self.env["check_managment.check_operation"].search([('initial_operation', '=', True),('use_for', '=', 'recieved')])
        if self.check_type == 2 : # paid
           op = self.env["check_managment.check_operation"].search([('initial_operation', '=', True),('use_for', '=', 'paid')])
        res =  self.env['check_managment.check_transaction'].search([('notes', '=', 'Initial'), ('operation', '=', op.id) ,('check_id', '=', self.id) ])
        if len(res) ==0 :
            trans = self.env['check_managment.check_transaction'].create({'notes': "Initial",'operation':op.id ,'check_id' :self.id})
            #if op.debit_account is not None:
            self.initial_debit_account = self.get_debit_account(trans)
            self.initial_credit_account =  self.get_credit_account(trans) ;
            self.last_operation = op.operation
            return trans
        else :
            self.last_operation = op.operation
            return res

    @api.depends('trasnaction_ids.operation')
    def _need_posting(self):
        trans = self._last_transaction()
        if trans is not None :
           if trans.status == 1 : # posted
             self.need_posting = False
           else:
             self.need_posting = True

    @api.multi
    @api.depends('trasnaction_ids.operation')
    def _last_transaction(self):
       try :
         if len(self.trasnaction_ids.sorted(key=lambda r: -r.id)) > 0 :
           self.last_transaction_id = self.trasnaction_ids.sorted(key=lambda r: -r.id)[0].id
           return self.trasnaction_ids.browse( self.last_transaction_id)
       except:
         pass


    @api.multi
    @api.depends('last_transaction_id')
    def post_last_operation(self):
        trans =  self.env['check_managment.check_transaction'].browse(self.last_transaction_id)
        if trans.status == 2 : # Unposted
           op = trans.operation
           if not op.initial_operation and op.has_account_impact:
              payment =  self.env['account.payment'].search([('check_id', '=', self.id)])

              move = self.initial_move.copy()
              if trans.check_id.check_type == 1 : # Recieved Check
                  if op.debit == 1:  # partner
                      for line in move.line_ids:
                          if line.debit > 0:
                              line.account_id = payment.payment_type in ('outbound',
                                                                      'transfer') and payment.journal_id.default_debit_account_id.id or payment.journal_id.default_credit_account_id.id

                  if op.credit == 1:  # partner

                      for line in move.line_ids:
                          if line.credit > 0:
                              line.account_id = payment.destination_account_id.id

              if trans.check_id.check_type == 2:  # Paid Check
                      if op.debit == 1:  # partner
                          for line in move.line_ids:
                              if line.debit > 0:
                                  line.account_id = payment.destination_account_id.id


                      if op.credit == 1:  # partner

                          for line in move.line_ids:
                              if line.credit > 0:
                                  line.account_id = payment.payment_type in ('outbound',
                                                                             'transfer') and payment.journal_id.default_debit_account_id.id or payment.journal_id.default_credit_account_id.id

              if op.debit == 3 : #Others

                   for line in move.line_ids :
                     if line.debit > 0 :
                       line.account_id = op.debit_account.id
                    # if line.credit > 0 :
                      # line.account_id = op.credit_account.id




              if op.credit == 3 : #Others

                   for line in move.line_ids :

                     if line.credit > 0 :
                       line.account_id = op.credit_account.id

              if op.credit == 2:  # issuing Bank
                  if self.clearing_bank is not None:
                      for line in move.line_ids:

                          if line.credit > 0:
                              line.account_id =  self.issue_bank.default_credit_account_id.id
                  else:
                      raise UserError(
                          _('issuing Bank Account is Emplty'))
              if op.debit == 2:  # issuing Bank
                  if self.clearing_bank is not None:
                      for line in move.line_ids:

                          if line.debit > 0:
                              line.account_id = self.issue_bank.default_debit_account_id.id
                  else:
                      raise UserError(
                          _('issuing Bank Account is Emplty'))

              if op.credit == 4:  # clearing Bank
                  if self.clearing_bank is not None:
                      for line in move.line_ids:

                          if line.credit > 0:
                              line.account_id = self.clearing_bank.default_credit_account_id.id
                  else:
                      raise UserError(
                          _('Clearing Bank Account is Emplty'))
              if op.debit == 4:  # clearing Bank
                  if self.clearing_bank is not None:
                      for line in move.line_ids:

                          if line.debit > 0:
                              line.account_id = self.clearing_bank.default_debit_account_id.id
                  else:
                      raise UserError(
                          _('Clearing Bank Account is Emplty'))
              move.post()
              trans.status = 1 # change to Posted
              self.last_operation = op.operation
           if not op.has_account_impact:
               trans.status = 1
               self.last_operation = op.operation

        if trans.status == 1: #posted
            op = trans.operation
            self.last_operation = op.operation

    @api.multi
    def fix_last_operation(self): # used to fix the missing status for the first operation
       for little_check in self.env['check_managment.check'].search([ ('amount' , '!=','')]):
        trans = little_check._last_transaction()
        if trans.status == 1:  # posted
            op = trans.operation
            little_check.last_operation = op.operation

    def get_debit_account(self, transaction):
        op = transaction.operation
        payment = self.env['account.payment'].search([('check_id', '=', self.id)])
        if transaction.check_id.check_type == 1:  # Recieved Check
            if op.debit == 1:  # partner
                return  payment.payment_type in ('outbound', 'transfer') and payment.journal_id.default_debit_account_id.id or payment.journal_id.default_credit_account_id.id
        if transaction.check_id.check_type == 2:  # Paid Check
            if op.debit == 1:  # partner
                return  payment.destination_account_id.id

        if op.debit == 3:  # Others
               return  op.debit_account.id
        if op.debit == 2:  # Clearing check
            if self.clearing_bank is not None:
                return self.clearing_bank.default_debit_account_id.id
            else:
                raise UserError(
                    _('Clearing Bank Account is Emplty'))
        if op.debit == 4:  # clearing Bank
            if self.clearing_bank is not None:
                return self.clearing_bank.default_debit_account_id.id
            else:
                raise UserError(
                    _('Clearing Bank Account is Emplty'))

    def get_credit_account(self, transaction):
        op = transaction.operation
        payment = self.env['account.payment'].search([('check_id', '=', self.id)])
        if transaction.check_id.check_type == 1:  # Recieved Check
            if op.credit == 1:  # partner
               return payment.destination_account_id.id
        if transaction.check_id.check_type == 2:
            if op.credit == 1:  # partner
               return payment.payment_type in ('outbound', 'transfer') and payment.journal_id.default_debit_account_id.id or payment.journal_id.default_credit_account_id.id
        if op.credit == 3:  # Others
            return op.credit_account.id
        if op.credit == 2 : # Clearing check
            if self.clearing_bank is not None :
                return self.clearing_bank.default_credit_account_id.id
            else :
                raise UserError(
                    _('Clearing Bank Account is Emplty'))
        if op.credit == 4:  # clearing Bank
            if self.clearing_bank is not None:
                return self.clearing_bank.default_credit_account_id.id
            else:
                raise UserError(
                    _('Clearing Bank Account is Emplty'))

class check_transaction(models.Model):
    _name = 'check_managment.check_transaction'
    
    operation_date =  fields.Date(string = 'Operation Date' )

    operation = fields.Many2one('check_managment.check_operation', ondelete='set null', string="Operation", index=True ,required =True )
    check_id = fields.Many2one('check_managment.check', ondelete='set null', string="check", index=True)
    bank_account = fields.Many2one('account.account', ondelete='set null', string="Bank Account", index=True)
    notes = fields.Char(string = 'Notes :')
    status =  fields.Selection([(1, 'Posted'),(2, 'Un-posted')], "Status",default=2)
    debit_account = fields.Many2one('account.account', ondelete='set null', string="Debit account", index=True)
    credit_account = fields.Many2one('account.account', ondelete='set null', string="Credit account", index=True)

    @api.multi
    @api.constrains(
        'check_id',
        'operation'
    )
    @api.depends('check_idn' ,'operation')
    def _check_validity(self):
        for rec in self:
             same_operation = self.search([
                    ('check_id', '=', rec.check_id.id),
                    ('operation', '=', rec.operation.id)

                ])
             same_operation -= self
             if same_operation:
                    raise ValidationError(_(
                        'The Operation (%s) is already registered on this check ') % (
                                              rec.operation.name))
             unposted = self.search([
                    ('status', '=', 2),('check_id', '=', rec.check_id.id)])
             unposted -= self
             if unposted :
                 raise ValidationError(_(
                     'there are unposted transactions on on the check , Please Post it first  ') )

             if self.operation.use_for  == 'paid' and self.check_id.check_type == 2 :
                 return  True
             elif self.operation.use_for == 'recieved' and self.check_id.check_type == 1:
                 return True
             else :
                 raise ValidationError(_(
                     'The Operation should Match the Cheque type (Issued or Recieved)'))


        return True







     