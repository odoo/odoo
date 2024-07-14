# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError

from .product_template import MX_PACKAGING_CATALOG


class Picking(models.Model):
    _inherit = 'stock.picking'

    l10n_mx_edi_customs_no = fields.Char(
        string='Customs Number',
        help='Optional field for entering the customs information in the case '
             'of first-hand sales of imported goods or in the case of foreign trade'
             ' operations with goods or services.\n'
             'The format must be:\n'
             ' - 2 digits of the year of validation followed by two spaces.\n'
             ' - 2 digits of customs clearance followed by two spaces.\n'
             ' - 4 digits of the serial number followed by two spaces.\n'
             ' - 1 digit corresponding to the last digit of the current year, '
             'except in case of a consolidated customs initiated in the previous '
             'year of the original request for a rectification.\n'
             ' - 6 digits of the progressive numbering of the custom.\n'
             'example: 15  48  3009  0001235')

    def _l10n_mx_edi_cfdi_check_external_trade_config(self):
        # EXTENDS 'l10n_mx_edi_stock'
        self.ensure_one()
        errors = []
        if not self.partner_id.zip or not self.partner_id.state_id:
            errors.append(_("A zip code and state are required to generate a delivery guide"))
        return errors

    def _l10n_mx_edi_get_packaging_desc(self, code):
        return dict(MX_PACKAGING_CATALOG).get(code, None)
