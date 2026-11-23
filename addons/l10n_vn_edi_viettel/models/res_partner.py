# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

VN_ADDITIONAL_IDENTIFIERS_METADATA = {
    'VN_CCCD': {
        'label': _lt('CCCD'),
        'help': _lt('Vietnamese citizen identity card number (Căn cước công dân).'),
        'placeholder': '001099012345',
        'category': 'CN',
        'countries': ['VN'],
    },
    'VN_BUDGET_CODE': {
        'label': _lt('Budget Unit Code'),
        'help': _lt('Budget unit code (Mã quan hệ ngân sách) of a buyer paid from the state budget.'),
        'placeholder': '1234567',
        'category': 'EN',
        'countries': ['VN'],
    },
}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('vn_sinvoice', 'Vietnam (SInvoice)')])

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **VN_ADDITIONAL_IDENTIFIERS_METADATA}

    def _compute_available_additional_identifiers_metadata(self):
        super()._compute_available_additional_identifiers_metadata()
        if self.env.company.country_code != 'VN':
            return
        # Base only offers the passport in a few countries, yet S-Invoice needs it for any foreign buyer.
        passport_metadata = self._lazy_translate_additional_identifiers_metadata(
            self._get_all_additional_identifiers_metadata()['PASSPORT'],
        )
        for partner in self:
            partner.available_additional_identifiers_metadata = {
                **partner.available_additional_identifiers_metadata,
                'PASSPORT': passport_metadata,
            }
