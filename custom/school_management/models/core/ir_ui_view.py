# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    type = fields.Selection(
        selection_add=[("gantt", "Gantt")],
        ondelete={"gantt": "cascade"},
    )

    def _get_view_info(self):
        return {"gantt": {"icon": "fa fa-tasks", "multi_record": True}} | super()._get_view_info()

    def _is_qweb_based_view(self, view_type):
        return view_type == "gantt" or super()._is_qweb_based_view(view_type)


class IrActionsActWindowView(models.Model):
    _inherit = "ir.actions.act_window.view"

    view_mode = fields.Selection(
        selection_add=[("gantt", "Gantt")],
        ondelete={"gantt": "cascade"},
    )
