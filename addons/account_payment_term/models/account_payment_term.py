from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import date_utils


class AccountPaymentTermLine(models.Model):
    _inherit = "account.payment.term.line"

    delay_type = fields.Selection(
        selection_add=[('days_end_of_month_on_the', 'Days end of month on the')],
        ondelete={'days_end_of_month_on_the': 'set default'}
    )
    display_days_next_month = fields.Boolean(compute='_compute_display_days_next_month')
    days_next_month = fields.Char(
        string='Days on the next month',
        readonly=False,
        store=True,
        default='10',
        size=2,
    )

    @api.constrains('days_next_month')
    def _check_valid_char_value(self):
        for record in self:
            if record.days_next_month.isnumeric():
                if not (0 <= int(record.days_next_month) <= 31):
                    raise ValidationError(_('The days added must be between 0 and 31.'))
            else:
                raise ValidationError(_('The days added must be a number and has to be between 0 and 31.'))

    @api.depends('delay_type')
    def _compute_display_days_next_month(self):
        for record in self:
            record.display_days_next_month = record.delay_type == 'days_end_of_month_on_the'

    def _get_due_date(self, date_ref):
        res = super()._get_due_date(date_ref)

        due_date = fields.Date.from_string(date_ref) or fields.Date.today()
        if self.delay_type == 'days_end_of_month_on_the':
            date_end_of_month = date_utils.end_of(due_date + relativedelta(days=self.nb_days), 'month')

            # Special case handling when the day of the month is 29, 30 or 31 to avoid exceeding the next month's end
            # For instance, with a payment term of 30 days end of month and using the 31st of a month,
            # prevent calculation from moving beyond the end of the next month (e.g., early March instead of end February)
            if self.days_next_month in {'29', '30', '31'}:
                # We get the min of the days the user enter in the payment term and the last day of the next month
                days_next_month = relativedelta(days=min(int(self.days_next_month), (date_end_of_month + relativedelta(month=2)).day))
            else:
                days_next_month = relativedelta(days=int(self.days_next_month))
            return date_end_of_month + days_next_month
        return res
