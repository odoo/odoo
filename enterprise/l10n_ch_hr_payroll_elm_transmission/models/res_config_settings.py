from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ch_uses_delegate = fields.Boolean(
        related='company_id.l10n_ch_uses_delegate',
        readonly=False,
        string="Delegate Payroll Accounting",
        help="Enable this option if you delegate payroll accounting tasks to an external provider"
    )
    l10n_ch_swissdec_delegate_name = fields.Char(
        related='company_id.l10n_ch_swissdec_delegate_name',
        readonly=False,
        string="Delegate Name"
    )
    l10n_ch_swissdec_delegate_ch_uid = fields.Char(
        related='company_id.l10n_ch_swissdec_delegate_ch_uid',
        readonly=False,
        string="Delegate Identification Number (IDE-OFS)"
    )
    l10n_ch_delegate_Po_Box = fields.Char(
        related='company_id.l10n_ch_delegate_Po_Box',
        readonly=False,
        string="Delegate PO. Box"
    )
    l10n_ch_delegate_street = fields.Char(
        related='company_id.l10n_ch_delegate_street',
        readonly=False,
        string="Delegate Street"
    )
    l10n_ch_delegate_street2 = fields.Char(
        related='company_id.l10n_ch_delegate_street2',
        readonly=False,
        string="Delegate Street 2"
    )
    l10n_ch_delegate_zip = fields.Char(
        related='company_id.l10n_ch_delegate_zip',
        readonly=False,
        string="Delegate ZIP"
    )
    l10n_ch_delegate_city = fields.Char(
        related='company_id.l10n_ch_delegate_city',
        readonly=False,
        string="Delegate City"
    )
    l10n_ch_delegate_state_id = fields.Many2one(
        'res.country.state',
        domain="[('country_id', '=?', l10n_ch_delegate_country_id)]",
        related='company_id.l10n_ch_delegate_state_id',
        readonly=False,
        string="Delegate State"
    )
    l10n_ch_delegate_country_id = fields.Many2one(
        'res.country',
        related='company_id.l10n_ch_delegate_country_id',
        readonly=False,
        string="Delegate Country"
    )

    l10n_ch_agricole_company = fields.Boolean(
        related='company_id.l10n_ch_agricole_company',
        readonly=False,
        string="Agricultural Company"
    )
    l10n_ch_statistics_convention = fields.Selection(
        related='company_id.l10n_ch_statistics_convention',
        readonly=False,
        string="Statistics Pay Agreement"
    )
    l10n_ch_statistics_payroll_unit = fields.Char(
        related='company_id.l10n_ch_statistics_payroll_unit',
        readonly=False,
        string="Statistics Payroll Unit"
    )
    l10n_ch_contact_person_name = fields.Char(
        related='company_id.l10n_ch_contact_person_name',
        readonly=False,
        string="Contact Person Name"
    )
    l10n_ch_contact_person_email = fields.Char(
        related='company_id.l10n_ch_contact_person_email',
        readonly=False,
        string="Contact Person Email"
    )
    l10n_ch_contact_person_phone = fields.Char(
        related='company_id.l10n_ch_contact_person_phone',
        readonly=False,
        string="Contact Person Phone"
    )
    l10n_ch_30_day_method = fields.Boolean(
        related='company_id.l10n_ch_30_day_method',
        readonly=False,
        string="30-Day Calculation Method",
        help="Compute Salaries based on the 30 day method"
    )

    l10n_ch_transmission_language = fields.Selection(
        related='company_id.l10n_ch_transmission_language',
        readonly=False,
        string="Transmission Language",
        help="Language in which communication with institutions is done")


