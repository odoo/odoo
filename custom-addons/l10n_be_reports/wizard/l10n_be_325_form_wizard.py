from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Form325Wizard(models.TransientModel):
    _name = 'l10n_be.form.325.wizard'
    _description = '325 Form Wizard'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != 'BE':
            raise UserError(_("You must be logged in a Belgian company to use this feature"))
        return super(Form325Wizard, self).default_get(field_list)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    sender_id = fields.Many2one(
        'res.partner',
        string='Sender',
        required=True,
        compute='_compute_sender_id', readonly=False, store=True,
        help="The company responsible for sending the form.",
    )
    reference_year = fields.Char(
        string='Reference Year',
        default=lambda x: str(fields.Date.context_today(x).year - 1),
    )
    is_test = fields.Boolean(
        string="Test Form",
        help="Indicates if the 325 is a test",
    )
    sending_type = fields.Selection(
        [
            ('0', 'Original send'),
            ('1', 'Send grouped corrections'),
        ],
        string="Sending Type",
        default='0',
        required=True,
        help="This field allows to make an original sending(correspond to first send) "
             "or a grouped corrections(if you have made some mistakes before).",
    )
    treatment_type = fields.Selection(
        [
            ('0', 'Original'),
            ('1', 'Modification'),
            ('2', 'Add'),
            ('3', 'Cancel'),
        ],
        string="Treatment Type",
        default='0',
        required=True,
        help="This field represents the nature of the form.",
    )

    @api.depends('company_id')
    def _compute_sender_id(self):
        for record in self:
            record.sender_id = record.company_id.account_representative_id or record.company_id.partner_id

    @api.constrains('reference_year')
    def _constrains_reference_year(self):
        for record in self:
            if not record.reference_year.isdigit():
                raise ValidationError(_("The reference year must be a number."))
            if not record.is_test and int(record.reference_year) >= fields.Date.context_today(self).year:
                raise ValidationError(_("You can't use a reference year in the future or for the current year."))

    def action_generate_325_form(self):
        self.ensure_one()

        company_id = self.env.company
        debtor_id = company_id.partner_id

        self.sender_id._check_partner_281_50_required_values(check_phone_number=True)
        debtor_id._check_partner_281_50_required_values(check_phone_number=True)
        form_325 = self.env['l10n_be.form.325'].create({
            'company_id': company_id.id,
            'sender_id': self.sender_id.id,
            'reference_year': self.reference_year,
            'is_test': self.is_test,
            'sending_type': self.sending_type,
            'treatment_type': self.treatment_type,
        })
        form_325._generate_form_281_50()

        return {
            "name": form_325.display_name,
            "type": "ir.actions.act_window",
            "res_model": "l10n_be.form.325",
            "res_id": form_325.id,
            "views": [[False, "form"]],
            "target": "main",
        }
