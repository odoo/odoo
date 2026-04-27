from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # EDI Environment fields

    def _l10n_uy_edi_get_doc_type(self):
        """ Return UY code that identifies the UY identification type of the given partner
        If foreign partner from Mercosur return DNI """
        self.ensure_one()
        id_type = self.l10n_latam_identification_type_id

        # DNI Mercosur: Argentina, Brazil, Chile y Paraguay
        if id_type == self.env.ref("l10n_latam_base.it_fid") and self.country_id.code in ["AR", "BR", "CL", "PA"]:
            id_type = self.env.ref("l10n_uy.it_dni")  # Foreign ID / DNI

        return int(id_type.l10n_uy_dgi_code)

    def _l10n_uy_edi_get_fiscal_address(self):
        res = [self[fieldname] for fieldname in ["street", "street2"] if self[fieldname]]
        return " ".join(res)[:70]
