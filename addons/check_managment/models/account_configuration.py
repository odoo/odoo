from openerp import fields, models, api ,_
from openerp.exceptions import UserError, ValidationError

class account_configuration(models.Model):
    _name = 'check_managment.payment_cofig'


    main_cash_default_account = fields.Many2one('account.account', ondelete='set null', string="Main cash default account", index=True)
    merchant_settlement_account = fields.Many2one('account.account', ondelete='set null',
                                                string="Merchant settlement account", index=True)
    credit_card__fee_account = fields.Many2one('account.account', ondelete='set null',
                                                  string="Credit card fee account", index=True)

    default_card_fee_percent = fields.Float(string = 'Default card fee %')

    @api.multi
    @api.constrains(
        'default_card_fee_percent'
    )
    @api.depends('default_card_fee_percent')
    def check_validation(self):

        if self.default_card_fee_percent < 0 or self.default_card_fee_percent > 100:
            raise UserError(
                _('Credit card fees should fall between 0 - 100 '))

    def get_main_cash_default_account(self):

        for rec in self:
            return rec.main_cash_default_account
        return 0

    def get_merchant_settlement_account(self):

        for rec in self:
            return rec.merchant_settlement_account
        return 0

    def get_credit_card__fee_account(self):

        for rec in self:
            return rec.credit_card__fee_account
        return 0

    def get_card_fee_percent(self):

        for rec in self:
            return rec.default_card_fee_percent
        return 0