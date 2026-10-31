from odoo import api, models


RGS_TAG_XMLID_PREFIX = 'l10n_nl_account_tag_rgs_'


class AccountAccount(models.Model):
    _inherit = 'account.account'

    @api.model
    def _l10n_nl_apply_default_rgs_tags(self, company, replace_existing_rgs_tags=False):
        """Give the accounts generated per journal (bank, cash) and the liquidity transfer account
        of a Dutch company their RGS tag.

        An RGS tag already on the account is kept as the user's choice, unless `replace_existing_rgs_tags`
        is set, for the transfer account only: used on a just-created transfer account, which only carries the RGS tag of its closest
        preceding template account."""
        journals = self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(company),
            ('type', 'in', ('bank', 'cash')),
        ])

        accounts_by_code = {
            'BLimBanRba': journals.filtered(lambda j: j.type == 'bank').default_account_id,
            'BLimKasKas': journals.filtered(lambda j: j.type == 'cash').default_account_id,
            'BLimKruSto': company.transfer_account_id,
        }

        rgs_tag_ids = set(self.env['ir.model.data'].search([
            ('module', '=', 'l10n_nl'),
            ('model', '=', 'account.account.tag'),
            ('name', '=like', f'{RGS_TAG_XMLID_PREFIX}%'),
        ]).mapped('res_id'))

        for code, accounts in accounts_by_code.items():
            tag = self.env.ref(f'l10n_nl.{RGS_TAG_XMLID_PREFIX}{code}')
            for account in accounts:
                current_rgs_tags = account.tag_ids.filtered(lambda t: t.id in rgs_tag_ids)
                if replace_existing_rgs_tags and code == 'BLimKruSto':
                    account.tag_ids = account.tag_ids - current_rgs_tags + tag
                elif not current_rgs_tags:
                    account.tag_ids += tag
