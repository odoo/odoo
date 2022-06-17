#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "../../../")))

import odoo
import odoo.modules.graph

if __name__ == "__main__":

    def add_node(graph, name, depends=False, priority=0):
        if isinstance(depends, str):
            depends = [depends]
        graph.add_node(
            name,
            {
                "depends": depends or [],
                "soft_depends": [],
                "loading_priority": priority,
            },
        )

    def graph_status(graph):
        TABLE_FMT = "{:<6} {:<6} {:<10} {:<60}"
        print("\n")
        print("Node hierarchy:")
        print("------------------------")
        print(graph)
        print("Final loading order is:")
        print("------------------------")
        print(graph._pprint())

    def test_graph_case_1():
        print("================================================")
        print("Case 1:")
        print("- no priority")

        graph = odoo.modules.graph.Graph()
        add_node(graph, "root")
        add_node(graph, "node_a", "root")
        add_node(graph, "node_b", "root")

        add_node(graph, "node_a1", "node_a")
        add_node(graph, "node_a2", "node_a")

        add_node(graph, "node_c", "node_a2")
        add_node(graph, "node_c1", "node_c")
        add_node(graph, "node_c2", "node_c")
        add_node(graph, "node_c3", "node_c")

        add_node(graph, "node_a3", "node_a")

        add_node(graph, "node_b1", "node_b")
        add_node(graph, "node_b2", "node_b")
        add_node(graph, "node_b3", "node_b")

        add_node(graph, "node_d", "node_b3")
        add_node(graph, "node_d1", "node_d")
        add_node(graph, "node_d2", "node_d")
        add_node(graph, "node_d3", "node_d")

        graph_status(graph)
        return graph

    def test_graph_case_2():
        print("================================================")
        print("Case 2:")
        print("- priority 10 set to Node C2")

        graph = odoo.modules.graph.Graph()
        add_node(graph, "root")
        add_node(graph, "node_a", "root")
        add_node(graph, "node_b", "root")

        add_node(graph, "node_a1", "node_a")
        add_node(graph, "node_a2", "node_a")

        add_node(graph, "node_c", "node_a2")
        add_node(graph, "node_c1", "node_c")
        add_node(graph, "node_c2", "node_c", 10)
        add_node(graph, "node_c3", "node_c")

        add_node(graph, "node_a3", "node_a")

        add_node(graph, "node_b1", "node_b")
        add_node(graph, "node_b2", "node_b")
        add_node(graph, "node_b3", "node_b")

        add_node(graph, "node_d", "node_b3")
        add_node(graph, "node_d1", "node_d")
        add_node(graph, "node_d2", "node_d")
        add_node(graph, "node_d3", "node_d")

        graph_status(graph)
        return graph

    def test_graph_case_3():
        print("================================================")
        print("Case 3:")
        print("- priority 10 set to Node C2")
        print("- priority 11 set to Node D2")

        graph = odoo.modules.graph.Graph()
        add_node(graph, "root")
        add_node(graph, "node_a", "root")
        add_node(graph, "node_b", "root")

        add_node(graph, "node_a1", "node_a")
        add_node(graph, "node_a2", "node_a")

        add_node(graph, "node_c", "node_a2")
        add_node(graph, "node_c1", "node_c")
        add_node(graph, "node_c2", "node_c", 10)
        add_node(graph, "node_c3", "node_c")

        add_node(graph, "node_a3", "node_a")

        add_node(graph, "node_b1", "node_b")
        add_node(graph, "node_b2", "node_b")
        add_node(graph, "node_b3", "node_b")

        add_node(graph, "node_d", "node_b3")
        add_node(graph, "node_d1", "node_d")
        add_node(graph, "node_d2", "node_d", 11)
        add_node(graph, "node_d3", "node_d")

        graph_status(graph)
        return graph

    def test_graph_case_4():
        print("================================================")
        print("Case 4:")
        print("- priority 10 set to Node C2")
        print("- priority 8  set to Node D2")
        print("- priority 4  set to Node D")

        graph = odoo.modules.graph.Graph()
        add_node(graph, "root")
        add_node(graph, "node_a", "root")
        add_node(graph, "node_b", "root", -100)

        add_node(graph, "node_a1", "node_a")
        add_node(graph, "node_a2", "node_a")

        add_node(graph, "node_c", "node_a2")
        add_node(graph, "node_c1", "node_c")
        add_node(graph, "node_c2", "node_c", 10)
        add_node(graph, "node_c3", "node_c")

        add_node(graph, "node_a3", "node_a")

        add_node(graph, "node_b1", "node_b")
        add_node(graph, "node_b2", "node_b")
        add_node(graph, "node_b3", "node_b")

        add_node(graph, "node_d", "node_b3", 4)
        add_node(graph, "node_d1", "node_d")
        add_node(graph, "node_d2", "node_d", 8)
        add_node(graph, "node_d3", "node_d")

        graph_status(graph)
        return graph

    def test_graph_case_5():
        print("================================================")
        print("Case 5:")
        print("- no priority")

        graph = odoo.modules.graph.Graph()
        add_node(graph, "base")
        add_node(graph, "uom", "base")
        add_node(graph, "web", "base")
        add_node(graph, "auth_totp", "web")
        add_node(graph, "barcodes", "web")
        add_node(graph, "base_import", "web")
        add_node(graph, "base_setup", "web")
        add_node(graph, "bus", "web")
        add_node(graph, "http_routing", "web")
        add_node(graph, "resource", "web")
        add_node(graph, "web_editor", "web")
        add_node(graph, "web_unsplash", ["base_setup", "web_editor"])
        add_node(graph, "web_tour", "web")
        add_node(graph, "web_kanban_gauge", "web")
        add_node(graph, "mail", ["base", "base_setup", "bus", "web_tour"])
        add_node(graph, "auth_signup", ["base_setup", "mail", "web"])
        add_node(
            graph,
            "portal",
            ["web", "web_editor", "http_routing", "mail", "auth_signup"],
        )
        add_node(graph, "auth_totp_portal", ["portal", "auth_totp"])
        add_node(graph, "digest", ["mail", "portal", "resource"])
        add_node(graph, "stock", ["product", "barcodes", "digest"], )
        add_node(graph, "product", ["base", "mail", "uom"],10)

        graph_status(graph)
        return graph

    test_graph_case_1()
    test_graph_case_2()
    test_graph_case_3()
    test_graph_case_4()
    test_graph_case_5()
