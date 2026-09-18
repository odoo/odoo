from odoo import fields, models


class IrActionsAct_Url(models.Model):
    _name = "ir.actions.act_url"
    _description = "Action URL"
    _table = "ir_act_url"
    _inherit = ["ir.actions.actions"]

    url = fields.Text(
        string="Action URL",
        required=True,
    )
    target = fields.Selection(
        selection=[
            ("new", "New Window"),
            ("self", "This Window"),
            ("download", "Download"),
        ],
        string="Action Target",
        default="new",
        required=True,
    )

    def _get_fields_readable(self) -> frozenset[str]:
        return super()._get_fields_readable() | {"target", "url"}

    def _get_keys_client_only(self) -> frozenset[str]:
        return super()._get_keys_client_only() | {"close"}
