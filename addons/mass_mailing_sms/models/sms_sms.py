# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools.mail import text_url_replace, TEXT_URL_REGEX


class SmsSms(models.Model):
    _inherit = 'sms.sms'

    mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing')
    # Linking to another field than the comodel id allows to use the ORM to create
    # "linked" records (see _prepare_mass_sms_values) without adding a foreign key.
    # See commit message for why this is useful.
    mailing_trace_ids = fields.One2many('mailing.trace', string='Statistics', compute='_compute_trace_ids', search='_search_trace_ids', compute_sudo=True)
    mailing_trace_existing_ids = fields.One2many('mailing.trace', 'sms_id', string='Statistics (existing)')

    @api.depends('mailing_trace_existing_ids.sms_id_int')
    def _compute_trace_ids(self):
        sms_traces = dict(self.env['mailing.trace']._read_group([('sms_id_int', 'in', self.ids)], ['sms_id_int'], ['id:array_agg']))
        for sms in self:
            sms.mailing_trace_ids = sms_traces.get(sms.id) or []

    def _search_trace_ids(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        query = self.env['mailing.trace']._search(Domain('id', operator, value) & Domain('sms_id_int', '!=', False))
        domain = Domain('id', 'in', query.subselect(query.table.sms_id_int))
        if operator == 'in' and False in value:  # relation may be falsy
            query = self.env['mailing.trace']._search([])
            domain |= Domain('id', 'not in', query.subselect(query.table.sms_id_int))
        return domain

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (traces := vals.pop('mailing_trace_ids', None)) is not None:
                vals['mailing_trace_existing_ids'] = traces
        return super().create(vals_list)

    def _update_body_short_links(self):
        """ Override to tweak shortened URLs by adding statistics ids, allowing to
        find customer back once clicked. """
        res = dict.fromkeys(self.ids, False)
        for sms in self:
            if not sms.mailing_id or not sms.body:
                res[sms.id] = sms.body
                continue

            body = sms.body
            for url in set(re.findall(TEXT_URL_REGEX, body)):
                if url.startswith(sms.get_base_url() + '/r/'):
                    body = text_url_replace(url, url + f'/s/{sms.id}', body)
            res[sms.id] = body
        return res
