from odoo import api, models


class IrHub(models.Model):
    _inherit = 'ir.hub'

    def _get_items_data(self):
        """ Return the items of this hub visible to the current user, as sent to
        the web client.
        """
        self.ensure_one()
        return self.item_ids._filter_visible().read(['display_name', 'action_id', 'python_method', 'context'])

    @api.model
    def _get_session_hubs(self):
        """ Return the hubs per model, sent with the lazy session info for the
        web client to open them on their default item without a server round
        trip (see the ``hub_default`` client action).
        """
        return {
            hub.res_model: {'id': hub.id, 'item_ids': hub._get_items_data()}
            for hub in self.search([])
        }

    def _get_hub_info(self, item, res_id):
        """ Return what the web client needs to display this hub for the record
        ``res_id`` of its model, with ``item`` being the opened item.
        """
        self.ensure_one()
        return {
            'id': self.id,
            'res_model': self.res_model,
            'res_id': res_id,
            'item_ids': self._get_items_data(),
            'active_item_id': item.id,
        }

    def _add_hub_info(self, action, item, res_id):
        """ Make ``action``, opening ``item`` for the record ``res_id``, display
        this hub, and name it after that record and item.
        """
        self.ensure_one()
        record = self.env[self.res_model].browse(res_id)
        action['hub'] = self._get_hub_info(item, res_id)
        action['display_name'] = self.env._(
            "%(record)s - %(item)s", record=record.display_name, item=item.display_name,
        )
        return action
