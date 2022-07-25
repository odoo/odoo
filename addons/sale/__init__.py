# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from . import report
from . import wizard
from . import populate

from odoo.api import Environment, SUPERUSER_ID


def _synchronize_cron(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {'active_test': False})
    send_invoice_cron = env.ref('sale.send_invoice_cron', raise_if_not_found=False)
    if send_invoice_cron:
        config = env['ir.config_parameter'].get_param('sale.automatic_invoice', False)
        send_invoice_cron.active = bool(config)
