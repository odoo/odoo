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