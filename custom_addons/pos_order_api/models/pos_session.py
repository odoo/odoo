from odoo import models, api, fields, _
from odoo.exceptions import UserError

class PosSession(models.Model):
    _inherit = 'pos.session'

    def action_pos_session_closing_control(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """
        Fix signature to match Odoo 19 core and remove dedicated delivery restriction.
        """
        # User wants to be able to close sessions manually even if they are delivery sessions.
        return super().action_pos_session_closing_control(balancing_account, amount_to_balance, bank_payment_method_diffs)

    delivery_active = fields.Boolean(
        string="Delivery Active", 
        default=True, 
        help="If unchecked, Online/Aggregator orders will be rejected for this session."
    )

    def action_toggle_delivery(self, active_state):
        """ Allow POS UI to toggle delivery status (Updates both Session and Config for persistence) """
        self = self.sudo()
        self.ensure_one()
        
        # Update Session
        self.write({'delivery_active': active_state})
        
        # Update Config for persistence across sessions
        self.config_id.write({'accept_remote_orders': active_state})
        
        # Log the change
        self.message_post(body=_("Delivery Status changed to %s by %s") % (
            _('Active') if active_state else _('Inactive'), 
            self.env.user.name
        ))
        
        # Broadcast to sync other tablets
        self.env['bus.bus']._sendone(self._get_bus_channel_name(), 'delivery_status_change', {
            'delivery_active': active_state,
            'session_id': self.id
        })
        return True

    def _get_bus_channel_name(self):
        return f"pos_session_{self.id}"

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        fields.append('delivery_active')
        return fields
