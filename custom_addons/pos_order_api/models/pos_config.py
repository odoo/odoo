from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # Virtual / Delivery POS
    is_delivery_config = fields.Boolean(
        string='Is Delivery / Virtual POS',
        help='This POS is used only for online or aggregator orders and is kept open automatically.'
    )

    # Physical POS
    accept_remote_orders = fields.Boolean(
        string='Accept Remote Orders',
        help='Allow this POS to receive and print online / aggregator orders.'
    )

    @api.model
    def _cron_auto_open_delivery_session(self):
        """
        Ensure all Delivery / Virtual POS configs always have an open session.
        """
        delivery_configs = self.search([('is_delivery_config', '=', True)])
        for config in delivery_configs:
            if config.current_session_state != 'opened':
                try:
                    # open_ui ensures a session exists in newer Odoo versions
                    config.open_ui()
                    if not config.current_session_id:
                        config._open_session()
                except Exception:
                    # Never block cron
                    pass

    def write(self, vals):
        res = super().write(vals)
        if 'accept_remote_orders' in vals or 'is_delivery_config' in vals:
            for config in self:
                self.env['bus.bus']._sendone(config._get_bus_channel(), 'POS_CONFIG_UPDATE', {
                    'accept_remote_orders': config.accept_remote_orders,
                    'is_delivery_config': config.is_delivery_config,
                })
        return res

    def _get_bus_channel(self):
        self.ensure_one()
        return f"pos_config_{self.id}"
