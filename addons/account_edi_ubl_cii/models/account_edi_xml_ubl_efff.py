# -*- coding: utf-8 -*-
from odoo.addons import account_edi_ubl_cii

from odoo import models

import re


class AccountEdiXmlUblEfff(models.AbstractModel, account_edi_ubl_cii.AccountEdiXmlUbl20):
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
