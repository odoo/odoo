# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.http import request

from odoo.addons.account.controllers.portal import PortalAccount


class PortalAccountMy(PortalAccount):

    def _prepare_my_account_rendering_values(self, *args, **kwargs):
        # EXTENDS 'portal'
        rendering_values = super()._prepare_my_account_rendering_values(*args, **kwargs)
        rendering_values.update({
            'l10n_my_identification_types': dict(rendering_values['partner_sudo']._fields['l10n_my_identification_type'].selection),
            'l10n_my_edi_industrial_classifications': request.env['l10n_my_edi.industry_classification'].sudo().search([]),
        })
        return rendering_values
