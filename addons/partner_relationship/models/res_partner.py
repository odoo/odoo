from collections import defaultdict

from odoo import api, fields, models
from odoo.fields import Domain

DEFAULT_MAX_DEGREE = 3
MAX_DEGREE_PARAMETER = "partner_relationship.max_degree"


class ResPartner(models.Model):
    _inherit = "res.partner"

    relation_out_ids = fields.One2many(
        comodel_name="res.partner.relation",
        inverse_name="partner_id",
        string="Relationships Declared",
    )
    relation_in_ids = fields.One2many(
        comodel_name="res.partner.relation",
        inverse_name="other_partner_id",
        string="Relationships Received",
    )
    relation_ids = fields.Many2many(
        comodel_name="res.partner.relation",
        string="Relationships",
        compute="_compute_relation_ids",
    )
    count_relation = fields.Integer(compute="_compute_relation_ids")
    related_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Related Parties",
        compute="_compute_related_partner_ids",
    )
    count_related_partner = fields.Integer(compute="_compute_related_partner_ids")

    @api.depends("relation_out_ids", "relation_in_ids")
    def _compute_relation_ids(self):
        for partner in self:
            relations = partner.relation_out_ids | partner.relation_in_ids
            partner.relation_ids = relations
            partner.count_relation = len(relations)

    @api.depends("relation_out_ids", "relation_in_ids")
    def _compute_related_partner_ids(self):
        degree_maps = self._get_relation_degree_maps()
        for partner in self:
            related = self.browse(set(degree_maps[partner.id]) - {partner.id})
            partner.related_partner_ids = related
            partner.count_related_partner = len(related)

    def action_view_relations(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Relationships"),
            "res_model": "res.partner.relation",
            "view_mode": "list,form",
            "domain": self.env["res.partner.relation"]._get_domain_touching(self.ids),
            "context": {"default_partner_id": self.id},
        }

    def action_new_relation(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("New Relationship"),
            "res_model": "res.partner.relation",
            "view_mode": "form",
            "target": "new",
            "context": {"default_partner_id": self.id},
        }

    def action_view_network(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Network of %s", self.display_name),
            "res_model": "res.partner",
            "res_id": self.id,
            "view_mode": "form",
            "views": [
                (
                    self.env.ref(
                        "partner_relationship.view_res_partner_form_network"
                    ).id,
                    "form",
                )
            ],
        }

    def action_view_related_partners(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Related Parties"),
            "res_model": "res.partner",
            "view_mode": "list,form",
            "domain": [("id", "in", self._get_related_partners().ids)],
        }

    def _get_related_partners(self, max_degree=None):
        reached = set()
        for degree_map in self._get_relation_degree_maps(max_degree).values():
            reached |= set(degree_map)
        return self.browse(reached - set(self.ids))

    def _get_relation_degree_map(self, max_degree=None):
        self.check_singleton()
        return self._get_relation_degree_maps(max_degree)[self.id]

    def _get_relation_degree_maps(self, max_degree=None):
        return {
            source_id: {node_id: degree for node_id, (degree, _, _) in reach.items()}
            for source_id, reach in self._get_relation_reach_maps(max_degree).items()
        }

    def _get_relation_reach_maps(self, max_degree=None, until=None):
        max_degree = self._get_max_relation_degree(max_degree)
        relations = self.env["res.partner.relation"]
        reach_per_source = {
            partner_id: {partner_id: (0, None, None)} for partner_id in self.ids
        }
        frontier = {partner_id: {partner_id} for partner_id in self.ids}

        for degree in range(1, max_degree + 1):
            if not frontier or (
                until is not None
                and all(until in reach for reach in reach_per_source.values())
            ):
                break
            edges = relations.search(relations._get_domain_touching(list(frontier)))
            next_frontier = defaultdict(set)
            for edge in edges:
                partner_id = edge.partner_id.id
                other_partner_id = edge.other_partner_id.id
                for node_id, via_id in (
                    (other_partner_id, partner_id),
                    (partner_id, other_partner_id),
                ):
                    for source_id in frontier.get(via_id, ()):
                        reach = reach_per_source[source_id]
                        if node_id not in reach:
                            reach[node_id] = (degree, edge, via_id)
                            next_frontier[node_id].add(source_id)
            frontier = next_frontier

        return reach_per_source

    def _get_relation_strength_map(self, max_degree=None):
        self.check_singleton()
        return self._get_relation_strength_maps(max_degree)[self.id]

    # The strongest chain to each contact, a chain being as strong as its
    # weakest tie. Unlike the degree walk a contact re-enters the frontier
    # whenever a stronger chain reaches it, so the same edge query serves every
    # source and every improvement.
    def _get_relation_strength_maps(self, max_degree=None):
        max_degree = self._get_max_relation_degree(max_degree)
        relations = self.env["res.partner.relation"]
        strength_per_source = {partner_id: {partner_id: 1.0} for partner_id in self.ids}
        frontier = {partner_id: {partner_id} for partner_id in self.ids}

        for _degree in range(max_degree):
            if not frontier:
                break
            edges = relations.search(relations._get_domain_touching(list(frontier)))
            next_frontier = defaultdict(set)
            for edge in edges:
                partner_id = edge.partner_id.id
                other_partner_id = edge.other_partner_id.id
                for node_id, via_id in (
                    (other_partner_id, partner_id),
                    (partner_id, other_partner_id),
                ):
                    for source_id in frontier.get(via_id, ()):
                        strength = strength_per_source[source_id]
                        candidate = min(strength[via_id], edge.weight_risk)
                        if node_id not in strength or candidate > strength[node_id]:
                            strength[node_id] = candidate
                            next_frontier[node_id].add(source_id)
            frontier = next_frontier

        for partner_id, strength in strength_per_source.items():
            strength.pop(partner_id, None)
        return strength_per_source

    def _get_relation_path(self, other, max_degree=None):
        self.check_singleton()
        other.check_singleton()
        if self == other:
            return []

        reach = self._get_relation_reach_maps(max_degree, until=other.id)[self.id]
        if other.id not in reach:
            return []

        path = []
        cursor = other.id
        while cursor != self.id:
            _degree, edge, via_id = reach[cursor]
            source = self.browse(via_id)
            path.append(
                {
                    "relation": edge,
                    "partner": source,
                    "other_partner": self.browse(cursor),
                    "label": edge._get_label_from(source),
                }
            )
            cursor = via_id
        path.reverse()
        return path

    @api.readonly
    def get_relation_network(self, max_degree=None):
        return self._get_relation_network(max_degree=max_degree)

    def _get_relation_network(self, max_degree=None):
        self.check_singleton()
        degree_per_id = self._get_relation_degree_map(max_degree)
        partners = self.browse(list(degree_per_id))._filtered_access("read")
        relations = self.env["res.partner.relation"]
        edges = relations.search(
            Domain("partner_id", "in", partners.ids)
            & Domain("other_partner_id", "in", partners.ids)
        )
        return {
            "focus_id": self.id,
            "max_degree": self._get_max_relation_degree(max_degree),
            "reached_degree": max(
                (degree_per_id[partner.id] for partner in partners), default=0
            ),
            "categories": self._get_relation_network_categories(edges),
            "nodes": [
                {
                    "id": partner.id,
                    "name": partner.display_name,
                    "degree": degree_per_id[partner.id],
                    "is_company": partner.is_company,
                }
                for partner in partners
            ],
            "edges": [
                {
                    "id": edge.id,
                    "source": edge.partner_id.id,
                    "target": edge.other_partner_id.id,
                    "label": edge._get_label_from(edge.partner_id),
                    "category": edge.category,
                    "weight_risk": edge.weight_risk,
                    "symmetric": edge.type_id.is_symmetric,
                }
                for edge in edges
            ],
        }

    @api.model
    def _get_relation_network_categories(self, edges):
        labels = dict(
            self.env["res.partner.relation.type"]
            ._fields["category"]
            ._description_selection(self.env)
        )
        present = {edge.category for edge in edges if edge.category}
        return [
            {"key": key, "label": label}
            for key, label in labels.items()
            if key in present
        ]

    @api.model
    def _get_graph_field_names(self):
        return ["related_partner_ids", "count_related_partner"]

    @api.model
    def _invalidate_relation_graph(self):
        self.env["res.partner"].invalidate_model(self._get_graph_field_names())

    @api.model
    def _get_max_relation_degree(self, max_degree=None):
        if max_degree is not None:
            return max_degree
        parameter = (
            self.env["ir.config_parameter"].sudo().get_param(MAX_DEGREE_PARAMETER)
        )
        if not parameter:
            return DEFAULT_MAX_DEGREE
        try:
            return max(int(parameter), 0)
        except TypeError, ValueError:
            return DEFAULT_MAX_DEGREE
