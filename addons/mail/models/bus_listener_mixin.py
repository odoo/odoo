# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.mail.tools.discuss import Store


class BusListenerMixin(models.AbstractModel):
    _inherit = "bus.listener.mixin"

    def _bus_send_store(
        self, /, *args, notification_type="mail.record/insert", subchannel=None, **kwargs
    ):
        """Use the given Store or create a Store from the given params and send this
        Store to ``self`` bus listener."""
        if len(args) == 1 and isinstance(args[0], Store):
            assert not kwargs, f"should not have kwargs with Store: {kwargs}"
            store = args[0]
        else:
            store = Store(*args, **kwargs)
        if res := store.get_result():
            self._bus_send(notification_type, res, subchannel=subchannel)
