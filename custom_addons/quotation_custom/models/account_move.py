import calendar
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from hashlib import sha256
from json import dumps
import logging
#from markupsafe import Markup
import math
import re
from textwrap import shorten

from odoo import api, fields, models, _, Command, SUPERUSER_ID, modules, tools
from odoo.tools.sql import column_exists, create_column
from odoo.addons.account.tools import format_structured_reference_iso
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from odoo.osv import expression
from odoo.tools.misc import clean_context
from odoo.tools import (
    create_index,
    date_utils,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    groupby,
    index_exists,
    OrderedSet,
    SQL,
)
from odoo.tools.mail import email_re, email_split, is_html_empty


_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _build_credit_exception_notification(self, record, current_amount=0.0, exclude_current=False, exclude_amount=0.0):
        """ Build the UserError message that will be displayed in a pop up on the Quotation form.
            if the partner exceeds a credit limit (set on the company or the partner itself).
            :param record:                  The record where the warning will appear (Invoice, Sales Order...).
            :param current_amount (float):  The partner's outstanding credit amount from the current document.
            :param exclude_current (bool):  DEPRECATED in favor of parameter `exclude_amount`:
                                            Whether to exclude `current_amount` from the credit to invoice.
            :param exclude_amount (float):  The amount to subtract from the partner's `credit_to_invoice`.
                                            Consider the warning on a draft invoice created from a sales order.
                                            After confirming the invoice the (partial) amount (on the invoice)
                                            stemming from sales orders will be substracted from the `credit_to_invoice`.
                                            This will reduce the total credit of the partner.
                                            This parameter is used to reflect this amount.
            :return (str):                  The UserError message to be showed.
        """
        warning_message = super()._build_credit_warning_message(record, current_amount, exclude_current, exclude_amount)

        if warning_message:
            raise UserError(warning_message + '\n' + _('You can not confirm this quotation.'))