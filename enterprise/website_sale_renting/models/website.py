# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from odoo import models, fields
from odoo.osv import expression
from odoo.http import request


class Website(models.Model):
    _inherit = 'website'

    tz = fields.Selection(
        selection='_tz_get',
        required=True,
        default=lambda self: self.env.user.tz or 'UTC',
        string="Timezone",
        help="Select your website timezone here."
    )

    def _tz_get(self):
        return [
            (tz, f'{tz} {self._get_utc_offset(tz)}')
            for tz in sorted(
                pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_'
            )
        ]

    def _product_domain(self):
        return expression.OR([[('rent_ok', '=', True)], super()._product_domain()])

    def _is_customer_in_the_same_timezone(self):  # TODO VCR this method should be renamed in master
        """ Return whether the customer is on the same timezone as the website or not.

        Compare the timezone offset between the website and the customer's browser.

        :return: Whether the customer is on the same timezone as the website or not.
        :rtype: bool
        """
        now = fields.datetime.now()
        customer_tz = request.cookies.get('tz') if request else None

        return (
            pytz.timezone(self.tz).localize(now).utcoffset()
            != pytz.timezone(customer_tz or 'UTC').localize(now).utcoffset()
        )

    def _get_utc_offset(self, tz):
        """ Return the offset between UTC and the provided timezone
        :return: (UTC ±HH:MM)
        :rtype: string
        """
        # strftime('%z') return the UTC offset in this form: ±HHMM[SS[.ffffff]]
        utcoffset = pytz.timezone(tz).localize(fields.datetime.now()).strftime('%z')
        return f'(UTC {utcoffset[0]} {utcoffset[1:3]}:{utcoffset[3:5]})'
