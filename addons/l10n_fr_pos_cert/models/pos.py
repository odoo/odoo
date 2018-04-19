# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta
import pytz

from odoo import models, api, fields
from odoo.fields import Datetime
from odoo.tools.translate import _
from odoo.exceptions import UserError


def ctx_tz(record, field):
    res_lang = None
    ctx = record._context
    tz_name = pytz.timezone(ctx.get('tz') or record.env.user.tz)
    timestamp = Datetime.from_string(record[field])
    if ctx.get('lang'):
        res_lang = record.env['res.lang'].search([('code', '=', ctx['lang'])], limit=1)
    if res_lang:
        timestamp = pytz.utc.localize(timestamp, is_dst=False)
        return datetime.strftime(timestamp.astimezone(tz_name), res_lang.date_format + ' ' + res_lang.time_format)
    return Datetime.context_timestamp(record, timestamp)


class pos_config(models.Model):
    _inherit = 'pos.config'

    @api.multi
    def open_ui(self):
        for config in self.filtered(lambda c: c.company_id._is_accounting_unalterable()):
            if config.current_session_id:
                config.current_session_id._check_session_timing()
        return super(pos_config, self).open_ui()


class pos_session(models.Model):
    _inherit = 'pos.session'

    @api.multi
    def _check_session_timing(self):
        self.ensure_one()
        date_today = datetime.utcnow()
        session_start = Datetime.from_string(self.start_at)
        if not date_today - timedelta(hours=24) <= session_start:
            raise UserError(_("This session has been opened another day. To comply with the French law, you should close sessions on a daily basis. Please close session %s and open a new one.") % self.name)
        return True

    @api.multi
    def open_frontend_cb(self):
        for session in self.filtered(lambda s: s.config_id.company_id._is_accounting_unalterable()):
            session._check_session_timing()
        return super(pos_session, self).open_frontend_cb()


class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = ['pos.order', 'unalterable.hash.mixin']

    @api.model
    def _get_unalterable_fields(self):
        # Override
        return ['date_order', 'user_id', 'lines', 'statement_ids', 'pricelist_id', 'partner_id', 'session_id',
                'pos_reference', 'sale_journal', 'fiscal_position_id']

    @api.multi
    def _is_object_unalterable(self):
        # Override
        return self.company_id._is_accounting_unalterable() and self.state in ['paid', 'done', 'invoiced']


class PosOrderLine(models.Model):
    _name = 'pos.order.line'
    _inherit = ['pos.order.line', 'unalterable.fields.mixin']

    @api.model
    def _get_unalterable_fields(self):
        # Override
        return ['notice', 'product_id', 'qty', 'price_unit', 'discount', 'tax_ids', 'tax_ids_after_fiscal_position']

    @api.multi
    def _is_object_unalterable(self):
        # Override
        return self.order_id._is_object_unalterable()
