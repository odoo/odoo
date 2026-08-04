from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.l10n_pt_certification.const import PT_AT_WS_ENDPOINT_TEST, PT_AT_WS_ENDPOINT_PROD
from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_pt_region_code = fields.Char('Region Code', compute='_compute_l10n_pt_region_code', store=True, readonly=False)
    l10n_pt_at_ws_env = fields.Selection(
        selection=[
            ('prod', 'Production'),
            ('test', 'Test'),
            ('offline', 'Offline (no connection)'),
        ],
        string="AT Webservice Environment",
        default='offline',
    )
    l10n_pt_at_ws_username = fields.Char(
        string='AT Webservice Username',
        groups='base.group_system',
        help="Username (NIF/sub-user ID) for the Autoridade Tributária Series webservice.",
    )
    l10n_pt_at_ws_password = fields.Char(
        string='AT Webservice Password',
        groups='base.group_system',
        help="Password for the Autoridade Tributária Series webservice.",
    )
    l10n_pt_at_ws_public_cert_id = fields.Many2one(
        comodel_name='certificate.certificate',
        string='AT Public Key Certificate',
        groups='base.group_system',
        help="The AT public key certificate used to encrypt the password sent to the Series webservice.",
        check_company=True,
    )
    l10n_pt_at_ws_ssl_certificate_ids = fields.One2many(
        comodel_name='certificate.certificate',
        inverse_name='company_id',
        domain=[('scope', '=', 'at_series')],
    )
    l10n_pt_at_ws_ssl_certificate_id = fields.Many2one(
        string="SSL Certificate (AT Series)",
        comodel_name='certificate.certificate',
        compute='_compute_l10n_pt_at_ws_ssl_certificate',
        store=True,
        readonly=False,
    )

    @api.depends('country_id', 'l10n_pt_at_ws_ssl_certificate_ids')
    def _compute_l10n_pt_at_ws_ssl_certificate(self):
        for company in self:
            if company.country_code == 'PT':
                company.l10n_pt_at_ws_ssl_certificate_id = self.env['certificate.certificate'].search(
                    [('company_id', '=', company.id), ('is_valid', '=', True), ('scope', '=', 'at_series')],
                    order='date_end desc',
                    limit=1,
                )
            else:
                company.l10n_pt_at_ws_ssl_certificate_id = False

    def _l10n_pt_at_ws_get_soap_endpoint(self):
        self.ensure_one()
        if self.l10n_pt_at_ws_env == 'prod':
            return PT_AT_WS_ENDPOINT_PROD
        return PT_AT_WS_ENDPOINT_TEST

    @api.depends('country_id', 'state_id')
    def _compute_l10n_pt_region_code(self):
        for company in self.filtered(lambda c: c.country_id.code == 'PT'):
            if company.state_id == self.env.ref('base.state_pt_pt-20'):
                company.l10n_pt_region_code = 'PT-AC'
            elif company.state_id == self.env.ref('base.state_pt_pt-30'):
                company.l10n_pt_region_code = 'PT-MA'
            else:
                company.l10n_pt_region_code = 'PT'

    @api.onchange('country_id')
    def onchange_country(self):
        """
        Portuguese companies use round_globally as tax_calculation_rounding_method to ensure
        rounding conforms with the requirements from Autoridade Tributaria
        """
        for company in self.filtered(lambda c: c.country_id.code == "PT"):
            company.tax_calculation_rounding_method = 'round_globally'

    def _get_hash_versioning_list(self):
        if self.account_fiscal_country_id.code != 'PT':
            return super()._get_hash_versioning_list()
        return list(pt_hash_utils.get_public_keys(self.env).values())

    def _check_hash_integrity(self):
        # EXTEND account
        try:
            return super()._check_hash_integrity()
        except AccessError as e:
            if self.account_fiscal_country_id.code == 'PT':
                raise UserError(
                    _("This company has AT Series shared across branches, and other companies also have hashed documents under this series. "
                      "To generate the report, please also select %s in the company selector.", e.context['suggested_company']['display_name']))
            raise

    def _verify_hashed_move(self, move, previous_hash, versioning_list, current_versioning_index):
        if self.account_fiscal_country_id.code != 'PT':
            return super()._verify_hashed_move(move, previous_hash, versioning_list, current_versioning_index)
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        message = pt_hash_utils.get_message_to_hash(
            move.date, move.l10n_pt_hashed_on, move._l10n_pt_get_document_number(), abs(move.amount_total_signed), previous_hash,
        )
        return pt_hash_utils.verify_integrity(
            message, move.inalterable_hash, versioning_list[current_versioning_index],
        ), current_versioning_index
