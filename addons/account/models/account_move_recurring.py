from odoo import models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_next_recurring_date(self, date, date_origin):
        """The accounting date of the occurrence following `date`.

        Anchored on the series origin rather than stepped off `date`, so a move
        whose date was edited by hand does not shift every later occurrence:
        the count of whole periods since the origin decides, and the answer is
        always back on the series' own grid.
        """
        self.check_singleton()
        if self.repeat_unit == "year":
            elapsed = date.year - date_origin.year
        else:
            elapsed = (date.year - date_origin.year) * 12 + (
                date.month - date_origin.month
            )
        periods = elapsed // self.repeat_interval + 1
        return date_origin + self._get_recurrence_delta() * periods

    @_debug.perf.timed
    def _copy_recurring_entries(self):
        moves_next_dates = []
        for record in self:
            record.auto_post_origin_id = record.auto_post_origin_id or record
            next_date = record._get_next_recurring_date(
                record.date, record.auto_post_origin_id.date
            )
            if not record.repeat_until or next_date <= record.repeat_until:
                moves_next_dates.append((record, next_date))
        if not moves_next_dates:
            return

        # A reset-and-repost, or the cron, reaches a period whose recurrence already
        # exists; copying again would post that period twice.
        self.flush_model(["date", "auto_post_origin_id"])
        values = SQL(", ").join(
            SQL(
                "(%s::int4, %s::int4, %s::date)",
                move.id,
                move.auto_post_origin_id.id,
                next_date,
            )
            for move, next_date in moves_next_dates
        )
        recurrence_exists = dict(
            self.env.execute_query(
                SQL(
                    """
                       SELECT current_move.id,
                              EXISTS (
                                  SELECT 1
                                    FROM account_move AS next_move
                                   WHERE next_move.auto_post_origin_id = current_move.auto_post_origin_id
                                     AND next_move.date = current_move.next_date
                              )
                         FROM (VALUES %(values)s) AS current_move(id, auto_post_origin_id, next_date)
                    """,
                    values=values,
                )
            )
        )
        for record, next_date in moves_next_dates:
            if recurrence_exists.get(record.id):
                _debug.logic(
                    "recurrence_already_exists_not_copied",
                    move=record,
                    next_date=next_date,
                )
                continue
            _debug.pipeline(
                "copying_recurring_entry",
                move=record,
                next_date=next_date,
                auto_post=record.auto_post,
            )
            record.copy(
                default=record._get_fields_to_copy_recurring_entries(
                    {"date": next_date}
                )
            )

    def _get_fields_to_copy_recurring_entries(self, values):
        values.update(
            {
                "auto_post": self.auto_post,
                "repeat_interval": self.repeat_interval,
                "repeat_unit": self.repeat_unit,
                "repeat_type": self.repeat_type,
                "repeat_until": self.repeat_until,
                "auto_post_origin_id": self.auto_post_origin_id.id,
                "invoice_user_id": self.invoice_user_id.id,
            }
        )
        if self.invoice_date and self.auto_post_origin_id.invoice_date:
            values.update(
                {
                    "invoice_date": self._get_next_recurring_date(
                        self.invoice_date,
                        self.auto_post_origin_id.invoice_date,
                    )
                }
            )
        if not self.invoice_payment_term_id and self.invoice_date_due:
            values.update(
                {
                    "invoice_date_due": values["date"]
                    + (self.invoice_date_due - self.date)
                }
            )
        _debug.logic(
            "recurring_dates_carried",
            move=self,
            invoice_date="invoice_date" in values,
            invoice_date_due="invoice_date_due" in values,
        )
        return values
