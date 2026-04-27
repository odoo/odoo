from odoo import models
from odoo.addons.base_iban.models.res_partner_bank import _map_iban_template, normalize_iban


BBAN_PART_MAP = {
    'bank': 'B',  # Bank national code
    'branch': 'S',  # Branch code
    'account': 'C',  # Account number
    'check': 'k',  # Check digits
    'check_other': 'K',  # Other check digits
}


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    def get_iban_part(self, number_kind):
        """ Get part of the iban depending on the mask

            .. code-block:: python

                # template = 'ITkk KBBB BBSS SSSC CCCC CCCC CCC'
                partner.acc_number = 'IT60X0542811101000000123456'
                partner.get_iban_mask('bank') == '05428'

            Returns ``False`` in case of failure
        """
        self.ensure_one()
        mask_char = BBAN_PART_MAP[number_kind.lower()]
        if self.acc_type != 'iban' or not mask_char:
            return False
        iban = normalize_iban(self.acc_number)
        country_code = iban[:2].lower()
        template = _map_iban_template.get(country_code, '').replace(' ', '')
        return template and "".join(c for c, t in zip(iban, template) if t == mask_char)
