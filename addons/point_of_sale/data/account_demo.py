import logging
import time
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, Command
from odoo.tools.misc import file_open, formatLang
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _get_demo_exception_product_variant_xml_ids(self):
        """ Override """
        return super()._get_demo_exception_product_variant_xml_ids() + [
            'point_of_sale.product_product_tip', 'point_of_sale.wall_shelf',
            'point_of_sale.product_t_shirt_pants', 'point_of_sale.small_shelf'
        ]
