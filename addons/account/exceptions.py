from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date
from odoo import fields, _


class ImbalanceMoveValidationError(ValidationError):
    def __init__(self, records):
        self.imbalance_amounts = [sum(rec.line_ids.mapped('balance')) for rec in records]
        super().__init__(_(
            "Cannot create unbalanced journal entry. Ids: %s\n"
            "Differences debit - credit: %s",
            records,
            self.imbalance_amounts,
        ), records)


class UniqueSequenceValidationError(ValidationError):
    def __init__(self, records):
        self.duplicated_names = records.mapped('name')
        super().__init__(_(
            "Posted journal entry must have an unique sequence number per company.\n"
            "Problematic numbers: %s\n",
            ", ".join(self.duplicated_names)
        ), records)


class UniqueReferenceValidationError(ValidationError):
    def __init__(self, records):
        super().__init__(_(
            "Duplicated vendor reference detected. "
            "You probably encoded twice the same vendor bill/credit note:\n%s",
            "\n".join(records.mapped(lambda m: "%(partner)s - %(ref)s - %(date)s" % {
                'ref': m.ref,
                'partner': m.partner_id.display_name,
                'date': format_date(records.env, m.date),
            }))
        ), records)
