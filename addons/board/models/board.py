from lxml import etree

from odoo import api, fields, models

from odoo.addons.base.models.ir_ui_view_base import attach_ir


class BoardBoard(models.AbstractModel):
    _name = "board.board"
    _description = "Board"
    _auto = False

    # This is necessary for when the web client opens a dashboard. Technically
    # speaking, the dashboard is a form view, and opening it makes the client
    # initialize a dummy record by invoking onchange(). And the latter requires
    # an 'id' field to work properly...
    id = fields.Id()

    @api.model_create_multi
    def create(self, vals_list):
        return self

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        """Override ``get_view`` to merge the user's saved dashboard layout and preprocess the arch.

        :return: view dict (fields, arch, toolbar)
        """

        res = super().get_view(view_id, view_type, **options)

        custom_view = (
            self.env["ir.ui.view.custom"]
            .sudo()
            .search([("user_id", "=", self.env.uid), ("ref_id", "=", view_id)], limit=1)
        )
        if custom_view:
            res.update({"custom_view_id": custom_view.id, "arch": custom_view.arch})
        res["arch"] = self._arch_preprocessing(res["arch"])
        return attach_ir(res)

    @api.model
    def _arch_preprocessing(self, arch):
        archnode = etree.fromstring(arch)
        # add the js_class 'board' on the fly to force the webclient to
        # instantiate a BoardView instead of FormView
        archnode.set("js_class", "board")
        return etree.tostring(archnode, pretty_print=True, encoding="unicode")
