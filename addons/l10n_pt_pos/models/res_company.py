from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pt_pos_secure_sequence_id = fields.Many2one('ir.sequence')

    def _l10n_pt_create_pos_secure_sequence(self, companies):
        for company in companies.filtered(lambda c: c.country_id.code == 'PT'):
            self.env['blockchain.mixin']._create_blockchain_secure_sequence(company, "l10n_pt_pos_secure_sequence_id", company.id)

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        # When creating a new portuguese company, create the securisation sequence as well
        self._l10n_pt_create_pos_secure_sequence(companies)
        return companies

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        # If country changed to PT, create the securisation sequence
        self._l10n_pt_create_pos_secure_sequence(self)
        return res

    def _action_check_l10n_pt_pos_blockchain_integrity(self):
        return self.env.ref('l10n_pt_pos.action_report_l10n_pt_pos_blockchain_integrity').report_action(self.id)
