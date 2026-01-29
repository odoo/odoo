/** @odoo-module */

import { registry } from "@web/core/registry";
import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData, target;

const serviceRegistry = registry.category("services");

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(() => {
        serviceRegistry.add("mail.thread", { start() {} });
        serverData = {
            models: {
                "hr.employee": {
                    fields: {
                        parent_id: { string: "Manager", type: "many2one", relation: "hr.employee" },
                        name: { string: "Name" },
                        child_ids: {
                            string: "Subordinates",
                            type: "one2many",
                            relation: "hr.employee",
                            relation_field: "parent_id",
                        },
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
                    <hierarchy child_field="child_ids" js_class="hr_employee_hierarchy">
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

    QUnit.module("HrEmployeeHierarchy View");

    QUnit.test("load hierarchy view", async function (assert) {
        await makeView({
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });

        assert.containsOnce(target, ".o_hierarchy_view");
        assert.containsN(target, ".o_hierarchy_button_add", 2);
        assert.containsOnce(target, ".o_hierarchy_view .o_hierarchy_renderer");
        assert.containsOnce(
            target,
            ".o_hierarchy_view .o_hierarchy_renderer > .o_hierarchy_container"
        );
        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsOnce(target, ".o_hierarchy_separator");
        assert.containsN(target, ".o_hierarchy_line_part", 2);
        assert.containsOnce(target, ".o_hierarchy_line_left");
        assert.containsOnce(target, ".o_hierarchy_line_right");
        assert.containsN(target, ".o_hierarchy_node_container", 3);
        assert.containsN(target, ".o_hierarchy_node", 3);
        assert.containsN(target, ".o_hierarchy_node_button", 2);
        assert.containsOnce(target, ".o_hierarchy_node_button.btn-primary");
        assert.containsNone(
            target,
            ".o_hierarchy_node_button.btn-primary.d-grid",
            "'d-grid' class has been removed in that js_class"
        );
        assert.containsNone(
            target,
            ".o_hierarchy_node_button.btn-primary.rounded-0",
            "'d-grid' class has been removed in that js_class"
        );
        assert.containsNone(
            target,
            ".o_hierarchy_node_button.btn-primary .o_hierarchy_icon",
            "the icon has been replaced in that js_class"
        );
        assert.containsOnce(
            target,
            ".o_hierarchy_node_button.btn-primary .fa-caret-right",
            "the icon has been replaced in that js_class"
        );
        assert.strictEqual(
            target.querySelector(".o_hierarchy_node_button.btn-primary").textContent.trim(),
            "1 people"
        );
        // check nodes in each row
        const row = target.querySelector(".o_hierarchy_row");
        assert.containsOnce(row, ".o_hierarchy_node");
        assert.strictEqual(row.querySelector(".o_hierarchy_node_content").textContent, "Albert");
        assert.containsOnce(target, ".o_hierarchy_node_button.btn-secondary");
        assert.containsOnce(target, ".o_hierarchy_node_button.btn-secondary .fa-caret-down");
        assert.strictEqual(
            target.querySelector(".o_hierarchy_node_button.btn-secondary").textContent.trim(),
            "2 people"
        );
    });

    QUnit.test(
        "display the avatar of the parent when there is more than one node in the same row of the parent",
        async function (assert) {
            await makeView({
                type: "hierarchy",
                resModel: "hr.employee",
                serverData,
            });

            assert.containsN(target, ".o_hierarchy_row", 2);
            assert.containsOnce(target, ".o_hierarchy_node_button.btn-primary");
            await click(target, ".o_hierarchy_node_button.btn-primary");
            assert.containsN(target, ".o_hierarchy_row", 3);
            assert.containsN(target, ".o_hierarchy_node", 4);
            assert.containsN(target, ".o_hierarchy_separator", 2);
            assert.containsOnce(target, ".o_hierarchy_parent_node_container .o_avatar");
            assert.strictEqual(target.querySelector(".o_avatar").textContent, "Josephine");
        }
    );

    QUnit.test("hierarchy with a self manager employee", async function(assert) {
        serverData = {
            ...serverData,
            models: {...serverData["models"], "hr.employee":{
                ...serverData["models"]["hr.employee"],
                records: [{ id: 1, name: "Albert", parent_id: 1, child_ids: [1] }]
            }}
        }
        await makeView({
            context:{
                hierarchy_res_id: 1,
            },
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });

        assert.containsN(target, ".o_hierarchy_row", 2);
        assert.containsN(target, ".o_hierarchy_node_button.btn-secondary", 1);
        assert.containsN(target, ".o_hierarchy_node", 2);
        await click(target, ".o_hierarchy_node_button.btn-secondary");
        assert.containsN(target, ".o_hierarchy_row", 1);
        assert.containsN(target, ".o_hierarchy_node", 1);
    });

    QUnit.test("hierarchy with a cycle", async function(assert) {
        serverData = {
            ...serverData,
            models: {...serverData["models"], "hr.employee":{
                ...serverData["models"]["hr.employee"],
                records: [
                    { id: 1, name: "Albert", parent_id: 4, child_ids: [2, 3] },
                    { id: 2, name: "Georges", parent_id: 1, child_ids: [] },
                    { id: 3, name: "Josephine", parent_id: 1, child_ids: [4] },
                    { id: 4, name: "Louis", parent_id: 3, child_ids: [1] },
                ],
            }}
        }
        await makeView({
            context:{
                hierarchy_res_id: 1,
            },
            type: "hierarchy",
            resModel: "hr.employee",
            serverData,
        });

        assert.containsN(target, ".o_hierarchy_row", 4);
        assert.containsN(target, ".o_hierarchy_node", 5);
        assert.containsN(target, ".o_hierarchy_row:nth-of-type(8) .o_hierarchy_node", 1);
        // check that the node in the cycle cannot be expanded
        assert.containsN(target, ".o_hierarchy_row:nth-of-type(8) .o_hierarchy_node_button", 0);
        assert.strictEqual(target.querySelector(".o_hierarchy_row:nth-of-type(1) .o_hierarchy_node_content").textContent, "AlbertLouis");
        await click(target, ".o_hierarchy_row:nth-of-type(1) .btn-secondary");
        await click(target, ".o_hierarchy_row:nth-of-type(1) .btn-primary");
        await click(target, ".o_hierarchy_row:nth-of-type(3) .btn-primary");
        await click(target, ".o_hierarchy_row:nth-of-type(6) .btn-primary");
        // check the root of the tree is still Albert
        assert.strictEqual(target.querySelector(".o_hierarchy_row:nth-of-type(1) .o_hierarchy_node_content").textContent, "AlbertLouis");
        assert.strictEqual(target.querySelector(".o_hierarchy_row:nth-of-type(8) .o_hierarchy_node_content").textContent, "AlbertLouis");
    });
});
