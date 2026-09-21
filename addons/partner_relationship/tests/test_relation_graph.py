from odoo import fields
from odoo.tests import tagged

from .common import PartnerRelationCommon
from odoo.addons.partner_relationship.models.res_partner_relation_type import (
    CATEGORY_SELECTION,
)

CATEGORY_KEYS = [key for key, _label in CATEGORY_SELECTION]


@tagged("post_install", "-at_install")
class TestRelationGraph(PartnerRelationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.juan_maria = cls._create_relation(cls.juan, cls.type_spouse, cls.maria)
        cls.maria_pedro = cls._create_relation(cls.maria, cls.type_compadre, cls.pedro)
        cls.pedro_lucia = cls._create_relation(cls.pedro, cls.type_crop, cls.lucia)

    def test_relations_are_collected_from_both_ends(self):
        self.assertEqual(self.maria.count_relation, 2)
        self.assertEqual(self.maria.relation_ids, self.juan_maria | self.maria_pedro)

    def test_degree_is_the_hop_count(self):
        degrees = self.juan._get_relation_degree_map()

        self.assertEqual(degrees[self.juan.id], 0)
        self.assertEqual(degrees[self.maria.id], 1)
        self.assertEqual(degrees[self.pedro.id], 2)
        self.assertEqual(degrees[self.lucia.id], 3)

    def test_the_walk_stops_at_the_requested_degree(self):
        degrees = self.juan._get_relation_degree_map(max_degree=2)

        self.assertIn(self.pedro.id, degrees)
        self.assertNotIn(self.lucia.id, degrees)

    def test_an_unconnected_contact_is_never_reached(self):
        related = self.juan._get_related_partners()

        self.assertNotIn(self.stranger, related)

    def test_a_contact_not_yet_saved_has_no_related_party(self):
        unsaved = self.env["res.partner"].new({"name": "Unsaved"})

        self.assertFalse(unsaved.related_partner_ids)
        self.assertEqual(unsaved.count_related_partner, 0)
        self.assertEqual(unsaved._get_relation_degree_map(), {unsaved.id: 0})
        self.assertEqual(unsaved._get_relation_strength_map(), {})

    def test_the_related_party_group_excludes_the_contact_itself(self):
        related = self.juan._get_related_partners()

        self.assertNotIn(self.juan, related)
        self.assertEqual(related, self.maria | self.pedro | self.lucia)

    def test_a_path_is_worded_from_each_contact_own_end(self):
        path = self.juan._get_relation_path(self.pedro)

        self.assertEqual([hop["label"] for hop in path], ["husband of", "comadre of"])
        self.assertEqual(path[0]["partner"], self.juan)
        self.assertEqual(path[-1]["other_partner"], self.pedro)

    def test_a_path_is_the_shortest_one(self):
        self._create_relation(self.juan, self.type_sibling, self.lucia)

        path = self.juan._get_relation_path(self.lucia)

        self.assertEqual(len(path), 1)

    def test_no_path_beyond_the_requested_degree(self):
        self.assertEqual(self.juan._get_relation_path(self.lucia, max_degree=2), [])

    def test_no_path_to_an_unconnected_contact(self):
        self.assertEqual(self.juan._get_relation_path(self.stranger), [])

    def test_the_walk_searches_once_per_degree(self):
        relations = self.env["res.partner.relation"]
        original_search = type(relations).search
        calls = []

        def counting_search(records, *args, **kwargs):
            calls.append(records._name)
            return original_search(records, *args, **kwargs)

        self.patch(type(relations), "search", counting_search)
        self.juan._get_relation_degree_map(max_degree=3)

        self.assertEqual(len(calls), 3)

    def test_a_chain_is_as_strong_as_its_weakest_tie(self):
        strengths = self.juan._get_relation_strength_map()

        self.assertEqual(strengths[self.maria.id], self.type_spouse.weight_risk)
        self.assertEqual(strengths[self.pedro.id], self.type_compadre.weight_risk)
        self.assertEqual(strengths[self.lucia.id], self.type_compadre.weight_risk)

    def test_the_strongest_chain_wins_over_the_shortest(self):
        weak = self.env["res.partner.relation.type"].create(
            {
                "code": "test_weak",
                "name": "acquainted with",
                "is_symmetric": True,
                "category": "business",
                "weight_risk": 0.05,
            }
        )
        self._create_relation(self.juan, weak, self.lucia)

        strengths = self.juan._get_relation_strength_map()

        self.assertEqual(strengths[self.lucia.id], self.type_compadre.weight_risk)

    def test_the_strength_map_covers_exactly_the_related_partners(self):
        weightless = self.env["res.partner.relation.type"].create(
            {
                "code": "test_no_weight",
                "name": "acquainted with",
                "is_symmetric": True,
                "category": "business",
                "weight_risk": 0.0,
            }
        )
        self._create_relation(self.juan, weightless, self.stranger)

        degrees = self.juan._get_relation_degree_map()
        strengths = self.juan._get_relation_strength_map()

        self.assertEqual(set(strengths), set(degrees) - {self.juan.id})
        self.assertEqual(strengths[self.stranger.id], 0.0)

    def test_strength_never_reaches_an_unconnected_contact(self):
        strengths = self.juan._get_relation_strength_map()

        self.assertNotIn(self.stranger.id, strengths)
        self.assertNotIn(self.juan.id, strengths)

    def test_the_related_group_is_fresh_after_a_distant_relation(self):
        outsider = self._create_person("Outsider", "male")
        self.assertNotIn(outsider, self.juan.related_partner_ids)

        self._create_relation(self.maria, self.type_sibling, outsider)

        self.assertIn(outsider, self.juan.related_partner_ids)

    def test_the_network_carries_every_reached_contact_with_its_degree(self):
        network = self.juan._get_relation_network()

        degree_per_id = {node["id"]: node["degree"] for node in network["nodes"]}

        self.assertEqual(network["focus_id"], self.juan.id)
        self.assertEqual(degree_per_id[self.juan.id], 0)
        self.assertEqual(degree_per_id[self.maria.id], 1)
        self.assertEqual(degree_per_id[self.pedro.id], 2)
        self.assertEqual(degree_per_id[self.lucia.id], 3)
        self.assertNotIn(self.stranger.id, degree_per_id)

    def test_a_network_edge_is_worded_from_its_own_source(self):
        network = self.juan._get_relation_network()

        label_per_id = {edge["id"]: edge["label"] for edge in network["edges"]}

        self.assertEqual(label_per_id[self.juan_maria.id], "husband of")
        self.assertEqual(label_per_id[self.maria_pedro.id], "comadre of")

    def test_a_network_edge_leaving_the_last_ring_is_dropped(self):
        network = self.juan._get_relation_network(max_degree=2)

        drawn = {edge["id"] for edge in network["edges"]}

        self.assertIn(self.maria_pedro.id, drawn)
        self.assertNotIn(self.pedro_lucia.id, drawn)

    def test_every_network_edge_ends_on_a_drawn_node(self):
        self._create_relation(self.lucia, self.type_sibling, self.stranger)

        for degree in range(1, 5):
            network = self.juan._get_relation_network(max_degree=degree)
            drawn = {node["id"] for node in network["nodes"]}
            for edge in network["edges"]:
                self.assertIn(edge["source"], drawn)
                self.assertIn(edge["target"], drawn)

    def test_the_reached_degree_is_the_walk_not_the_ceiling(self):
        network = self.juan._get_relation_network(max_degree=9)

        self.assertEqual(network["max_degree"], 9)
        self.assertEqual(network["reached_degree"], 3)

    def test_the_reached_degree_falls_with_the_ceiling(self):
        network = self.juan._get_relation_network(max_degree=2)

        self.assertEqual(network["reached_degree"], 2)

    def test_an_unrelated_contact_reaches_degree_zero(self):
        network = self.stranger._get_relation_network()

        self.assertEqual(network["reached_degree"], 0)
        self.assertEqual(network["edges"], [])

    def test_the_network_names_only_the_categories_it_drew(self):
        network = self.juan._get_relation_network()

        drawn = {edge["category"] for edge in network["edges"]}
        named = [category["key"] for category in network["categories"]]

        self.assertEqual(set(named), drawn)
        self.assertNotIn("blood", named)

    def test_a_category_left_outside_the_ceiling_is_not_named(self):
        self.assertIn(
            "agricultural",
            [
                category["key"]
                for category in self.juan._get_relation_network()["categories"]
            ],
        )

        network = self.juan._get_relation_network(max_degree=2)

        self.assertNotIn(
            "agricultural", [category["key"] for category in network["categories"]]
        )

    def test_the_categories_are_labelled_and_ordered_by_the_selection(self):
        self._create_relation(self.juan, self.type_sibling, self.stranger)

        network = self.juan._get_relation_network()

        named = [category["key"] for category in network["categories"]]
        labels = {
            category["key"]: category["label"] for category in network["categories"]
        }

        self.assertEqual(named, ["blood", "affinity", "ritual", "agricultural"])
        self.assertEqual(named, sorted(named, key=CATEGORY_KEYS.index))
        self.assertEqual(labels["blood"], "Consanguinity")
        self.assertEqual(labels["agricultural"], "Agricultural")

    def test_a_recordset_is_walked_in_one_query_per_degree(self):
        hubs = self.env["res.partner"]
        for index in range(12):
            hub = self._create_person(f"Hub {index}", "male")
            near = self._create_person(f"Near {index}", "female")
            far = self._create_person(f"Far {index}", "male")
            self._create_relation(hub, self.type_sibling, near)
            self._create_relation(near, self.type_compadre, far)
            hubs |= hub
        self.env.flush_all()
        self.env.invalidate_all()

        relations = self.env["res.partner.relation"]
        original_search = type(relations).search
        calls = []

        def counting_search(records, *args, **kwargs):
            calls.append(records._name)
            return original_search(records, *args, **kwargs)

        self.patch(type(relations), "search", counting_search)
        counts = hubs.mapped("count_related_partner")

        self.assertEqual(counts, [2] * 12)
        self.assertEqual(len(calls), 3)

    def test_each_source_of_a_batched_walk_keeps_its_own_degrees(self):
        degree_maps = (self.juan | self.pedro)._get_relation_degree_maps()

        self.assertEqual(degree_maps[self.juan.id][self.pedro.id], 2)
        self.assertEqual(degree_maps[self.pedro.id][self.juan.id], 2)
        self.assertEqual(degree_maps[self.pedro.id][self.lucia.id], 1)
        self.assertNotIn(self.stranger.id, degree_maps[self.juan.id])

    def test_the_related_parties_of_a_recordset_are_the_union(self):
        related = (self.juan | self.stranger)._get_related_partners()

        self.assertEqual(related, self.maria | self.pedro | self.lucia)

    def test_the_path_and_the_degree_map_agree_on_the_distance(self):
        path = self.juan._get_relation_path(self.lucia)

        self.assertEqual(len(path), self.juan._get_relation_degree_map()[self.lucia.id])
        self.assertEqual(
            [hop["relation"] for hop in path],
            [self.juan_maria, self.maria_pedro, self.pedro_lucia],
        )

    def test_the_path_search_stops_as_soon_as_the_other_end_is_reached(self):
        relations = self.env["res.partner.relation"]
        original_search = type(relations).search
        calls = []

        def counting_search(records, *args, **kwargs):
            calls.append(records._name)
            return original_search(records, *args, **kwargs)

        self.patch(type(relations), "search", counting_search)
        self.juan._get_relation_path(self.maria, max_degree=3)

        self.assertEqual(len(calls), 1)

    def test_the_network_leaves_out_a_contact_the_user_may_not_read(self):
        other_company = self.env["res.company"].create({"name": "Elsewhere"})
        hidden = self.env["res.partner"].create(
            {"name": "Hidden", "company_id": other_company.id}
        )
        self._create_relation(self.lucia, self.type_sibling, hidden)
        user = self.env["res.users"].create(
            {
                "name": "Clerk",
                "login": "clerk_partner_relationship",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

        network = self.juan.with_user(user).get_relation_network(max_degree=4)

        drawn = {node["id"] for node in network["nodes"]}
        self.assertIn(self.lucia.id, drawn)
        self.assertNotIn(hidden.id, drawn)
        for edge in network["edges"]:
            self.assertIn(edge["source"], drawn)
            self.assertIn(edge["target"], drawn)
        self.assertEqual(network["reached_degree"], 3)

    def test_the_path_wizard_carries_the_relations_it_found(self):
        wizard = self.env["partner.relation.path"].create(
            {"partner_id": self.juan.id, "other_partner_id": self.pedro.id}
        )

        self.assertTrue(wizard.is_connected)
        self.assertEqual(wizard.count_hop, 2)
        self.assertEqual(wizard.relation_ids, self.juan_maria | self.maria_pedro)
        self.assertIn("husband of", wizard.path_html)
        self.assertEqual(
            wizard.action_view_path_relations()["domain"],
            [("id", "in", wizard.relation_ids.ids)],
        )

    def test_the_path_wizard_reports_no_path_within_its_depth(self):
        wizard = self.env["partner.relation.path"].create(
            {
                "partner_id": self.juan.id,
                "other_partner_id": self.lucia.id,
                "max_degree": 2,
            }
        )

        self.assertFalse(wizard.is_connected)
        self.assertFalse(wizard.relation_ids)
        self.assertFalse(wizard.path_html)

    def test_an_ended_tie_reaches_nobody_but_stays_on_the_contact(self):
        self.juan_maria.date_end = "2020-01-01"

        self.assertIn(self.juan_maria, self.juan.relation_ids)
        self.assertEqual(self.juan._get_related_partners(), self.env["res.partner"])
        self.assertEqual(self.juan._get_relation_path(self.pedro), [])
        self.assertEqual(self.juan._get_relation_strength_map(), {})

    def test_a_tie_ending_today_is_still_in_force(self):
        self.juan_maria.date_end = fields.Date.context_today(self.juan)

        self.assertIn(self.maria, self.juan._get_related_partners())

    def test_a_recordset_strength_walk_matches_the_walk_per_contact(self):
        partners = self.juan | self.pedro | self.stranger

        strength_maps = partners._get_relation_strength_maps()

        for partner in partners:
            self.assertEqual(
                strength_maps[partner.id], partner._get_relation_strength_map()
            )
        self.assertEqual(strength_maps[self.stranger.id], {})

    def test_a_recordset_strength_walk_costs_one_query_per_degree(self):
        relations = self.env["res.partner.relation"]
        original_search = type(relations).search
        calls = []

        def counting_search(records, *args, **kwargs):
            calls.append(records._name)
            return original_search(records, *args, **kwargs)

        self.patch(type(relations), "search", counting_search)
        (self.juan | self.maria | self.pedro | self.lucia)._get_relation_strength_maps(
            max_degree=3
        )

        self.assertEqual(len(calls), 3)
