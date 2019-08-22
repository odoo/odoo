# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields, _
from odoo.exceptions import UserError
from datetime import datetime
from odoo.fields import Datetime
import pytz


def ctx_tz(record, field):
    res_lang = None
    ctx = record._context
    tz_name = pytz.timezone(ctx.get('tz') or record.env.user.tz)
    timestamp = Datetime.from_string(record[field])
    if ctx.get('lang'):
        res_lang = record.env['res.lang']._lang_get(ctx['lang'])
    if res_lang:
        timestamp = pytz.utc.localize(timestamp, is_dst=False)
        return datetime.strftime(timestamp.astimezone(tz_name), res_lang.date_format + ' ' + res_lang.time_format)
    return Datetime.context_timestamp(record, timestamp)


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pos_cert_sequence_id = fields.Many2one('ir.sequence')

    @api.model
    def create(self, vals):
        company = super(ResCompany, self).create(vals)
        #when creating a new french company, create the securisation sequence as well
        if company._is_accounting_unalterable():
            sequence_fields = ['l10n_fr_pos_cert_sequence_id']
            company._create_secure_sequence(sequence_fields)
        return company

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        #if country changed to fr, create the securisation sequence
        for company in self:
            if company._is_accounting_unalterable():
                sequence_fields = ['l10n_fr_pos_cert_sequence_id']
                company._create_secure_sequence(sequence_fields)
        return res
