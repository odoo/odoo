from odoo import models


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"

    def _check_tax_ids_len(self, line):
        return len(line.tax_ids.flatten_taxes_hierarchy().filtered(
            lambda t: t.amount_type not in ('fixed', 'code') and t.ubl_cii_type != 'allowance_charge'
        )) != 1
