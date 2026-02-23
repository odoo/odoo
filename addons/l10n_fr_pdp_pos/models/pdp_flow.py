from odoo import _, api, fields, models

class PdpFlow(models.Model):
    _inherit = 'l10n.fr.pdp.reports.flow'

    def _get_sale_move_types(self):
        # if an entry already is a valid flow 10 move, then it's a sale
        return self.env['account.move'].get_sale_types(True) + ['entry']