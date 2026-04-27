from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_gt_edi_service_provider = fields.Selection(related='company_id.l10n_gt_edi_service_provider', readonly=False)
    l10n_gt_edi_ws_prefix = fields.Char(related='company_id.l10n_gt_edi_ws_prefix', readonly=False)
    l10n_gt_edi_infile_token = fields.Char(related='company_id.l10n_gt_edi_infile_token', readonly=False)
    l10n_gt_edi_infile_key = fields.Char(related='company_id.l10n_gt_edi_infile_key', readonly=False)
    l10n_gt_edi_is_root_company = fields.Boolean(compute='_compute_l10n_gt_edi_is_root_company')

    @api.depends('company_id')
    def _compute_l10n_gt_edi_is_root_company(self):
        for setting in self:
            setting.l10n_gt_edi_is_root_company = not setting.company_id.parent_id
