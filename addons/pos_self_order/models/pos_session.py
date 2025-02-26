# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields
from odoo.service.common import exp_version


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model_create_multi
    def create(self, vals_list):
        sessions = super(PosSession, self).create(vals_list)
        sessions = self._create_pos_self_sessions_sequence(sessions)
        return sessions

    @api.model
    def _create_pos_self_sessions_sequence(self, sessions):
        company_id = self.env.company.id

        for session in sessions:
            session.env['ir.sequence'].sudo().create({
                'name': _("PoS Order by Session"),
                'padding': 4,
                'code': f'pos.order_{session.id}',
                'number_next': 1,
                'number_increment': 1,
                'company_id': company_id,
            })

        return sessions

    @api.model
    def _load_pos_self_data_domain(self, data):
        return [('config_id', '=', data['pos.config']['data'][0]['id']), ('state', '=', 'opened')]

    def _load_pos_self_data(self, data):
        config_id = data['pos.config']['data'][0]['id']
        domains = self._load_pos_self_data_domain(data)
        fields = self._load_pos_data_fields(config_id)
        data = self.search_read(domains, fields, load=False, limit=1)
        if len(data) > 0:
            data[0]['_base_url'] = self.get_base_url()
            data[0]['_partner_commercial_fields'] = self.env['res.partner']._commercial_fields()
            data[0]['_server_version'] = exp_version()
            data[0]['_has_cash_move_perm'] = self.env.user.has_group('account.group_account_invoice')
            data[0]['_has_available_products'] = self._pos_has_valid_product()
            data[0]['_pos_special_products_ids'] = self.env['pos.config']._get_special_products().ids
            data[0]['_self_ordering'] = (
                self.env["pos.config"]
                .sudo()
                .search_count(
                    [
                        *self.env["pos.config"]._check_company_domain(self.env.company),
                        '|', ("self_ordering_mode", "=", "kiosk"),
                        ("self_ordering_mode", "=", "mobile"),
                    ],
                    limit=1,
                )
                > 0
            )
        return {
            'data': data,
            'fields': fields
        }
