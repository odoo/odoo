from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools.partner_identifiers import normalize_identifier
from odoo.addons.l10n_sa.tools.partner_identifiers import COMPANY_SCHEMES, SA_ADDITIONAL_IDENTIFIERS_METADATA


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('additional_identifiers')
    def _compute_available_additional_identifiers_metadata(self):
        super()._compute_available_additional_identifiers_metadata()

        for partner in self:
            metadata = partner.available_additional_identifiers_metadata
            if partner.country_code == 'SA' and metadata:
                sa_identifier_in_use = [k for k in (partner.additional_identifiers or {}) if 'SA' in (metadata[k].get('countries') or [])]
                if not sa_identifier_in_use:
                    continue
                partner.available_additional_identifiers_metadata = {
                    k: v for k, v in partner.available_additional_identifiers_metadata.items()
                    if 'SA' not in (v.get('countries') or []) or k in sa_identifier_in_use
                }

    @api.depends('additional_identifiers')
    def _compute_is_company(self):
        """ Determines if a Saudi partner is a company or an individual based on VAT and
        additional identification fields.
        """
        l10n_sa_commercial_partners = self.filtered(
            lambda p: (
                p.country_code == 'SA'
                and p.commercial_partner_id == p
                and p._is_vat_void(p.vat)
                and any(
                        k in COMPANY_SCHEMES and v
                        for k, v in (p.additional_identifiers or {}).items()
                    )
            )
        )
        l10n_sa_non_sa_commercial_partners = self.filtered(
            lambda p: (
                p.country_code != 'SA'
                and p.commercial_partner_id == p
                and p._get_additional_identifier('SA_OTH')
            )
        )
        (l10n_sa_commercial_partners | l10n_sa_non_sa_commercial_partners).is_company = True
        super(ResPartner, self - l10n_sa_commercial_partners - l10n_sa_non_sa_commercial_partners)._compute_is_company()

    @api.model
    def _l10n_sa_get_tin_from_vat(self, vat):
        # For Saudi TIN is always the first 10 digits of VAT
        return normalize_identifier(vat)[:10]

    @api.onchange('vat', 'additional_identifiers')
    def _onchange_populate_sa_tin_from_vat(self):
        identifiers = self.additional_identifiers or {}
        # A falsy 'SA_TIN' can only exist here transiently, mid-onchange: the js `onAdd`
        # sets it to "" before `_clean_additional_identifiers`/`_set_additional_identifier` run.
        # Post-save this state is impossible, so this will not always return early.
        if 'SA_TIN' not in identifiers or identifiers.get('SA_TIN'):
            return
        tin = self._l10n_sa_get_tin_from_vat(self.vat)
        if not tin:
            return
        self.additional_identifiers = {**identifiers, 'SA_TIN': tin}

    def _get_all_additional_identifiers_metadata(self):
        return {
            **super()._get_all_additional_identifiers_metadata(),
            **SA_ADDITIONAL_IDENTIFIERS_METADATA,
        }

    def _clean_additional_identifiers(self, vals):
        """Only one 'SA' additional identifier should be present in additional identifiers"""
        super()._clean_additional_identifiers(vals)

        identifiers = vals.get('additional_identifiers')
        if not identifiers:
            return vals

        metadata = self._get_all_additional_identifiers_metadata()
        sa_keys = [k for k in identifiers if 'SA' in (metadata.get(k, {}).get('countries') or [])]
        if len(sa_keys) > 1:
            raise ValidationError(self.env._("Only one Saudi Arabia identifier can be set at a time."))

        return vals
