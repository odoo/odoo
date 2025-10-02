# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data += ['mail.template']
        return data

    @api.model
    def _load_pos_self_data_domain(self, data):
        return [('config_id', '=', data['pos.config'][0]['id']), ('state', '=', 'opened')]

    def _post_read_pos_data(self, data):
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
        return super()._post_read_pos_data(data)

    def _post_read_pos_self_data(self, data):
        if data:
            data[0]['_base_url'] = self.get_base_url()
            data[0]['_self_order_pos'] = True
        return super()._post_read_pos_self_data(data)

    def set_opening_control(self, cashbox_value: int, notes: str):
        res = super().set_opening_control(cashbox_value, notes)

        # Set refs for takeout orders created when no session where opened
        for session in self:
            orders_no_session = self.env['pos.order'].search([
                ('config_id', '=', session.config_id.id),
                ('session_id', '=', False),
                ('pos_reference', '=', False),
                ('sequence_number', '=', False),
                ('tracking_number', '=', False),
            ])

            for order in orders_no_session:
                # An order created without a session is always coming from self-ordering mobile
                tracking_prefix = 'S'
                ref_prefix = 'Self-Order'
                pos_reference, sequence_number, tracking_number = session.get_next_order_refs(ref_prefix=ref_prefix, tracking_prefix=tracking_prefix)
                order.write({
                    'session_id': session.id,
                    'pos_reference': pos_reference,
                    'sequence_number': sequence_number,
                    'tracking_number': tracking_number,
                })

        return res
