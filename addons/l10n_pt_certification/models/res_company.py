from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_pt_region_code = fields.Char('Region Code', compute='_compute_l10n_pt_region_code', store=True, readonly=False)

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
            move.date, move.l10n_pt_hashed_on, move._get_l10n_pt_document_number(), abs(move.amount_total_signed), previous_hash,
        )
        return pt_hash_utils.verify_integrity(
            message, move.inalterable_hash, versioning_list[current_versioning_index],
        ), current_versioning_index
