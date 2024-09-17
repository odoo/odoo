import re
from odoo import models, fields, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_sa_private_key_id = fields.Many2one(string="ZATCA Private key", comodel_name='certificate.key', copy=False, domain=[('public', '=', False)],
                                        help="The private key used to generate the CSR and obtain certificates",)

    l10n_sa_api_mode = fields.Selection(
        [('sandbox', 'Sandbox'), ('preprod', 'Simulation (Pre-Production)'), ('prod', 'Production')],
        help="Specifies which API the system should use", required=True,
        default='sandbox', copy=False)

    l10n_sa_edi_building_number = fields.Char(compute='_compute_address',
                                              inverse='_l10n_sa_edi_inverse_building_number')
    l10n_sa_edi_plot_identification = fields.Char(compute='_compute_address',
                                                  inverse='_l10n_sa_edi_inverse_plot_identification')

    l10n_sa_additional_identification_scheme = fields.Selection(
        related='partner_id.l10n_sa_additional_identification_scheme', readonly=False)
    l10n_sa_additional_identification_number = fields.Char(
        related='partner_id.l10n_sa_additional_identification_number', readonly=False)

    def _get_company_root_delegated_field_names(self):
        return super()._get_company_root_delegated_field_names() + [
            'l10n_sa_api_mode',
            'l10n_sa_private_key_id',
        ]

    def write(self, vals):
        for company in self:
            if 'l10n_sa_api_mode' in vals:
                if company.l10n_sa_api_mode == 'prod' and vals['l10n_sa_api_mode'] != 'prod':
                    raise UserError(_("You cannot change the ZATCA Submission Mode once it has been set to Production"))
                journals = self.env['account.journal'].search(self.env['account.journal']._check_company_domain(company))
                journals._l10n_sa_reset_certificates()
                journals.l10n_sa_latest_submission_hash = False
        return super().write(vals)

    def _get_company_address_field_names(self):
        """ Override to add ZATCA specific address fields """
        return super()._get_company_address_field_names() + \
            ['l10n_sa_edi_building_number', 'l10n_sa_edi_plot_identification']

    def _l10n_sa_edi_inverse_building_number(self):
        for company in self:
            company.partner_id.l10n_sa_edi_building_number = company.l10n_sa_edi_building_number

    def _l10n_sa_edi_inverse_plot_identification(self):
        for company in self:
            company.partner_id.l10n_sa_edi_plot_identification = company.l10n_sa_edi_plot_identification

    def _l10n_sa_get_csr_invoice_type(self):
        """
            Return the Invoice Type flag used in the CSR. 4-digit numerical input using 0 & 1 mapped to “TSCZ” where:
            -   0: False/Not supported, 1: True/Supported
            -   T: Tax Invoice (Standard), S: Simplified Invoice, C & Z will be used in the future and should
                always be 0
            For example: 1100 would mean the Solution will be generating Standard and Simplified invoices.
            We can assume Odoo-powered EGS solutions will always generate both Standard & Simplified invoices
        :return:
        """
        return '1100'

    def _l10n_sa_check_organization_unit(self):
        """
            Check company Organization Unit according to ZATCA specifications
            Standards:
                BR-KSA-39
                BR-KSA-40
            See https://zatca.gov.sa/ar/RulesRegulations/Taxes/Documents/20210528_ZATCA_Electronic_Invoice_XML_Implementation_Standard_vShared.pdf
        """
        self.ensure_one()
        if not self.vat:
            return False
        return len(self.vat) == 15 and bool(re.match(r'^3\d{13}3$', self.vat))
