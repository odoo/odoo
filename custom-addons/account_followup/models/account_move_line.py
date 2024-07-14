# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.tools import Query, SQL


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    followup_line_id = fields.Many2one('account_followup.followup.line', 'Follow-up Level', copy=False)
    last_followup_date = fields.Date('Latest Follow-up', index=True, copy=False)  # TODO remove in master
    next_action_date = fields.Date('Next Action Date',  # TODO remove in master
                                   help="Date where the next action should be taken for a receivable item. Usually, "
                                        "automatically set when sending reminders through the customer statement.")
    invoice_origin = fields.Char(related='move_id.invoice_origin')

    def _read_group_groupby(self, groupby_spec: str, query: Query) -> tuple[SQL, list[str]]:
        if groupby_spec != 'followup_overdue':
            return super()._read_group_groupby(groupby_spec, query)
        return SQL(
            """COALESCE(%s, %s) < %s""",
            self._field_to_sql(self._table, 'date_maturity', query),
            self._field_to_sql(self._table, 'date', query),
            fields.Date.context_today(self),
        ), ['date_maturity', 'date']

    def _read_group_empty_value(self, spec):
        if spec != 'followup_overdue':
            return super()._read_group_empty_value(spec)
        return False

    def _read_group_postprocess_groupby(self, groupby_spec, raw_values):
        if groupby_spec != 'followup_overdue':
            return super()._read_group_postprocess_groupby(groupby_spec, raw_values)
        return ((value or False) for value in raw_values)
