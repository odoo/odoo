from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    routing_scheme = fields.Selection(related='partner_id.routing_scheme', readonly=False)
    routing_endpoint = fields.Char(related='partner_id.routing_endpoint', readonly=False)
    routing_identifier = fields.Char(related='partner_id.routing_identifier', readonly=False)
    routing_identifier_override = fields.Char(related='partner_id.routing_identifier_override', readonly=False)

    def _get_l10n_de_stnr(self):
        """ The Steuernummer (BT-32) of a DE company, or False. """
        self.ensure_one()
        # l10n_de is not a dependency: use item access since the field may not exist.
        if self.country_code == 'DE' and 'l10n_de_stnr' in self._fields:
            return self['l10n_de_stnr']
        return False
