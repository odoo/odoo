from odoo import fields, models


class L10nBeCodaBoxValidationWizard(models.TransientModel):
    _name = 'l10n_be_codabox.validation.wizard'
    _description = 'CodaBox Validation Wizard'
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    l10n_be_codabox_is_connected = fields.Boolean(related='company_id.l10n_be_codabox_is_connected')
    fidu_password = fields.Char(
        string='Accounting Firm Password',
        help='This is the password you have received from Odoo the first time you connected to CodaBox.',
    )
    confirmation_url = fields.Char(required=True)

    def validate_connection(self):
        self.fidu_password = False  # Avoid storing the password in the DB
        return {
            "type": "ir.actions.act_url",
            "url": self.confirmation_url,
            "target": "self",
        }
