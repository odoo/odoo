from odoo import api, fields, models
from odoo.tools import SQL


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


class TabActionView(models.Model):
    """A SQL view over the holders: it derives its rows, so none can dangle."""

    _name = "tab.action.view"
    _description = "tab.action.view"
    _auto = False

    action_id = fields.Many2one(comodel_name="ir.actions.actions", readonly=True)

    def init(self) -> None:
        self.env.cr.execute(
            SQL(
                "CREATE OR REPLACE VIEW %s AS SELECT id, action_id FROM tab_action_holder",
                SQL.identifier(self._table),
            )
        )


class TabReferenceView(models.Model):
    """A SQL view carrying a res_model/res_id pair, like ir.attachment.report."""

    _name = "tab.reference.view"
    _description = "tab.reference.view"
    _auto = False

    res_model = fields.Char(readonly=True)
    res_id = fields.Many2oneReference(model_field="res_model", readonly=True)

    def init(self) -> None:
        self.env.cr.execute(
            SQL(
                "CREATE OR REPLACE VIEW %s AS SELECT id,"
                " 'ir.actions.act_window'::varchar AS res_model,"
                " action_id AS res_id FROM tab_action_holder",
                SQL.identifier(self._table),
            )
        )
