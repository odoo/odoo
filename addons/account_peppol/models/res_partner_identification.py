from odoo import fields, models
from odoo.addons.account.models.res_partner_identification import ODOO_IDENTIFIERS
from odoo.exceptions import UserError


class ResPartnerIdentification(models.Model):
    _inherit = 'res.partner.identification'

    is_on_odoo_peppol = fields.Boolean()
    is_on_peppol = fields.Boolean()

    def _is_peppol_registrable(self):
        self.ensure_one()
        return ODOO_IDENTIFIERS[self.code].get('peppol-registrable', False)

    def _get_peppol_codes_by_country(self, country_code, include_international=False):
        codes = self._get_codes_by_country(country_code, include_international=include_international)
        return codes.filter(lambda code: codes[code].get('peppol-registrable', False))

    def write(self, vals):
        if self.is_on_odoo_peppol and 'identifier' in vals:
            raise UserError(self.env._("You can't change the identification as it's registered on Peppol. "
                                       "Please deregister first."))
        super().write(vals)
