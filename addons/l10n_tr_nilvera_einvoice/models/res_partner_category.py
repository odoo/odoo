from odoo import _, api, models
from odoo.exceptions import UserError

l10n_tr_official_code_categories = [
    "res_partner_category_hizmetno",
    "res_partner_category_mersisno",
    "res_partner_category_tesisatno",
    "res_partner_category_telefonno",
    "res_partner_category_distributorno",
    "res_partner_category_ticaretsicilno",
    "res_partner_category_tapdkno",
    "res_partner_category_bayino",
    "res_partner_category_aboneno",
    "res_partner_category_sayacno",
    "res_partner_category_epdkno",
    "res_partner_category_subeno",
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

l10n_tr_official_mandatory_code_categories = [
    "res_partner_category_mersisno",
    "res_partner_category_ticaretsicilno",
]


class PartnerCategory(models.Model):
    _inherit = "res.partner.category"

    def _get_categories_from_xml_ids(self, xml_ids_list):
        categories = self.env["res.partner.category"]
        for xml_id in xml_ids_list:
            categories |= self.env.ref(f"l10n_tr_nilvera_einvoice.{xml_id}", raise_if_not_found=False)
        return categories

    def _get_l10n_tr_official_categories(self):
        return self._get_categories_from_xml_ids(l10n_tr_official_code_categories)

    def _get_l10n_tr_official_mandatory_categories(self):
        return self._get_categories_from_xml_ids(l10n_tr_official_mandatory_code_categories)

    @api.ondelete(at_uninstall=False)
    def _unlink_l10n_tr_official_category(self):
        """Prevent the deletion of Nilvera official TR categories"""
        official_categories = self._get_l10n_tr_official_categories()
        if any(rec in official_categories for rec in self):
            raise UserError(_("The Contact Tag(s) cannot be deleted because it is used in Türkiye electronic integrations."))
