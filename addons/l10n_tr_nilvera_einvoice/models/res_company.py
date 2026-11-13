from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_tr_nilvera_filter_missing_registry_codes(self):
        """ Return the TR companies whose contact has neither a MERSISNO nor a TICARETSICILNO code.
        An E-Archive company that does not need them is exempted by the REGISTRY EXEMPT tag.
        """
        mandatory_categories = self.env['res.partner.category']._get_l10n_tr_official_mandatory_categories()
        registry_exempt = self.env.ref('l10n_tr_nilvera_einvoice.res_partner_category_registry_exempt', raise_if_not_found=False)

        def is_missing_codes(company):
            if company.country_code != 'TR':
                return False

            partner = company.partner_id
            if registry_exempt and partner.l10n_tr_nilvera_customer_status == 'earchive' and registry_exempt in partner.category_id:
                return False
            return not (mandatory_categories & partner.category_id.parent_id)

        return self.filtered(is_missing_codes)
