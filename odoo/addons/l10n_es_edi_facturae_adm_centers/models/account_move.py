from odoo import models
from odoo.addons.l10n_es_edi_facturae.models.account_move import COUNTRY_CODE_MAP, PHONE_CLEAN_TABLE


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_es_edi_facturae_get_administrative_centers(self, partner):
        self.ensure_one()
        administrative_centers = []
        for ac in partner.child_ids.filtered(lambda p: p.type == 'facturae_ac'):
            ac_template = {
                'center_code': ac.l10n_es_edi_facturae_ac_center_code,
                'name': ac.name,
                'partner': ac,
                'partner_country_code': COUNTRY_CODE_MAP[ac.country_code],
                'partner_phone': ac.phone.translate(PHONE_CLEAN_TABLE) if ac.phone else False,
                'physical_gln': ac.l10n_es_edi_facturae_ac_physical_gln,
                'logical_operational_point': ac.l10n_es_edi_facturae_ac_logical_operational_point,
            }
            # An administrative center can have multiple roles, each of which should be reported separately.
            for role in ac.l10n_es_edi_facturae_ac_role_type_ids or [self.env['l10n_es_edi_facturae_adm_centers.ac_role_type']]:
                administrative_centers.append({
                    **ac_template,
                    'role_type_code': role.code,
                })
        return administrative_centers

    def _l10n_es_edi_facturae_export_facturae(self):
        template_values, signature_values = super()._l10n_es_edi_facturae_export_facturae()
        template_values['self_party_administrative_centers'] = self._l10n_es_edi_facturae_get_administrative_centers(
            template_values.get('self_party')
        )
        template_values['other_party_administrative_centers'] = self._l10n_es_edi_facturae_get_administrative_centers(
            template_values.get('other_party')
        )
        return template_values, signature_values
