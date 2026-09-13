from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountAutopostBillsWizard(models.TransientModel):
    _name = "account.autopost.bills.wizard"
    _description = "Autopost Bills Wizard"

    partner_id = fields.Many2one(comodel_name="res.partner")
    partner_name = fields.Char(related="partner_id.name")
    nb_unmodified_bills = fields.Integer(
        string="Number of bills previously unmodified from this partner"
    )

    @_debug.perf.timed
    def action_automate_partner(self):
        _debug.lifecycle("action_automate_partner", records=self)
        for wizard in self:
            wizard.partner_id.autopost_bills = "always"

    @_debug.perf.timed
    def action_ask_later(self):
        _debug.lifecycle("action_ask_later", records=self)
        for wizard in self:
            wizard.partner_id.autopost_bills = "ask"

    @_debug.perf.timed
    def action_never_automate_partner(self):
        _debug.lifecycle("action_never_automate_partner", records=self)
        for wizard in self:
            wizard.partner_id.autopost_bills = "never"
