# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_th_edi_inet_staging_mode = fields.Boolean(
        string="INET Staging Mode",
        groups='base.group_system',
    )
    l10n_th_edi_inet_api_key = fields.Char(
        string="INET API Key",
        groups='base.group_system',
    )
    l10n_th_edi_inet_authorization_code = fields.Char(
        string="INET Authorization Code",
        groups='base.group_system',
    )
    l10n_th_edi_subdistrict_code = fields.Char(
        string="Sub-district Code",
        help="6-digit TISI code of the company's sub-district (tambon). Its first 4 digits are the district code and "
             "its first 2 digits the province code.",
    )

    def _l10n_th_edi_get_branch_code(self):
        self.ensure_one()
        return self.partner_id._get_additional_identifier('TH_BRANCH_CODE') or '00000'
