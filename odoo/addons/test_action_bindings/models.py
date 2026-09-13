from odoo import api, fields, models


class TabA(models.Model):
    _name = "tab.a"
    _description = "tab.a"


class TabB(models.Model):
    _name = "tab.b"
    _description = "tab.b"


class TabActionHolder(models.Model):
    _name = "tab.action.holder"
    _description = "tab.action.holder"

    action_id = fields.Many2one(
        comodel_name="ir.actions.actions",
        ondelete="cascade",
    )


class TabActionMirror(models.Model):
    _name = "tab.action.mirror"
    _description = "tab.action.mirror"

    holder_id = fields.Many2one(
        comodel_name="tab.action.holder",
        required=True,
        ondelete="cascade",
    )
    action_id = fields.Many2one(
        comodel_name="ir.actions.actions",
        related="holder_id.action_id",
        store=True,
    )


class TabActionComputed(models.Model):
    _name = "tab.action.computed"
    _description = "tab.action.computed"

    holder_id = fields.Many2one(comodel_name="tab.action.holder")
    action_id = fields.Many2one(
        comodel_name="ir.actions.actions",
        compute="_compute_action_id",
    )

    @api.depends("holder_id.action_id")
    def _compute_action_id(self) -> None:
        for record in self:
            record.action_id = record.holder_id.action_id
