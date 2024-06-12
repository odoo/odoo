/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import {
    click,
    drag,
    dragAndDrop,
    getFixture,
    getNodesTextContent,
    mockAnimationFrame,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData, target;

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                "hr.employee": {
                    fields: {
                        parent_id: { string: "Manager", type: "many2one", relation: "hr.employee" },
                        name: { string: "Name" },
                        child_ids: { string: "Subordinates", type: "one2many", relation: "hr.employee", relation_field: "parent_id" },
                    },
                    records: [
                        { id: 1, name: "Albert", parent_id: false, child_ids: [2, 3] },
                        { id: 2, name: "Georges", parent_id: 1, child_ids: [] },
                        { id: 3, name: "Josephine", parent_id: 1, child_ids: [4] },
                        { id: 4, name: "Louis", parent_id: 3, child_ids: [] },
                    ],
                },
            },
            views: {
                "hr.employee,false,hierarchy": `
                    <hierarchy>
                        <templates>
                            <t t-name="hierarchy-box">
                                <div class="o_hierarchy_node_header">
                                    <field name="name"/>
                                </div>
                                <div class="o_hierarchy_node_body">
                                    <field name="parent_id"/>
                                </div>
                            </t>
                        </templates>
                    </hierarchy>
                `,
                "hr.employee,1,hierarchy": `
                    <hierarchy child_field="child_ids">
                        <field name="child_ids" invisible="1"/>
                        <templates>
                            <t t-name="hierarchy-box">
                                <div class="o_hierarchy_node_header">
                                    <field name="name"/>
                                </div>
                                <div class="o_hierarchy_node_body">
                                    <field name="parent_id"/>
                                </div>
                            </t>
                        </templates>
                    </hierarchy>
                `,
                "hr.employee,false,form": `
                    <form>
                        <sheet>
                            <group>
                                <field name="name"/>
                                <field name="parent_id"/>
                            </group>
                        </sheet>
                    </form>
                `,
            },
        };
        setupViewRegistries();
        target = getFixture();
    });

    QUnit.module("Hierarchy View");

    QUnit.test("load hierarchy view", async function (assert) {
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });

        assert.containsOnce(target, ".o_hierarchy_view");
        assert.containsN(target, ".o_hierarchy_button_add", 2);
        assert.containsOnce(target, ".o_hierarchy_view .o_hierarchy_renderer");
        assert.containsOnce(target, ".o_hierarchy_view .o_hierarchy_renderer > .o_hierarchy_container");
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsOnce(target, ".o_hierarchy_separator");
        assert.containsN(target, ".o_hierarchy_line_part", 2);
        assert.containsOnce(target, ".o_hierarchy_line_left");
        assert.containsOnce(target, ".o_hierarchy_line_right");
        assert.containsN(target, ".o_hierarchy_node_container", 3);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.containsN(target, ".o_hierarchy_node_button", 2);
        assert.containsOnce(target, ".o_hierarchy_node_button.btn-primary");
        assert.containsOnce(target, ".o_hierarchy_node_button.btn-primary.d-grid");
        assert.containsOnce(target, ".o_hierarchy_node_button.btn-primary.rounded-0");
        assert.containsOnce(target, ".o_hierarchy_node_button.btn-primary .o_hierarchy_icon");
        assert.strictEqual(target.querySelector(".o_hierarchy_node_button.btn-primary").textContent.trim(), "Unfold 1");
        // check nodes in each row
        const row = target.querySelector(".o_hierarchy_row");
        assert.containsOnce(row, ".o_hierarchy_node");
        assert.strictEqual(row.querySelector(".o_hierarchy_node_content").textContent, "Albert");
        assert.containsOnce(target, ".o_hierarchy_node_button.btn-secondary");
        assert.strictEqual(target.querySelector(".o_hierarchy_node_button.btn-secondary").textContent.trim(), "Fold");
    });

    QUnit.test("display child nodes", async function (assert) {
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
            async mockRPC(route, args) {
                if (args.method === "read") {
                    assert.step("get child data");
                } else if (args.method === "read_group") {
                    assert.step("fetch descendants");
                }
            }
        });

        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node_button", 2);
        assert.containsOnce(target, ".o_hierarchy_node_button.btn-secondary");
        assert.containsOnce(target, ".o_hierarchy_node_button.btn-primary");
        await click(target,  ".o_hierarchy_node_button.btn-primary");
        assert.containsN(target, ".o_hierarchy_row", 3);
        assert.containsN(target, ".o_hierarchy_separator", 2);
        assert.containsN(target, ".o_hierarchy_line_part", 4);
        assert.containsN(target, ".o_hierarchy_line_left", 2);
        assert.containsN(target, ".o_hierarchy_line_right", 2);
        assert.containsN(target, ".o_hierarchy_node_container", 4);
        assert.containsN(target, ".o_hierarchy_node", 4);
        assert.containsN(target, ".o_hierarchy_node_button", 2);
        assert.containsNone(target, ".o_hierarchy_node_button.btn-primary");
        assert.containsN(target, ".o_hierarchy_node_button.btn-secondary", 2);
        assert.strictEqual(target.querySelector(".o_hierarchy_node_button.btn-secondary").textContent.trim(), "Fold");
        // check nodes in each row
        const rows = target.querySelectorAll(".o_hierarchy_row");
        let row = rows[0];
        assert.containsOnce(row, ".o_hierarchy_node");
        assert.strictEqual(row.querySelector(".o_hierarchy_node_content").textContent, "Albert");
        row = rows[1];
        assert.containsN(row, ".o_hierarchy_node", 2);
        assert.deepEqual(
            getNodesTextContent(row.querySelectorAll(".o_hierarchy_node_content")),
            [ // Name + Parent name
                "GeorgesAlbert",
                "JosephineAlbert",
            ],
        );
        row = rows[2];
        assert.containsOnce(row, ".o_hierarchy_node");
        assert.strictEqual(row.querySelector(".o_hierarchy_node_content").textContent, "LouisJosephine");
        assert.verifySteps([
            "get child data",
            "fetch descendants",
        ]);
    });

    QUnit.test("display child nodes with child_field set on the view", async function (assert) {
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
            viewId: 1,
            async mockRPC(route, args) {
                if (args.method === "read") {
                    assert.step("get child data with descendants");
                }
            }
        });

        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node_button", 2);
        assert.containsOnce(target, ".o_hierarchy_node_button.btn-secondary");
        assert.containsOnce(target, ".o_hierarchy_node_button.btn-primary");
        await click(target,  ".o_hierarchy_node_button.btn-primary");
        assert.containsN(target, ".o_hierarchy_row", 3);
        assert.containsN(target, ".o_hierarchy_separator", 2);
        assert.containsN(target, ".o_hierarchy_line_part", 4);
        assert.containsN(target, ".o_hierarchy_line_left", 2);
        assert.containsN(target, ".o_hierarchy_line_right", 2);
        assert.containsN(target, ".o_hierarchy_node_container", 4);
        assert.containsN(target, ".o_hierarchy_node", 4);
        assert.containsN(target, ".o_hierarchy_node_button", 2);
        assert.containsNone(target, ".o_hierarchy_node_button.btn-primary");
        assert.containsN(target, ".o_hierarchy_node_button.btn-secondary", 2);
        assert.verifySteps([
            "get child data with descendants",
        ]);
    });

    QUnit.test("collapse child nodes", async function (assert) {
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });

        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsOnce(target, ".o_hierarchy_separator");
        assert.containsN(target, ".o_hierarchy_line_part", 2);
        assert.containsOnce(target, ".o_hierarchy_line_left");
        assert.containsOnce(target, ".o_hierarchy_line_right");
        assert.containsN(target, ".o_hierarchy_node_container", 3);
        assert.containsN(target, ".o_hierarchy_node", 3);
        await click(target, ".o_hierarchy_node_button.btn-secondary");
        assert.containsOnce(target, ".o_hierarchy_row");
        assert.containsNone(target, ".o_hierarchy_separator");
        assert.containsNone(target, ".o_hierarchy_line_part", 2);
        assert.containsNone(target, ".o_hierarchy_line_left");
        assert.containsNone(target, ".o_hierarchy_line_right");
        assert.containsOnce(target, ".o_hierarchy_node_container");
        assert.containsOnce(target, ".o_hierarchy_node");
        assert.containsNone(target, ".o_hierarchy_node_button.btn-secondary");
        assert.containsOnce(target, ".o_hierarchy_node_button");
        assert.containsOnce(target, ".o_hierarchy_node_container:not(.o_hierarchy_node_button)");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_hierarchy_row .o_hierarchy_node_content")), ["Albert"]);
    });

    QUnit.test("display the parent above the line when many records on the parent row", async function (assert) {
        serverData.models["hr.employee"].records.push({
            name: "Alfred",
            parent_id: false,
            child_ids: [],
        })
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });

        assert.containsOnce(target, ".o_hierarchy_row");
        assert.containsNone(target, ".o_hierarchy_separator");
        assert.containsN(target, ".o_hierarchy_node", 2);
        assert.containsOnce(target, ".o_hierarchy_node_button.btn-primary");
        await click(target, ".o_hierarchy_node_button.btn-primary");
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsOnce(target, ".o_hierarchy_separator");
        assert.containsOnce(target, ".o_hierarchy_line_left");
        assert.containsOnce(target, ".o_hierarchy_line_right");
        assert.containsOnce(target, ".o_hierarchy_parent_node_container");
        assert.strictEqual(target.querySelector(".o_hierarchy_parent_node_container").textContent, "Albert");
    });

    QUnit.test("search record in hierarchy view", async function (assert) {
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
            domain: [["id", "=", 4]], // simulate a search
        });

        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 2);
        assert.containsN(target, ".o_hierarchy_separator", 1);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["JosephineAlbert", "LouisJosephine"],
        );
    });

    QUnit.test("search record in hierarchy view with child field name defined in the arch", async function (assert) {
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            viewId: 1,
            serverData,
            domain: [["id", "=", 4]], // simulate a search
        });

        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 2);
        assert.containsN(target, ".o_hierarchy_separator", 1);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["JosephineAlbert", "LouisJosephine"],
        );
    });

    QUnit.test("fetch parent record", async function (assert) {
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
            domain: [["id", "=", 4]], // simulate a search
        });

        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 2);
        assert.containsN(target, ".o_hierarchy_separator", 1);
        let rows = target.querySelectorAll(".o_hierarchy_row");
        let row = rows[0];
        assert.containsOnce(row, ".o_hierarchy_node");
        assert.strictEqual(row.querySelector(".o_hierarchy_node_content").textContent, "JosephineAlbert");
        row = rows[1];
        assert.containsOnce(row, ".o_hierarchy_node");
        assert.strictEqual(row.querySelector(".o_hierarchy_node_content").textContent, "LouisJosephine");
        assert.containsOnce(
            target,
            ".o_hierarchy_node_container button .fa-chevron-up",
            "Button to fetch the parent node should be visible on the first node displayed in the view."
        );
        await click(target, ".o_hierarchy_node_container button .fa-chevron-up");
        assert.containsN(target, ".o_hierarchy_row", 3);
        assert.containsN(target, ".o_hierarchy_node", 4);
        assert.containsN(target, ".o_hierarchy_separator", 2);
        rows = target.querySelectorAll(".o_hierarchy_row");
        row = rows[0];
        assert.containsOnce(row, ".o_hierarchy_node");
        assert.strictEqual(row.querySelector(".o_hierarchy_node_content").textContent, "Albert");
        row = rows[1];
        assert.containsN(row, ".o_hierarchy_node", 2);
        assert.deepEqual(
            getNodesTextContent(row.querySelectorAll(".o_hierarchy_node_content")),
            ["GeorgesAlbert", "JosephineAlbert"],
        );
        row = rows[2];
        assert.containsOnce(row, ".o_hierarchy_node");
        assert.strictEqual(row.querySelector(".o_hierarchy_node_content").textContent, "LouisJosephine");
    });

    QUnit.test("fetch parent when there are many records without the same parent in the same row", async function (assert) {
        serverData.models["hr.employee"].records.push(
            { id: 5, name: "Lisa", parent_id: 2, child_ids: []},
        );
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
            domain: [["name", "ilike", "l"]], // simulate a search
        });
        assert.containsOnce(target, ".o_hierarchy_row");
        assert.containsN(target, ".o_hierarchy_node_container", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            [
                "LisaGeorges", "LouisJosephine", "Albert",
            ],
        );
        assert.containsN(target, ".o_hierarchy_node_container button .fa-chevron-up", 2);
        const firstNode = target.querySelector(".o_hierarchy_node_container");
        await click(firstNode, ".o_hierarchy_node_container button .fa-chevron-up");
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 2);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            [
                "GeorgesAlbert", "LisaGeorges",
            ],
        );
        assert.containsOnce(target, ".o_hierarchy_node_container button .fa-chevron-up");
        await click(target, ".o_hierarchy_node_container button .fa-chevron-up");
        assert.containsN(target, ".o_hierarchy_row", 3);
        assert.containsN(target, ".o_hierarchy_node", 4);
    });

    QUnit.test("fetch parent when parent record is in the same row", async function (assert) {
        serverData.models["hr.employee"].records.push(
            { id: 5, name: "Lisa", parent_id: 2, child_ids: []},
        );
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
            domain: [["id", "in", [1, 2, 3, 4, 5]]], // simulate a search
        });
        assert.containsOnce(target, ".o_hierarchy_row");
        assert.containsN(target, ".o_hierarchy_node_container", 5);
        assert.containsN(target, ".o_hierarchy_node_container button .fa-chevron-up", 4);
        const firstNodeWithParentBtn = target.querySelector(".o_hierarchy_node_container:has(button .fa-chevron-up)");
        await click(firstNodeWithParentBtn, ".o_hierarchy_node_container button .fa-chevron-up");
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            [
                "Albert", "GeorgesAlbert", "JosephineAlbert",
            ],
        );
    });

    QUnit.test("fetch parent of node with children displayed", async function (assert) {
        serverData.models["hr.employee"].records.push(
            { id: 5, name: "Lisa", parent_id: 2, child_ids: []},
        );
        serverData.models["hr.employee"].records.find((rec) => rec.id === 2).child_ids.push(5);
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
            domain: [["id", "in", [1, 2, 3, 4, 5]]], // simulate a search
        });
        assert.containsOnce(target, ".o_hierarchy_row");
        assert.containsN(target, ".o_hierarchy_node_container", 5);
        assert.containsN(target, ".o_hierarchy_node_container button .fa-chevron-up", 4);
        const georgesNode = target.querySelector(".o_hierarchy_node_container:has(button[name=hierarchy_search_parent_node])");
        assert.strictEqual(georgesNode.querySelector(".o_hierarchy_node_content").textContent, "GeorgesAlbert");
        await click(georgesNode, "button[name=hierarchy_search_subsidiaries]");
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 5);
        const rows = target.querySelectorAll(".o_hierarchy_row");
        let row = rows[0];
        assert.containsN(row, ".o_hierarchy_node", 4);
        assert.deepEqual(
            getNodesTextContent(row.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert", "LouisJosephine"],
        );
        row = rows[1];
        assert.containsN(row, ".o_hierarchy_node", 1);
        assert.strictEqual(row.querySelector(".o_hierarchy_node_content").textContent, "LisaGeorges");
        const firstNodeWithParentBtn = target.querySelector(".o_hierarchy_node_container:has(button .fa-chevron-up)");
        await click(firstNodeWithParentBtn, ".o_hierarchy_node_container button .fa-chevron-up");
        assert.containsN(target, ".o_hierarchy_row", 3);
        assert.containsN(target, ".o_hierarchy_node", 4);
    });

    QUnit.test("drag and drop is disabled by default", async function (assert) {
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert"],
        );

        const nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        const georgesNodeContainer = nodeContainers[1];
        assert.strictEqual(georgesNodeContainer.querySelector(".o_hierarchy_node_content").textContent, "GeorgesAlbert");

        await dragAndDrop(
            georgesNodeContainer.querySelector(".o_hierarchy_node"),
            ".o_hierarchy_row:first-child"
        );

        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert"],
        );
    });

    QUnit.test("drag and drop record on another row", async function (assert) {
        serverData.views["hr.employee,false,hierarchy"] = serverData.views["hr.employee,false,hierarchy"].replace("<hierarchy>", "<hierarchy draggable='1'>");
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert"],
        );

        const nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        const georgesNodeContainer = nodeContainers[1];
        assert.strictEqual(georgesNodeContainer.querySelector(".o_hierarchy_node_content").textContent, "GeorgesAlbert");

        await dragAndDrop(
            georgesNodeContainer.querySelector(".o_hierarchy_node"),
            ".o_hierarchy_row:first-child"
        );

        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "Georges", "JosephineAlbert"],
            "Georges should no longer have a manager"
        );
    });

    QUnit.test("drag and drop record on sibling node", async function (assert) {
        serverData.views["hr.employee,false,hierarchy"] = serverData.views["hr.employee,false,hierarchy"].replace("<hierarchy>", "<hierarchy draggable='1'>");
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert"],
        );

        const nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        const georgesNodeContainer = nodeContainers[1];
        const josephineNodeContainer = nodeContainers[2];
        assert.strictEqual(georgesNodeContainer.querySelector(".o_hierarchy_node_content").textContent, "GeorgesAlbert");
        assert.strictEqual(josephineNodeContainer.querySelector(".o_hierarchy_node_content").textContent, "JosephineAlbert");

        await dragAndDrop(
            georgesNodeContainer.querySelector(".o_hierarchy_node"),
            josephineNodeContainer,
        );

        assert.containsN(target, ".o_hierarchy_row", 3);
        assert.containsN(target, ".o_hierarchy_node", 4);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "JosephineAlbert", "LouisJosephine", "GeorgesJosephine"],
            "Georges should have Josephine as manager"
        );
    });

    QUnit.test("drag and drop record on node of another tree", async function (assert) {
        serverData.views["hr.employee,1,hierarchy"] = serverData.views[
            "hr.employee,1,hierarchy"
        ].replace(`<hierarchy child_field="child_ids">`, `<hierarchy child_field="child_ids" draggable="1">`);
        serverData.models["hr.employee"].records = [
            { id: 1, name: "A", parent_id: false, child_ids: [3, 4] },
            { id: 2, name: "B", parent_id: false, child_ids: [] },
            { id: 3, name: "C", parent_id: 1, child_ids: [5] },
            { id: 4, name: "D", parent_id: 1, child_ids: [] },
            { id: 5, name: "E", parent_id: 3, child_ids: [] },
        ];
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
            viewId: 1,
        });

        assert.containsN(target, ".o_hierarchy_row", 1);
        await click(target, ".o_hierarchy_node_button.btn-primary");
        assert.containsN(target, ".o_hierarchy_row", 2);
        await click(target, ".o_hierarchy_node_button.btn-primary");
        assert.containsN(target, ".o_hierarchy_row", 3);
        let rowsContent = target.querySelectorAll(".o_hierarchy_row .o_hierarchy_node_content");
        assert.deepEqual(getNodesTextContent(rowsContent), ["A", "B", "CA", "DA", "EC"]);

        let nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        const bNode = nodeContainers[1];
        const dNode = nodeContainers[3];
        assert.strictEqual(bNode.querySelector(".o_hierarchy_node_content").textContent, "B");
        assert.strictEqual(dNode.querySelector(".o_hierarchy_node_content").textContent, "DA");

        await dragAndDrop(
            dNode.querySelector(".o_hierarchy_node"),
            bNode,
        );

        assert.containsN(target, ".o_hierarchy_row", 2);
        rowsContent = target.querySelectorAll(".o_hierarchy_row .o_hierarchy_node_content");
        assert.deepEqual(getNodesTextContent(rowsContent), ["A", "B", "DB"]);

        nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        const aNode = nodeContainers[0];
        assert.strictEqual(aNode.querySelector(".o_hierarchy_node_content").textContent, "A");

        await click(aNode, ".o_hierarchy_node_button.btn-primary");

        nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        const cNode = nodeContainers[2];
        assert.strictEqual(cNode.querySelector(".o_hierarchy_node_content").textContent, "CA");

        await click(cNode, ".o_hierarchy_node_button.btn-primary");

        rowsContent = target.querySelectorAll(".o_hierarchy_row .o_hierarchy_node_content");
        assert.deepEqual(
            getNodesTextContent(rowsContent),
            ["A", "B", "CA", "EC"],
            "Nodes that were folded as a result of the drop operation should all still be unfoldable"
        );
    });

    QUnit.test("drag and drop node unfolded on first row", async function (assert) {
        serverData.views["hr.employee,false,hierarchy"] = serverData.views["hr.employee,false,hierarchy"].replace("<hierarchy>", "<hierarchy draggable='1'>");
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert"],
        );

        let nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        const josephineNodeContainer = nodeContainers[2];
        assert.strictEqual(josephineNodeContainer.querySelector(".o_hierarchy_node_content").textContent, "JosephineAlbert");
        await click(josephineNodeContainer, "button[name='hierarchy_search_subsidiaries']");

        await dragAndDrop(
            josephineNodeContainer.querySelector(".o_hierarchy_node"),
            ".o_hierarchy_row:first-child"
        );

        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "Josephine", "LouisJosephine"],
            "Georges should have Josephine as manager"
        );

        nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        const louisNodeContainer = nodeContainers[2];
        assert.strictEqual(
            louisNodeContainer.querySelector(".o_hierarchy_node_content").textContent,
            "LouisJosephine"
        );

        await dragAndDrop(
            louisNodeContainer.querySelector(".o_hierarchy_node"),
            ".o_hierarchy_row:first-child"
        );

        assert.containsN(target, ".o_hierarchy_row", 1);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "Josephine", "Louis"],
            "Louis should still be draggable after being dragged along with Josephine"
        );
    });

    QUnit.test("drag and drop node when other node is unfolded on first row", async function (assert) {
        serverData.views["hr.employee,false,hierarchy"] = serverData.views["hr.employee,false,hierarchy"].replace("<hierarchy>", "<hierarchy draggable='1'>");
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert"],
        );

        const nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        const georgesNodeContainer = nodeContainers[1];
        const josephineNodeContainer = nodeContainers[2];
        assert.strictEqual(georgesNodeContainer.querySelector(".o_hierarchy_node_content").textContent, "GeorgesAlbert");
        assert.strictEqual(josephineNodeContainer.querySelector(".o_hierarchy_node_content").textContent, "JosephineAlbert");
        await click(josephineNodeContainer, "button[name='hierarchy_search_subsidiaries']");

        await dragAndDrop(
            georgesNodeContainer.querySelector(".o_hierarchy_node"),
            ".o_hierarchy_row:first-child"
        );

        assert.containsN(target, ".o_hierarchy_row", 3);
        assert.containsN(target, ".o_hierarchy_node", 4);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "Georges", "JosephineAlbert", "LouisJosephine"],
            "Georges should no longer have a manager"
        );
    });

    QUnit.test("drag and drop node unfolded on another row", async function (assert) {
        serverData.views["hr.employee,false,hierarchy"] = serverData.views[
            "hr.employee,false,hierarchy"
        ].replace("<hierarchy>", "<hierarchy draggable='1'>");
        serverData.models["hr.employee"].records = [
            { id: 1, name: "Albert", parent_id: false, child_ids: [2] },
            { id: 2, name: "Georges", parent_id: 1, child_ids: [3] },
            { id: 3, name: "Josephine", parent_id: 2, child_ids: [4] },
            { id: 4, name: "Louis", parent_id: 3, child_ids: [] },
            { id: 5, name: "Kelly", parent_id: 2, child_ids: [] },
        ];
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 2);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert"]
        );

        let nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        const georgeNodeContainer = nodeContainers[1];
        assert.strictEqual(
            georgeNodeContainer.querySelector(".o_hierarchy_node_content").textContent,
            "GeorgesAlbert"
        );
        await click(georgeNodeContainer, "button[name='hierarchy_search_subsidiaries']");

        nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        let josephineNodeContainer = nodeContainers[2];
        assert.strictEqual(
            josephineNodeContainer.querySelector(".o_hierarchy_node_content").textContent,
            "JosephineGeorges"
        );
        await click(josephineNodeContainer, "button[name='hierarchy_search_subsidiaries']");

        nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        josephineNodeContainer = nodeContainers[2];
        assert.strictEqual(
            josephineNodeContainer.querySelector(".o_hierarchy_node_content").textContent,
            "JosephineGeorges"
        );
        let louisNodeContainer = nodeContainers[4];
        assert.strictEqual(
            louisNodeContainer.querySelector(".o_hierarchy_node_content").textContent,
            "LouisJosephine"
        );
        assert.containsN(target, ".o_hierarchy_row", 4);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineGeorges", "KellyGeorges", "LouisJosephine"],
            "Kelly should be displayed"
        );

        await dragAndDrop(
            josephineNodeContainer.querySelector(".o_hierarchy_node"),
            ":nth-child(2 of .o_hierarchy_row)"
        );

        assert.containsN(target, ".o_hierarchy_row", 3);
        assert.containsN(target, ".o_hierarchy_node", 4);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert", "LouisJosephine"],
            "Josephine should have Albert as a manager and Kelly should be hidden"
        );

        nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        louisNodeContainer = nodeContainers[3];
        assert.strictEqual(
            louisNodeContainer.querySelector(".o_hierarchy_node_content").textContent,
            "LouisJosephine"
        );

        await dragAndDrop(
            louisNodeContainer.querySelector(".o_hierarchy_node"),
            ":nth-child(2 of .o_hierarchy_row)"
        );

        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 4);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert", "LouisAlbert"],
            "Louis should still be draggable after being dragged along with Josephine"
        );
    });

    QUnit.test("drag and drop node as a child of a sibling of its parent", async function (assert) {
        serverData.views["hr.employee,1,hierarchy"] = serverData.views[
            "hr.employee,1,hierarchy"
        ].replace(`<hierarchy child_field="child_ids">`, `<hierarchy child_field="child_ids" draggable="1">`);
        serverData.models["hr.employee"].records = [
            { id: 1, name: "A", parent_id: false, child_ids: [2, 3] },
            { id: 2, name: "B", parent_id: 1, child_ids: [4, 5] },
            { id: 3, name: "C", parent_id: 1, child_ids: [] },
            { id: 4, name: "D", parent_id: 2, child_ids: [] },
            { id: 5, name: "E", parent_id: 2, child_ids: [] },
        ];
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
            viewId: 1,
        });
        assert.containsN(target, ".o_hierarchy_row", 2);
        await click(target, ".o_hierarchy_node_button.btn-primary");
        assert.containsN(target, ".o_hierarchy_row", 3);
        let rowsContent = target.querySelectorAll(".o_hierarchy_row .o_hierarchy_node_content");
        assert.deepEqual(getNodesTextContent(rowsContent), ["A", "BA", "CA", "DB", "EB"]);

        let nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        const cNode = nodeContainers[2];
        const eNode = nodeContainers[4];
        assert.strictEqual(cNode.querySelector(".o_hierarchy_node_content").textContent, "CA");
        assert.strictEqual(eNode.querySelector(".o_hierarchy_node_content").textContent, "EB");

        await dragAndDrop(
            eNode.querySelector(".o_hierarchy_node"),
            cNode,
        );
        assert.containsN(target, ".o_hierarchy_row", 3);
        rowsContent = target.querySelectorAll(".o_hierarchy_row .o_hierarchy_node_content");
        assert.deepEqual(
            getNodesTextContent(rowsContent), ["A", "BA", "CA", "EC"],
            "B should be folded and C unfolded"
        );
    });

    QUnit.test("drag node and move it on a row", async function (assert) {
        serverData.views["hr.employee,false,hierarchy"] = serverData.views["hr.employee,false,hierarchy"].replace("<hierarchy>", "<hierarchy draggable='1'>");
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });

        assert.containsN(target, ".o_hierarchy_node", 3);
        const nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        const georgesNodeContainer = nodeContainers[1];
        assert.strictEqual(georgesNodeContainer.querySelector(".o_hierarchy_node_content").textContent, "GeorgesAlbert");

        const { drop, moveTo } = await drag(georgesNodeContainer.querySelector(".o_hierarchy_node"));

        await moveTo(".o_hierarchy_row:first-child");
        assert.hasClass(georgesNodeContainer, "o_hierarchy_dragged");
        assert.hasClass(target.querySelector(".o_hierarchy_row"), "o_hierarchy_hover");

        await drop();
        assert.containsNone(target, ".o_hierarchy_node.o_hierarchy_dragged");
        assert.containsNone(target, ".o_hierarchy_row.o_hierarchy_hover");
    });

    QUnit.test("drag node and move it on another node", async function (assert) {
        serverData.views["hr.employee,false,hierarchy"] = serverData.views["hr.employee,false,hierarchy"].replace("<hierarchy>", "<hierarchy draggable='1'>");
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });

        assert.containsN(target, ".o_hierarchy_node", 3);
        const nodeContainers = target.querySelectorAll(".o_hierarchy_node_container");
        const georgesNodeContainer = nodeContainers[1];
        const josephineNodeContainer = nodeContainers[2];
        assert.strictEqual(georgesNodeContainer.querySelector(".o_hierarchy_node_content").textContent, "GeorgesAlbert");
        assert.strictEqual(josephineNodeContainer.querySelector(".o_hierarchy_node_content").textContent, "JosephineAlbert");

        const { drop, moveTo } = await drag(georgesNodeContainer.querySelector(".o_hierarchy_node"));

        await moveTo(josephineNodeContainer.querySelector(".o_hierarchy_node"));
        assert.hasClass(georgesNodeContainer, "o_hierarchy_dragged");
        assert.hasClass(georgesNodeContainer.querySelector(".o_hierarchy_node"), "shadow");
        assert.hasClass(josephineNodeContainer, "o_hierarchy_hover");

        await drop();
        assert.containsNone(target, ".o_hierarchy_node.o_hierarchy_dragged");
        assert.containsNone(target, ".o_hierarchy_node.o_hierarchy_hover");
        assert.containsNone(target, ".o_hierarchy_node.shadow");
    });

    QUnit.test("drag node to scroll", async function (assert) {
        serverData.views["hr.employee,false,hierarchy"] = serverData.views[
            "hr.employee,false,hierarchy"
        ].replace("<hierarchy>", "<hierarchy draggable='1'>");
        serverData.models["hr.employee"].records = [
            { id: 1, name: "A", parent_id: false, child_ids: [2] },
            { id: 2, name: "B", parent_id: 1, child_ids: [3] },
            { id: 3, name: "C", parent_id: 2, child_ids: [4] },
            { id: 4, name: "D", parent_id: 3, child_ids: [5] },
            { id: 5, name: "E", parent_id: 4, child_ids: [] },
            { id: 6, name: "F", parent_id: false, child_ids: [] },
        ];
        const { advanceFrame } = mockAnimationFrame();
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });

        // Fully open the view
        assert.containsN(target, ".o_hierarchy_row", 1);
        await click(target, ".o_hierarchy_node_button.btn-primary");
        assert.containsN(target, ".o_hierarchy_row", 2);
        await click(target, ".o_hierarchy_node_button.btn-primary");
        assert.containsN(target, ".o_hierarchy_row", 3);
        await click(target, ".o_hierarchy_node_button.btn-primary");
        assert.containsN(target, ".o_hierarchy_row", 4);
        await click(target, ".o_hierarchy_node_button.btn-primary");
        assert.containsN(target, ".o_hierarchy_row", 5);
        const rowsContent = target.querySelectorAll(".o_hierarchy_row .o_hierarchy_node_content");
        assert.deepEqual(getNodesTextContent(rowsContent), ["A", "F", "BA", "CB", "DC", "ED"]);
        await nextTick();

        // Limit the height and enable scrolling
        const content = target.querySelector(".o_content");
        content.setAttribute("style", "min-height:600px;max-height:600px;overflow-y:auto;");
        assert.strictEqual(content.scrollTop, 0);
        assert.strictEqual(content.getBoundingClientRect().height, 600);

        const nodes = [...content.querySelectorAll(".o_hierarchy_node")];
        const fNode = nodes.find((n) => n.textContent === "F");
        const dragActions = await drag(fNode);
        await dragActions.moveTo(".o_hierarchy_row:last-child");
        assert.strictEqual(content.scrollTop, 0);

        await advanceFrame();

        // default speed of 20px per frame
        assert.strictEqual(content.scrollTop, 20);
        assert.containsOnce(target, ".o_hierarchy_node_container.o_hierarchy_dragged");

        // next 100 frames (2000px of scrolling)
        await advanceFrame(100);

        // should be at the end of the content
        assert.strictEqual(content.clientHeight + content.scrollTop, content.scrollHeight);

        await dragActions.moveTo(".o_hierarchy_row:first-child");
        assert.strictEqual(content.clientHeight + content.scrollTop, content.scrollHeight);

        await advanceFrame();

        // default speed of 20px per frame
        assert.strictEqual(content.clientHeight + content.scrollTop, content.scrollHeight - 20);
        assert.containsOnce(target, ".o_hierarchy_node_container.o_hierarchy_dragged");

        // next 100 frames (2000px of scrolling)
        await advanceFrame(100);

        // should be at the top of the content
        assert.strictEqual(content.scrollTop, 0);

        // cancel drag: press "Escape"
        triggerHotkey("Escape");
        await nextTick();

        assert.containsNone(target, ".o_hierarchy_node_container.o_hierarchy_dragged");
    });

    QUnit.test("check default icon is correctly used inside button to display child nodes", async function (assert) {
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });

        assert.containsOnce(target, ".o_hierarchy_node button[name=hierarchy_search_subsidiaries].btn-primary");
        assert.strictEqual(target.querySelector(".o_hierarchy_node button[name=hierarchy_search_subsidiaries].btn-primary").textContent.trim(), "Unfold 1");
        assert.containsOnce(
            target,
            ".o_hierarchy_node button[name=hierarchy_search_subsidiaries] i.fa-share-alt.o_hierarchy_icon",
            "The default icon of the hierarchy view should be displayed inside the button to unfold the node."
        );
    });

    QUnit.test("use other icon used next to Unfold string displayed inside the button", async function (assert) {
        serverData.views["hr.employee,false,hierarchy"] = serverData.views["hr.employee,false,hierarchy"].replace("<hierarchy>", "<hierarchy icon='fa-users'>");
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });

        assert.containsOnce(target, ".o_hierarchy_node button[name=hierarchy_search_subsidiaries].btn-primary");
        assert.strictEqual(target.querySelector(".o_hierarchy_node button[name=hierarchy_search_subsidiaries].btn-primary").textContent.trim(), "Unfold 1");
        assert.containsOnce(
            target,
            ".o_hierarchy_node button[name=hierarchy_search_subsidiaries] i.fa-users",
            "The icon defined in the attribute icon in hierarchy tag should be displayed inside the button to unfold the node instead of the default one."
        );
    });

    QUnit.test("use `hierarchy_res_id` context to load the view at that specific node with its siblings and parent node", async function (assert) {
        serverData.models["hr.employee"].records.push(
            { id: 5, name: "Lisa", parent_id: 3, child_ids: []},
        );
        serverData.models["hr.employee"].records.find((rec) => rec.id === 3).child_ids.push(5);
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
            context: {
                hierarchy_res_id: 5,
            },
        });

        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["JosephineAlbert", "LisaJosephine", "LouisJosephine"]
        );
        assert.containsOnce(target, ".o_hierarchy_node_container button[name=hierarchy_search_parent_node]");
    });

    QUnit.test("cannot set the record dragged as parent", async function (assert) {
        serverData.views["hr.employee,false,hierarchy"] = serverData.views["hr.employee,false,hierarchy"].replace("<hierarchy>", "<hierarchy draggable='1'>");
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
            mockRPC(route, { method, model }) {
                if (method === "write" && model === "hr.employee") {
                    assert.step("setManager");
                }
            },
        });

        patchWithCleanup(browser, {
            setTimeout: () => 1,
        });
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert"]
        );
        const rows = target.querySelectorAll(".o_hierarchy_row");
        await dragAndDrop(
            target.querySelector(".o_hierarchy_node"), // select first node (Albert)
            rows[1]
        );
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert"]
        );
        assert.containsOnce(target, ".o_notification");
        assert.containsOnce(target, ".o_notification.border-danger");

        assert.verifySteps([]);
    });

    QUnit.test("cannot create cyclic", async function (assert) {
        serverData.views["hr.employee,false,hierarchy"] = serverData.views["hr.employee,false,hierarchy"].replace("<hierarchy>", "<hierarchy draggable='1'>");
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
            mockRPC(route, { method, model }) {
                if (method === "write" && model === "hr.employee") {
                    assert.step("setManager");
                }
            },
        });

        patchWithCleanup(browser, {
            setTimeout: () => 1,
        });
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert"]
        );
        let nodes = target.querySelectorAll(".o_hierarchy_node");
        await dragAndDrop(
            nodes[0], // albert node
            nodes[1] // georges node
        );
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert"]
        );
        assert.containsOnce(target, ".o_notification");
        assert.containsOnce(target, ".o_notification.border-danger");

        await click(target, ".o_hierarchy_node_button.btn-primary");
        assert.containsN(target, ".o_hierarchy_row", 3);
        assert.containsN(target, ".o_hierarchy_node", 4);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert", "LouisJosephine"]
        );
        nodes = target.querySelectorAll(".o_hierarchy_node");
        await dragAndDrop(
            nodes[0],
            nodes[3]
        );
        assert.containsN(target, ".o_hierarchy_row", 3);
        assert.containsN(target, ".o_hierarchy_node", 4);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert", "LouisJosephine"]
        );
        assert.containsN(target, ".o_notification", 2);
        assert.containsN(target, ".o_notification.border-danger", 2);

        const rows = target.querySelectorAll(".o_hierarchy_row");
        await dragAndDrop(
            nodes[0],
            rows[2]
        );
        assert.containsN(target, ".o_hierarchy_row", 3);
        assert.containsN(target, ".o_hierarchy_node", 4);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_hierarchy_node_content")),
            ["Albert", "GeorgesAlbert", "JosephineAlbert", "LouisJosephine"]
        );
        assert.containsN(target, ".o_notification", 3);
        assert.containsN(target, ".o_notification.border-danger", 3);

        assert.verifySteps([]);
    });
});
