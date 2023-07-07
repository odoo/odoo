# -*- coding: utf-8 -*-

from odoo import models


class AccountEdiXmlUBLRO(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = 'account.edi.xml.ubl_ro'
    _description = "SI-UBL 2.0 (NLCIUS)"

    def _export_invoice_filename(self, invoice):
        # TODO: test this
        # return f"{invoice.name.replace('/', '_')}_cius_ro.xml"
        return f"{invoice.name.replace('/', '_')}_cius_rooo.xml"
