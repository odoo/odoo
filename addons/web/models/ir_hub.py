from odoo import api, models
from odoo.tools.safe_eval import expr_eval
from odoo.tools.view_validation import get_expression_field_names


class IrHub(models.Model):
    _inherit = 'ir.hub'

    def _get_items_data(self):
        """ Return the items of this hub visible to the current user, as sent to
        the web client.
        """
        self.ensure_one()
        return self.item_ids.filtered('is_allowed').read(['display_name', 'action_id', 'python_method', 'context'])

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
        ``res_id`` of its model, with ``item`` being the opened item. The items
        themselves are taken from the lazy session (see ``_get_session_hubs``).
        """
        self.ensure_one()
        return {
            'id': self.id,
            'res_model': self.res_model,
            'res_id': res_id,
            'active_item_id': item.id,
            'invisible_item_ids': self._get_invisible_item_ids(res_id),
        }

    def _get_invisible_item_ids(self, res_id):
        """ Return the ids of the items of this hub hidden for the record
        ``res_id``, i.e. whose ``invisible`` expression is true on that record.
        """
        self.ensure_one()
        items = self.item_ids.filtered(lambda item: item.invisible and item.is_allowed)
        record = self.env[self.res_model].browse(res_id).exists()
        if not items or not record:
            return []
        model_fields = record._fields
        fnames = {
            fname
            for item in items
            for fname in get_expression_field_names(item.invisible)
            if fname in model_fields
        }
        # sudo: the expressions only drive the display of the items, they must
        # not fail on a field the user can't read; load=None reads many2one
        # fields as ids, as the invisible attribute of views evaluates them
        values = record.sudo().read(list(fnames), load=None)[0]
        return [item.id for item in items if expr_eval(item.invisible, values)]

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
