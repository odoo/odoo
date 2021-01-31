# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
import logging
import pytz
import odoo
from odoo import api, fields, models, tools, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)

class Datetime(Field):
    _inherit = 'datetime'

    @staticmethod
    def context_to_utc_timestamp(record, timestamp):
        """Returns the given timestamp converted from the client's timezone to UTC.
           This method is *not* meant for use as a _defaults initializer,
           because datetime fields are automatically converted upon
           display on client side. For _defaults :meth:`fields.datetime.now`
           should be used instead.

           :param datetime timestamp: naive datetime value (expressed in user time zone)
                                      to be converted to UTC
           :param dict context: the 'tz' key in the context should give the
                                name of the User/Client timezone (otherwise
                                UTC is used)
           :rtype: datetime
           :return: timestamp converted to timezone-aware datetime in UTC
                    timezone
        """
        assert isinstance(timestamp, datetime), 'Datetime instance expected'
        tz_name = record._context.get('tz') or record.env.user.tz
        utc_timestamp = pytz.utc.localize(timestamp, is_dst=False)  # UTC = no DST
        if tz_name:
            try:
                utc = pytz.timezone('UTC')
                context_tz = pytz.timezone(tz_name)
                localized_timestamp = context_tz.localize(timestamp, is_dst=False) # UTC = no DST
                utc_timestamp = localized_timestamp.astimezone(utc)

                context_tz = pytz.timezone(tz_name)
                return utc_timestamp.astimezone(context_tz)
            except Exception:
                _logger.debug("failed to compute context/client-specific timestamp, "
                              "using the UTC value",
                              exc_info=True)
        return utc_timestamp or timestamp
