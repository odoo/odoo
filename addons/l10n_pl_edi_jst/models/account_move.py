import re

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_pl_edi_get_xml_values(self):
        """Prepares a dictionary of values to be passed to the QWeb template."""
        self.ensure_one()
        xml_values = super()._l10n_pl_edi_get_xml_values()

        def get_address(partner):
            return re.sub(r'\n+', r' ', partner._display_address(True))

        if (buyer := self.commercial_partner_id.l10n_pl_parent_lgu):
            xml_values.update({
                'buyer': buyer,
                'buyer_address': get_address(buyer),
                'jst_subordinate': self.commercial_partner_id,
                'jst_subordinate_address': get_address(self.commercial_partner_id),
            })
        else:
            xml_values.update({
                'jst_subordinate': None,
                'jst_subordinate_address': None,
            })

        return xml_values
