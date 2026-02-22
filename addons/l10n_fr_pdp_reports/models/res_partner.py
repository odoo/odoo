from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def write(self, vals):
        """Reset open PDP flows when partner VAT/country changes."""
        tracked_keys = {'vat', 'country_id', 'property_account_position_id'}
        res = super().write(vals)
        if tracked_keys.intersection(vals):
            open_states = {'draft', 'building', 'ready', 'error'}
            moves = self.env['account.move'].search([
                ('state', '=', 'posted'),
                ('move_type', 'in', self.env['account.move'].get_sale_types(include_receipts=True)),
                ('commercial_partner_id', 'in', self.commercial_partner_id.ids),
            ])
            if flows := moves.mapped('l10n_fr_pdp_flow_ids').filtered(lambda f: f.state in open_states):
                flows._mark_as_outdated()
        return res
