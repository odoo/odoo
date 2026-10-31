# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_se_sru_type = fields.Selection(related='company_id.l10n_se_sru_type', readonly=False)
    l10n_se_f_tax_approved = fields.Boolean(related='company_id.l10n_se_f_tax_approved', readonly=False)

    def action_l10n_se_load_sru_mapping(self):
        """Replace the company's SRU mappings with the bundled template for the selected form."""
        self.ensure_one()
        self.company_id.l10n_se_sru_type = self.l10n_se_sru_type
        self.env['l10n_se.sru.mapping'].with_company(self.company_id).load_template_from_file(self.l10n_se_sru_type)
        action = self.env['ir.actions.act_window']._for_xml_id('l10n_se.l10n_se_sru_mapping_action')
        action['domain'] = [('company_id', '=', self.company_id.id), ('sru_type', '=', self.l10n_se_sru_type)]
        return action
