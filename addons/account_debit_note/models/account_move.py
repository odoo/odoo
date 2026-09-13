from odoo import _, api, fields, models
from odoo.fields import Domain


class AccountMove(models.Model):
    _inherit = "account.move"

    debit_origin_id = fields.Many2one(
        comodel_name="account.move",
        string="Original Invoice Debited",
        index="btree_not_null",
        copy=False,
        readonly=True,
    )
    debit_note_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="debit_origin_id",
        string="Debit Notes",
        help="The debit notes created for this invoice",
    )
    debit_note_count = fields.Integer(
        string="Number of Debit Notes",
        compute="_compute_debit_count",
    )

    @api.depends("debit_note_ids")
    def _compute_debit_count(self):
        debit_data = self.env["account.move"]._read_group(
            [("debit_origin_id", "in", self.ids)], ["debit_origin_id"], ["__count"]
        )
        data_map = {debit_origin.id: count for debit_origin, count in debit_data}
        for inv in self:
            inv.debit_note_count = data_map.get(inv.id, 0.0)

    def action_view_debit_notes(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": _("Debit Notes"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("debit_origin_id", "=", self.id)],
        }

    def action_debit_note(self):
        action = self.env.ref(
            "account_debit_note.action_view_account_move_debit"
        )._get_action_dict()
        return action

    def _get_domain_last_sequence(self, relaxed=False):
        domain = super()._get_domain_last_sequence(relaxed)
        if self.journal_id.debit_sequence:
            domain &= Domain(
                "debit_origin_id", "!=" if self.debit_origin_id else "=", False
            )
        return domain

    def _get_starting_sequence(self):
        starting_sequence = super()._get_starting_sequence()
        if (
            self.journal_id.debit_sequence
            and self.debit_origin_id
            and self.move_type in ("in_invoice", "out_invoice")
        ):
            starting_sequence = "D" + starting_sequence
        return starting_sequence

    def _get_copy_message_content(self, default):
        """Override to handle debit note specific messages."""
        if default and default.get("debit_origin_id"):
            return _("This debit note was created from: %s", self._get_html_link())
        return super()._get_copy_message_content(default)
