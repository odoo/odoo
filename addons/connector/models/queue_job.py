# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import _, models


class QueueJob(models.Model):

    _inherit = "queue.job"

    def related_action_unwrap_binding(self, component_usage="binder"):
        """Open a form view with the unwrapped record.

        For instance, for a job on a ``magento.product.product``,
        it will open a ``product.product`` form view with the unwrapped
        record.

        :param component_usage: base component usage to search for the binder
        """
        self.ensure_one()
        model_name = self.model_name
        binding = self.env[model_name].browse(self.record_ids).exists()
        if not binding:
            return None
        if len(binding) > 1:
            # not handled
            return None
        action = {
            "name": _("Related Record"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
        }
        with binding.backend_id.work_on(binding._name) as work:
            binder = work.component(usage=component_usage)
        try:
            model = binder.unwrap_model()
            record = binder.unwrap_binding(binding)
            # the unwrapped record will be displayed
            action.update({"res_model": model, "res_id": record.id})
        except ValueError:
            # the binding record will be displayed
            action.update({"res_model": binding._name, "res_id": binding.id})
        return action
