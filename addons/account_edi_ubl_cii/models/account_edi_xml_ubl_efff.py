# -*- coding: utf-8 -*-

from odoo import models

import re


class AccountEdiXmlUBLEFFF(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_20"
    _name = 'account.edi.xml.ubl_efff'
    _description = "E-FFF (BE)"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        # official naming convention
        vat = invoice.company_id.partner_id.commercial_partner_id.vat
        return 'efff_%s%s%s.xml' % (vat or '', '_' if vat else '', re.sub(r'[\W_]', '', invoice.name))

    def _export_invoice_ecosio_schematrons(self):
        return None
