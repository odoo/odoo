from odoo import models, fields


class AccountAutopostBillsWizard(models.TransientModel):
    _name = 'account.autopost.bills.wizard'
    _description = "Autopost Bills Wizard"

    partner_id = fields.Many2one("res.partner")
    partner_name = fields.Char(related="partner_id.name")
    nb_unmodified_bills = fields.Integer("Number of bills previously unmodified from this partner")

    def action_automate_partner(self):
        for wizard in self:
            wizard.partner_id.autopost_bills = 'always'

    def action_ask_later(self):
        for wizard in self:
            wizard.partner_id.autopost_bills = 'ask'

    def action_never_automate_partner(self):
        for wizard in self:
            wizard.partner_id.autopost_bills = 'never'
