# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import math

from odoo import api, models
from odoo.fields import Domain


class LoyaltyReward(models.Model):
    _name = 'loyalty.reward'
    _inherit = ['loyalty.reward', 'pos.load.mixin']

    def _get_pos_points_cost(self, reward_lines, available_points):
        """
        Points this reward costs as applied on `reward_lines`.

        mirror of *static/src/app/models/loyalty_reward.js* LoyaltyReward.getRewardLines

        :param reward_lines: this reward's lines on the order
        :param available_points: points the card can spend on this order (card balance
            plus what the order issues, minus what earlier rewards already consumed)
        """
        self.ensure_one()
        if self.clear_wallet:
            return available_points
        if self.program_id.is_payment_program:
            # Payment line, mirrors pos.order.applyPaymentProgram: the line's
            # tax-included total is the paid amount, the cost is paid / discount.
            if not self.discount:
                return 0
            paid = -sum(reward_lines.mapped('price_subtotal_incl'))
            return paid / self.discount
        if self.reward_type == 'product':
            if not self.reward_product_qty:
                return 0
            qty = sum(reward_lines.mapped('qty'))
            return math.ceil(qty / self.reward_product_qty) * self.required_points
        if self.discount_mode == 'per_point':
            if not self.discount:
                return 0
            reduction = -sum(reward_lines.mapped('price_subtotal_incl'))
            return self.currency_id.round(reduction / self.discount)
        return self.required_points

    @api.model
    def _load_pos_data_domain(self, data):
        reward_product_tag_domain = [
            ('reward_product_tag_id', '!=', False),
            '|',
            ('reward_product_tag_id.product_template_ids.active', '=', True),
            ('reward_product_tag_id.product_product_ids.active', '=', True),
        ]
        return Domain.AND([
            [('program_id', 'in', data['pos.config']._get_program_ids().ids)],
            Domain.OR([
                [('reward_type', '!=', 'product')],
                [('reward_product_id.active', '=', True)],
                reward_product_tag_domain,
            ]),
        ])

    @api.model
    def _load_pos_data_fields(self, config):
        return ['description', 'program_id', 'reward_type', 'required_points', 'clear_wallet', 'currency_id',
                'discount', 'discount_mode', 'discount_applicability', 'all_discount_product_ids', 'is_global_discount',
                'discount_max_amount', 'discount_line_product_id', 'reward_product_id',
                'multi_product', 'reward_product_ids', 'reward_product_qty', 'reward_product_uom_id', 'reward_product_domain']

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        for reward in read_records:
            reward['reward_product_domain'] = self._replace_ilike_with_in(reward['reward_product_domain'])
        return read_records

    def _get_reward_product_domain_fields(self, config):
        """Product fields referenced by the reward domains of this config's programs.

        These must be loaded onto the POS product so the domains can be evaluated
        client-side; otherwise a char-field condition (e.g. `name ilike ...`, which
        stays untouched by `_replace_ilike_with_in`) would hit an undefined field.
        """
        fields = set()
        search_domain = [('program_id', 'in', config._get_program_ids().ids)]
        domains = self.search_read(search_domain, fields=['reward_product_domain'], load=False)
        for domain in filter(lambda d: d['reward_product_domain'] != "null", domains):
            for condition in self._parse_domain(json.loads(domain['reward_product_domain'])).values():
                field_name, _, _ = condition
                fields.add(field_name)
        return fields

    def _replace_ilike_with_in(self, domain_str):
        if domain_str == "null":
            return domain_str

        domain = json.loads(domain_str)

        for index, condition in self._parse_domain(domain).items():
            field_name, operator, value = condition
            field = self.env['product.product']._fields.get(field_name)

            if field and field.type in ['many2one', 'many2many'] and operator in ('ilike', 'not ilike'):
                comodel = self.env[field.comodel_name]
                matching_ids = list(comodel._search([('display_name', 'ilike', value)]))

                new_operator = 'in' if operator == 'ilike' else 'not in'
                domain[index] = [field_name, new_operator, matching_ids]

        return json.dumps(domain)

    def _parse_domain(self, domain):
        parsed_domain = {}
        for index, condition in enumerate(domain):
            if isinstance(condition, (list, tuple)) and len(condition) == 3:
                parsed_domain[index] = condition
        return parsed_domain

    def unlink(self):
        if len(self) == 1 and self.env['pos.order.line'].sudo().search_count([('reward_id', 'in', self.ids)], limit=1):
            return self.action_archive()
        return super().unlink()
