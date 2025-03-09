from odoo import _, api, models
from odoo.addons.base.models.res_partner import ADDRESS_FIELDS


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    @api.onchange('name', 'vat', *ADDRESS_FIELDS)
    def _onchange_partner_with_posted_moves(self):
        if self.id.origin:
            posted_jo_moves_count = self.env['account.move'].search_count([
                ('partner_id', '=', self.id.origin),
                ('country_code', '=', 'JO'),
                ('state', '=', 'posted'),
            ], limit=1)
            if posted_jo_moves_count:
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _("Be careful when changing the details for partners with posted moves as it can cause a mismatch in your ISTD tax return and issues during an ISTD audit. Alternatively, create a new related contact or address."),
                    }
                }
