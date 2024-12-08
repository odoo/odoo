# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.l10n_latam_base.controllers.portal import L10nLatamBasePortalAccount


class L10nUYPortalAccount(L10nLatamBasePortalAccount):

    def _l10n_get_default_identification_type_id(self):
        return (
            (self.env.company.country_code == 'UY' and request.env.ref('l10n_uy.it_ci'))
            or super()._l10n_get_default_identification_type_id()
        )
