from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



class AccountJournal(models.Model):

    _inherit = "account.journal"

    l10n_ec_entity = fields.Char(string="Emission Entity", size=3, copy=False)
    l10n_ec_emission = fields.Char(string="Emission Point", size=3, copy=False)
    l10n_ec_emission_address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Emission address",
        domain="['|', ('id', '=', company_partner_id), '&', ('id', 'child_of', company_partner_id), ('type', '!=', 'contact')]",
    )

    #TODO: On next release deprecate field as is it has no use
    l10n_ec_emission_type = fields.Selection(
        string="Emission type",
        selection=[
            ("pre_printed", "Pre Printed"),
            ("auto_printer", "Auto Printer"),
            ("electronic", "Electronic"),
        ],
        default="electronic",
    )

    @api.constrains('l10n_ec_entity', 'l10n_ec_emmision')
    def l10n_ec_check_moves_entity_emmision(self):
        for journal in self:
            if self.env['account.move'].search([('journal_id', '=', journal.id), ('posted_before', '=', True)], limit=1):
                raise ValidationError(_(
                    'You can not modify the field "Emission Entity or Emission Point" if there are validated invoices in this journal!'))
