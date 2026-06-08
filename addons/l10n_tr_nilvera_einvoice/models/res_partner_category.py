from odoo import _, api, models
from odoo.exceptions import UserError

_LEGACY_L10N_TR_CATEGORY_XML_IDS = [
    "res_partner_category_hizmetno",
    "res_partner_category_tesisatno",
    "res_partner_category_telefonno",
    "res_partner_category_distributorno",
    "res_partner_category_tapdkno",
    "res_partner_category_bayino",
    "res_partner_category_aboneno",
    "res_partner_category_sayacno",
    "res_partner_category_epdkno",
    "res_partner_category_pasaportno",
    "res_partner_category_ureticino",
    "res_partner_category_ciftcino",
    "res_partner_category_imalatcino",
    "res_partner_category_dosyano",
    "res_partner_category_hastano",
    "res_partner_category_musterino",
    "res_partner_category_aracikurumvkn",
    "res_partner_category_aracikurumetiket",
]


class PartnerCategory(models.Model):
    _inherit = "res.partner.category"

    @api.ondelete(at_uninstall=False)
    def _unlink_l10n_tr_official_category(self):
        # Legacy guard: these tag categories exist only in existing users' databases and must
        # not be deleted to preserve audit log integrity.
        legacy_categories = self.env["res.partner.category"]
        for xml_id in _LEGACY_L10N_TR_CATEGORY_XML_IDS:
            legacy_categories |= self.env.ref(f"l10n_tr_nilvera_einvoice.{xml_id}", raise_if_not_found=False)
        if any(rec in legacy_categories for rec in self):
            raise UserError(_("The Contact Tag(s) cannot be deleted because it is used in Türkiye electronic integrations."))
