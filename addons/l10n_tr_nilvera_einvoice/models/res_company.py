from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_tr_nilvera_filter_missing_registry_codes(self):
        """ Return the TR E-Invoice companies whose contact has neither a MERSISNO nor a TICARETSICILNO code.
        E-Archive companies are not checked: only some of them need these codes.
        """
        mandatory_categories = self.env['res.partner.category']._get_l10n_tr_official_mandatory_categories()
        return self.filtered(lambda c: c.country_code == 'TR' and c.partner_id.l10n_tr_nilvera_customer_status == 'einvoice' and not (mandatory_categories & c.partner_id.category_id.parent_id))
