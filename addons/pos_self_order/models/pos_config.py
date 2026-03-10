# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = "pos.config"

    self_order_config_ids = fields.One2many('pos.self.order.config', 'pos_config_id', string="Self-ordering configuration")  # Technically One2one
    self_ordering_mode = fields.Selection(related="self_order_config_ids.ordering_mode", string="Self-ordering mode")

    @api.constrains('pos_config_id')
    def _constrain_pos_config_id(self):
        config_ids = self.env['pos.config'].search([('self_order_config_ids', '!=', False)])
        for record in self:
            filtered_config_ids = config_ids.filtered(lambda c: c != record and c.self_order_config_ids == record.self_order_config_ids)
            if filtered_config_ids:
                raise ValidationError(_("The POS configuration %s is already linked to another self-ordering configuration.") % record.name)

    def _load_pos_self_data_domain(self, data, config):
        return [('id', '=', data['pos.self.order.config'][0]['pos_config_id'])]

    @api.model
    def _load_pos_self_data_fields(self, config):
        return ['id']

    def close_ui(self):
        if self.self_ordering_mode == "kiosk":
            return self.action_close_kiosk_session()
        return super().close_ui()

    def action_close_kiosk_session(self):
        if self.current_session_id and self.current_session_id.order_ids:
            self.current_session_id.order_ids.filtered(lambda o: o.state == 'draft').unlink()

        self._notify('STATUS', {'status': 'closed'})
        return self.current_session_id.action_pos_session_closing_control()

    def _compute_status(self):
        for record in self:
            record.status = 'active' if record.has_active_session else 'inactive'

    def action_open_wizard(self):
        self.ensure_one()

        if not self.current_session_id:
            res = self._check_before_creating_new_session()
            if res:
                return res
            session = self.env['pos.session'].create({'user_id': self.env.uid, 'config_id': self.id})
            session.set_opening_control(0, "")
            self._notify('STATUS', {'status': 'open'})

        return {
            'type': 'ir.actions.act_url',
            'name': _('Self Order'),
            'target': 'new',
            'url': self.get_kiosk_url(),
        }

    def get_kiosk_url(self):
        return self.self_ordering_url

    def has_valid_self_payment_method(self):
        """ Checks if the POS config has a valid payment method (terminal or online). """
        self.ensure_one()
        domain = self.payment_method_ids._load_pos_self_data_domain({}, self)
        return bool(self.payment_method_ids.filtered_domain(domain))

    @api.model
    def load_onboarding_kiosk_scenario(self):
        if not bool(self.env.company.chart_template):
            return

        journal, payment_methods_ids = self._create_journal_and_payment_methods()
        restaurant_categories = self.get_record_by_ref([
            'pos_restaurant.food',
            'pos_restaurant.drinks',
        ])
        not_cash_payment_methods_ids = self.env['pos.payment.method'].search([
            ('is_cash_count', '=', False),
            ('id', 'in', payment_methods_ids),
        ]).ids
        self.env['pos.config'].create({
            'name': _('Kiosk'),
            'company_id': self.env.company.id,
            'journal_id': journal.id,
            'payment_method_ids': not_cash_payment_methods_ids,
            'limit_categories': True,
            'iface_available_categ_ids': restaurant_categories,
            'iface_splitbill': True,
            'module_pos_restaurant': True,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
        })

    def _load_restaurant_demo_data(self, with_demo_data=True):
        self.ensure_one()
        super()._load_restaurant_demo_data(with_demo_data)
        if with_demo_data:
            self.self_ordering_mode = 'mobile'
