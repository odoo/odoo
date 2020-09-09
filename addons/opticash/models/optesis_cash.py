from odoo import api, fields, models, _
from odoo.exceptions import UserError

class OptesisCash(models.Model):
    
    @api.model
    def _default_journal(self):
        journals = self.env['account.journal'].search([('type', '=', 'cash')])
        if journals:
            return journals[0]
        return self.env['account.journal']
    
    @api.model
    def _default_opening_balance(self):
        journals = self.env['account.journal'].search([('type', '=', 'cash')])
        if journals:
            last_bnk_stmt = self.search([('journal_id', '=', journals[0].id)], limit=1)
        if last_bnk_stmt:
            return last_bnk_stmt.balance_end
        return 0
    
    @api.one
    @api.depends('payment_lines', 'balance_start', 'payment_lines.cash_amount')
    def _end_balance(self):
        self.total_entry_encoding = sum([line.cash_amount for line in self.payment_lines])
        self.balance_end = self.balance_start + self.total_entry_encoding
        self.balance_end_real = self.balance_end

    
    @api.onchange('journal_id')
    def onchangejournal(self):
        if self.journal_id:
            last_bnk_stmt = self.search([('journal_id', '=', self.journal_id.id)], limit=1, order='create_date desc')
            self.balance_start = last_bnk_stmt.balance_end
        

    _name = "optesis.cash"
    _description = "Fiche de caisse"

    name = fields.Char(string='Référence')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, default=_default_journal)
    date = fields.Date(required=True,  index=True, copy=False, default=fields.Date.context_today)
    accounting_date = fields.Date(string="Date comptable", help="If set, the accounting entries created during the bank statement reconciliation process will be created at this date.\n"
        "This is useful if the accounting period in which the entries should normally be booked is already closed.")
    payment_lines = fields.One2many('optesis.cash.line', 'cash_id', string='Lignes de paiements')
    state = fields.Selection([('open', 'Ouvert'), ('validate', 'Validé'), ('close', 'Cloturé')], default='open')
    balance_start = fields.Float(string='Solde initial', states={'close': [('readonly', True)]}, default=_default_opening_balance)
    balance_end_real = fields.Float('Solde final',  states={'close': [('readonly', True)]}, compute='_end_balance')
    balance_end = fields.Float('Solde calculé', store=True,  compute='_end_balance', help='Balance as calculated based on Opening Balance and transaction lines')
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True, readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('account.bank.statement'))

    

    @api.multi
    def action_validate(self):
        for rec in self:
            rec.write({'state': 'validate'})
        return True

    @api.multi
    def action_close(self):
        for rec in self:
            if rec.balance_end < 0:
                raise UserError(_('La balance de cloture ne doit pas etre négative'))
            rec.write({'state': 'close'})
        return True

class OptesisCashLine(models.Model):
    _name = "optesis.cash.line"
    _description = "Ligne de caisse"

    payment_date = fields.Date(string='Date de paiement', default=fields.Date.context_today, required=True, copy=False)
    communication = fields.Char(string='Mémo')
    partner_id = fields.Many2one('res.partner', string='Partenaire')
    name = fields.Char(readonly=True, copy=False, string="Nom")
    cash_amount = fields.Float(string='Montant de paiement',  required=True)
    cash_id = fields.Many2one('optesis.cash', string='Brouillard de caisse')
    company_id = fields.Many2one('res.company', string='Société',  default=lambda self: self.env.user.company_id)
