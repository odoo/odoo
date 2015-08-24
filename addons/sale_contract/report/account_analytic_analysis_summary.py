# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
import datetime
import logging
import time

from openerp.osv import osv, fields
import openerp.tools
from openerp.tools.translate import _
from openerp.exceptions import UserError

from openerp.addons.decimal_precision import decimal_precision as dp

_logger = logging.getLogger(__name__)
