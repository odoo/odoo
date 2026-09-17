from odoo import api, fields, models

NON_WINDOW_VIEW_TYPES = ("search", "qweb")


class IrActionsAct_WindowView(models.Model):
    _name = "ir.actions.act_window.view"
    _description = "Action Window View"
    _table = "ir_act_window_view"
    _rec_name = "view_id"
    _order = "sequence,id"
    _allow_sudo_commands = False

    sequence = fields.Integer()
    view_id = fields.Many2one(comodel_name="ir.ui.view")
    view_mode = fields.Selection(
        selection="_selection_view_mode",
        string="View Type",
        required=True,
    )
    act_window_id = fields.Many2one(
        comodel_name="ir.actions.act_window",
        string="Action",
        index="btree_not_null",
        ondelete="cascade",
    )
    multi = fields.Boolean(
        string="On Multiple Doc.",
        help="If set to true, the action will not be displayed on the right toolbar of a form view.",
    )

    _unique_mode_per_action = models.UniqueIndex(
        "(act_window_id, view_mode) WHERE act_window_id IS NOT NULL"
    )

    @api.model
    def _selection_view_mode(self):
        # A window can show every view type but the two that are not views of
        # records: the vocabulary is ir.ui.view's, read at call time, so a
        # module registering a type registers a window mode with it and
        # nothing has to say it twice.
        return [
            (value, label)
            for value, label in self.env["ir.ui.view"]
            ._fields["type"]
            ._description_selection(self.env)
            if value not in NON_WINDOW_VIEW_TYPES
        ]
