from odoo import api, models, fields
from odoo.tools.misc import str2bool


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_co_dian_operation_mode_ids = fields.One2many(
        string="DIAN Operation Modes",
        comodel_name="l10n_co_dian.operation_mode",
        inverse_name="company_id",
    )
    l10n_co_dian_certificate_ids = fields.One2many(comodel_name='certificate.certificate', inverse_name='company_id')
    l10n_co_dian_test_environment = fields.Boolean(
        string="Test environment",
        inverse='_inverse_l10n_co_dian_test_environment',
        default=True,
    )
    l10n_co_dian_certification_process = fields.Boolean(
        compute='_compute_l10n_co_dian_certification_process',
        inverse='_inverse_l10n_co_dian_certification_process',
        store=True,
        readonly=False,
    )
    l10n_co_dian_provider = fields.Selection(
        selection=[
            ('dian', "DIAN: Free service"),
            ('carvajal', "Carvajal")
        ],
        default=lambda self: self._default_l10n_co_dian_provider(),
    )
    l10n_co_dian_demo_mode = fields.Boolean(
        string="DIAN Demo Mode",
        compute='_compute_l10n_co_dian_demo_mode',
        inverse='_inverse_l10n_co_dian_demo_mode',
    )

    @api.depends('l10n_co_dian_test_environment')
    def _compute_l10n_co_dian_certification_process(self):
        for company in self:
            if not company.l10n_co_dian_test_environment:
                company.l10n_co_dian_certification_process = False

    def _inverse_l10n_co_dian_certification_process(self):
        for company in self:
            if company.l10n_co_dian_certification_process and not company.l10n_co_dian_test_environment:
                company.l10n_co_dian_certification_process = False

    def _default_l10n_co_dian_provider(self):
        carvajal_id = self.env.ref('l10n_co_edi.edi_carvajal').id
        if self.env['account.edi.document'].with_company(self.env.company).search([
            ('edi_format_id', '=', carvajal_id)
        ], limit=1):
            return 'carvajal'
        else:
            return 'dian'

    def _compute_l10n_co_dian_demo_mode(self):
        for company in self:
            company.l10n_co_dian_demo_mode = str2bool(
                self.env['ir.config_parameter'].sudo().get_param(f"l10n_co_dian_demo_mode_{company.id}")
            )

    def _inverse_l10n_co_dian_demo_mode(self):
        for company in self:
            self.env['ir.config_parameter'].sudo().set_param(f"l10n_co_dian_demo_mode_{company.id}", str(company.l10n_co_dian_demo_mode))

    def _inverse_l10n_co_dian_test_environment(self):
        for company in self:
            if company.l10n_co_dian_test_environment:
                company.l10n_co_dian_demo_mode = False
