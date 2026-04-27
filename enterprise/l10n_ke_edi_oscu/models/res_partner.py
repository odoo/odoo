# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ke_branch_code = fields.Char('eTIMS Branch Code', default='00')

    def _l10n_ke_oscu_partner_content(self):
        """Returns a dict with the commonly required fields on partner for requests to the OSCU """
        self.ensure_one()
        return {
            'custNo':  self.id,                              # Customer Number
            'custTin': self.vat,                             # Customer PIN
            'custNm':  self.name,                            # Customer Name
            'adrs':    self.contact_address_inline or None,  # Address
            'email':   self.email or None,                   # Email
            'useYn':   'Y' if self.active else 'N',          # Used (Y/N)
        }

    def action_l10n_ke_oscu_register_bhf_customer(self):
        """Save the partner information on the OSCU."""
        for partner in self:
            content = {
                **self.env.company._l10n_ke_get_user_dict(partner.create_uid, partner.write_uid),
                **partner._l10n_ke_oscu_partner_content()    # Partner details
            }
            company = partner.company_id or self.env.company
            error, _data, _dummy = company._l10n_ke_call_etims('saveBhfCustomer', content)
            if error:
                raise UserError(f"[{error['code']}] {error['message']}")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'message': _("Partner successfully registered"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_l10n_ke_oscu_fetch_bhf_customer(self):
        """ Fetch saved customer information from eTIMS.
            We don't use this method but must have it to demonstrate we are able to call their API.
        """
        company = self.company_id or self.env.company
        error, data, _dummy = company._l10n_ke_call_etims('selectCustomer', {'custmTin': self.vat})
        raise UserError(data or error)
