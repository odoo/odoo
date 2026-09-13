from odoo import api, fields, models
from odoo.exceptions import UserError


class PartnerRelationPath(models.TransientModel):
    _name = "partner.relation.path"
    _description = "Relationship Path Between Two Contacts"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="From",
        required=True,
    )
    other_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="To",
        required=True,
    )
    max_degree = fields.Integer(
        string="Search Depth",
        default=lambda self: self.env["res.partner"]._get_max_relation_degree(),
    )
    relation_ids = fields.Many2many(
        comodel_name="res.partner.relation",
        string="Path",
        compute="_compute_path",
    )
    path_html = fields.Html(compute="_compute_path")
    count_hop = fields.Integer(compute="_compute_path")
    is_connected = fields.Boolean(compute="_compute_path")

    @api.depends("partner_id", "other_partner_id", "max_degree")
    def _compute_path(self):
        for wizard in self:
            path = wizard._get_path()
            wizard.relation_ids = [hop["relation"].id for hop in path]
            wizard.count_hop = len(path)
            wizard.is_connected = bool(path)
            wizard.path_html = wizard._render_path(path)

    def action_view_path_relations(self):
        self.check_singleton()
        if not self.relation_ids:
            raise UserError(
                self.env._(
                    "No relationship path was found between %(one)s and"
                    " %(other)s within %(degree)s degrees.",
                    one=self.partner_id.display_name,
                    other=self.other_partner_id.display_name,
                    degree=self.max_degree,
                )
            )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Relationship Path"),
            "res_model": "res.partner.relation",
            "view_mode": "list,form",
            "domain": [("id", "in", self.relation_ids.ids)],
        }

    def _get_path(self):
        self.check_singleton()
        if not self.partner_id or not self.other_partner_id:
            return []
        return self.partner_id._get_relation_path(
            self.other_partner_id, max_degree=self.max_degree or None
        )

    def _render_path(self, path):
        self.check_singleton()
        if not path:
            return False
        return self.env["ir.qweb"]._render(
            "partner_relationship.relation_path_document",
            {"start": self.partner_id, "path": path},
        )
