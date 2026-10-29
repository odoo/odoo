# Copyright 2023 Tecnativa - Pedro M. Baeza
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models


class Base(models.AbstractModel):
    _inherit = "base"

    def _check_company(self, fnames=None):
        """Inject as context the company of the record that is going to be compared
        for being taking into account when computing the company of many2one's
        relations that links with our multi-company models.

        We have to serialize the call to super, but it doesn't matter in terms of
        performance, as super also makes a for loop in the records.
        """
        for record in self:
            company_source_id = False
            if record._name == "res.company":
                company_source_id = record.id
            elif "company_id" in record._fields:
                company_source_id = record.company_id.id
            record = record.with_context(_check_company_source_id=company_source_id)
            super(Base, record)._check_company(fnames=fnames)
        return
