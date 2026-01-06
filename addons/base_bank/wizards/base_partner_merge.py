from odoo import api, models


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    @api.model
    def _merge_bank_accounts(self, src_partners, dst_partner):
        """ Merge bank accounts of src_partners into dst_partner.
            :param src_partners: merge source res.partner recordset (does not include destination one)
            :param dst_partner: record of destination res.partner
        """
        all_src_accounts = src_partners.bank_ids

        for src_account in all_src_accounts:
            duplicate_account = dst_partner.bank_ids.filtered(lambda a: a.sanitized_account_number == src_account.sanitized_account_number)
            if duplicate_account:
                self._update_foreign_keys_generic('res.partner.bank', src_account, duplicate_account)
                self._update_reference_fields_generic('res.partner.bank', src_account, duplicate_account)
                src_account.sudo().unlink()
            else:
                src_account.sudo().write({'partner_id': dst_partner.id})

    def _merge_partners(self, src_partners, dst_partner):
        # Merge bank accounts before merging partners
        self._merge_bank_accounts(src_partners, dst_partner)

        super()._merge_partners(src_partners, dst_partner)
