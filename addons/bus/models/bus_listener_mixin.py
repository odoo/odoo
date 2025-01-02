# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class BusListenerMixin(models.AbstractModel):
    """Allow sending messages related to the current model via as a bus.bus channel.

    The model needs to be allowed as a valid channel for the bus in `_build_bus_channel_list`.
    """

    _description = "Can send messages via bus.bus"

    def _bus_send(self, notification_type, message, /, *, subchannel=None):
        """Send a notification to the webclient."""
        for record in self:
            main_channel = record._bus_channel()
            assert isinstance(main_channel, models.Model)
            main_channel.ensure_one()
            channel = main_channel if subchannel is None else (main_channel, subchannel)
            self.env["bus.bus"]._sendone(channel, notification_type, message)

    def _bus_channel(self):
        self.ensure_one()
        return self

    @api.model_create_multi
    def create(self, vals_list):
        records = super(BusListenerMixin, self).create(vals_list)

        if self.env.user._is_internal():
            for rec in records:
                # Prevent sync in models not required
                model = self.env['ir.model'].sudo().search([
                    ('model', '=', rec._name),
                    ('is_bus_sync_enabled', '=', True)
                ], limit=1)

                if model:
                    view_ids = self.env['ir.ui.view'].sudo().search([
                        ('active', '=', True),
                        ('model', '=', rec._name),
                        ('type', '=', 'list')
                    ])
                    for view in view_ids:
                        merged_view = f'bus.listener.mixin/create_{rec._name}_{view.id}'

                        self.env.user._bus_send(merged_view, {
                            'mergedView': merged_view
                        })

        return records
