from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_co_dian_operation_mode_ids = fields.One2many(
        string="DIAN Operation Modes",
        related="company_id.l10n_co_dian_operation_mode_ids",
        readonly=False,
        help="Software configurations of DIAN",
    )
    l10n_co_dian_certificate_ids = fields.One2many(
        string="Software Certificates",
        related='company_id.l10n_co_dian_certificate_ids',
        readonly=False,
        help="Certificates to be used for electronic invoicing.",
    )
    l10n_co_dian_test_environment = fields.Boolean(
        string="Test environment",
        related='company_id.l10n_co_dian_test_environment',
        readonly=False,
        help="Activate this checkbox if you’re testing workflows for electronic invoicing.",
    )
    l10n_co_dian_certification_process = fields.Boolean(
        string="Activate the certification process",
        related='company_id.l10n_co_dian_certification_process',
        readonly=False,
        help="Activate this checkbox if you are in the certification process with the DIAN.",
    )
    l10n_co_dian_provider = fields.Selection(
        string="Electronic Invoicing Provider",
        related='company_id.l10n_co_dian_provider',
        readonly=False,
        required=True,
    )
    l10n_co_dian_demo_mode = fields.Boolean(
        string="DIAN Demo Mode",
        related='company_id.l10n_co_dian_demo_mode',
        readonly=False,
        help="Activate this checkbox if you’re testing elecronic invoice flows with internal validation.",
    )
