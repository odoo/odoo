from stdnum.pt import nif

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, RedirectWarning, UserError
from odoo.tools.misc import format_datetime

from odoo.addons.l10n_pt_certification.const import PT_AT_WS_ENDPOINT_TEST, PT_AT_WS_ENDPOINT_PROD
from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_pt_region_code = fields.Char('Region Code', compute='_compute_l10n_pt_region_code', store=True, readonly=False)
    l10n_pt_clock_confirmed_entry_date = fields.Datetime(
        string="System Clock Confirmed Against",
        readonly=True,
        help="The SystemEntryDate of the last issued document when a user confirmed that the system "
             "clock, although earlier, was correct.",
    )
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

    def _l10n_pt_get_last_system_entry_date(self):
        """The latest SystemEntryDate of any document issued under the root company's NIF, branches included."""
        self.ensure_one()
        last_dates = []
        for model_name in self.env['l10n_pt.at.series']._l10n_pt_document_models():
            # sudo: every branch's documents count, whichever companies the user may see.
            documents = self.env[model_name].sudo()
            if 'l10n_pt_hashed_on' not in documents._fields:
                continue
            [(last_date,)] = documents._read_group(
                [('company_id', 'child_of', self.root_id.id), ('l10n_pt_hashed_on', '!=', False)],
                aggregates=['l10n_pt_hashed_on:max'],
            )
            if last_date:
                last_dates.append(last_date)
        return max(last_dates, default=False)

    def _l10n_pt_check_system_clock(self):
        """
        Before issuing, a system date and time earlier than that of the last document issued, of any
        type and series, has to be confirmed by the user (Despacho 8632/2014 3.4.3). Confirming
        holds until a later document is issued.
        """
        now = fields.Datetime.now()
        for root in self.root_id:
            last_date = root._l10n_pt_get_last_system_entry_date()
            confirmed = root.l10n_pt_clock_confirmed_entry_date
            if last_date and now < last_date and not (confirmed and confirmed >= last_date):
                raise RedirectWarning(
                    _(
                        "The system date and time (%(now)s) are earlier than those of the last document "
                        "issued (%(last)s). Check the clock of the server. If it is correct, confirm it, "
                        "then issue the document again.",
                        now=format_datetime(self.env, now),
                        last=format_datetime(self.env, last_date),
                    ),
                    self.env.ref('l10n_pt_certification.action_l10n_pt_confirm_system_clock').id,
                    _("The clock is correct"),
                )

    def _l10n_pt_check_company_vat(self):
        """
        A document is issued under the NIF of its company, which it prints, signs and exports to the
        SAF-T: a missing or invalid one has to be fixed before the document is numbered and signed.
        """
        if self.filtered(lambda company: not company.vat or not nif.is_valid(company.vat)):
            raise RedirectWarning(
                _("Please define the VAT on your company (e.g. PT123456789)"),
                self.env.ref('base.action_res_company_form').id,
                _("Company Settings"),
            )

    @api.model
    def _l10n_pt_confirm_system_clock(self):
        """Run from the warning of `_l10n_pt_check_system_clock`, by the user it was shown to."""
        for root in self.env.companies.root_id:
            # sudo: any user issuing documents confirms the clock, not only those who may edit the company.
            root.sudo().l10n_pt_clock_confirmed_entry_date = root._l10n_pt_get_last_system_entry_date()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("The system date and time are confirmed. Issue the document again."),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

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
        message = pt_hash_utils.get_message_to_hash(move._l10n_pt_get_hash_values(), previous_hash)
        return pt_hash_utils.verify_integrity(
            message, move.inalterable_hash, versioning_list[current_versioning_index],
        ), current_versioning_index
