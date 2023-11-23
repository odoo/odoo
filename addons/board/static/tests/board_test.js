/** @odoo-module **/

import { BoardAction } from "@board/board_action";
import { click, dragAndDrop, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

const serviceRegistry = registry.category("services");

let serverData;
let target;

QUnit.module("Board", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        BoardAction.cache = {};

        serverData = {
            models: {
                board: {
                    fields: {},
                    records: [],
                },
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                        },
                        bar: { string: "Bar", type: "boolean" },
                        int_field: {
                            string: "Integer field",
                            type: "integer",
                            group_operator: "sum",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            foo: "yop",
                            int_field: 3,
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            foo: "lalala",
                            int_field: 5,
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            foo: "abc",
                            int_field: 2,
                        },
                    ],
                },
            },
            views: {
                "partner,100000001,form": "<form/>",
                "partner,100000002,search": "<search/>",
            },
        };
        setupViewRegistries();
    });

    QUnit.module("BoardView");

    QUnit.test("display the no content helper", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column></column>
                    </board>
                </form>`,
        });
        assert.containsOnce(target, ".o_view_nocontent");
    });

    QUnit.test("basic functionality, with one sub action", async function (assert) {
        assert.expect(23);
        serverData.views["partner,4,list"] = '<tree string="Partner"><field name="foo"/></tree>';
        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" view_mode="list" string="ABC" name="51" domain="[['foo', '!=', 'False']]"></action>
                        </column>
                    </board>
                </form>`,
            async mockRPC(route, args) {
                if (route === "/web/action/load") {
                    assert.step("load action");
                    return {
                        res_model: "partner",
                        views: [[4, "list"]],
                    };
                }
                if (route === "/web/dataset/call_kw/partner/web_search_read") {
                    assert.deepEqual(
                        args.kwargs.domain,
                        [["foo", "!=", "False"]],
                        "the domain should be passed"
                    );
                    assert.deepEqual(
                        args.kwargs.context.orderedBy,
                        [
                            {
                                name: "foo",
                                asc: true,
                            },
                        ],
                        "orderedBy is present in the search read when specified on the custom action"
                    );
                }
                if (route === "/web/view/edit_custom") {
                    assert.step("edit custom");
                    return true;
                }
                if (args.method === "get_views" && args.model == "partner") {
                    assert.deepEqual(
                        args.kwargs.views.find((v) => v[1] === "list"),
                        [4, "list"]
                    );
                }
            },
        });

        assert.containsOnce(target, ".o-dashboard-header", "should have rendered a header");
        assert.containsOnce(
            target,
            "div.o-dashboard-layout-2-1",
            "should have rendered a div with layout"
        );
        assert.containsNone(
            target,
            "td.o_list_record_selector",
            "td should not have a list selector"
        );
        assert.containsOnce(
            target,
            "h3 span:contains(ABC)",
            "should have rendered a header with action string"
        );
        assert.containsN(target, "tr.o_data_row", 3, "should have rendered 3 data rows");

        assert.containsOnce(target, ".o-dashboard-action .o_list_view");

        await click(target, "h3 i.fa-window-minimize");

        assert.containsNone(target, ".o-dashboard-action .o_list_view");

        await click(target, "h3 i.fa-window-maximize");

        // content is visible again
        assert.containsOnce(target, ".o-dashboard-action .o_list_view");
        assert.verifySteps(["load action", "edit custom", "edit custom"]);

        // header should have dropdown with correct image
        assert.containsOnce(
            target,
            ".o-dashboard-header .dropdown img[data-src='/board/static/img/layout_2-1.png']"
        );

        // change layout to 1-1
        await click(target, ".o-dashboard-header .dropdown img");
        await click(target, ".o-dashboard-header .dropdown-item:nth-child(2)");
        assert.containsOnce(
            target,
            ".o-dashboard-header .dropdown img[data-src='/board/static/img/layout_1-1.png']"
        );
        assert.containsOnce(
            target,
            "div.o-dashboard-layout-1-1",
            "should have rendered a div with layout"
        );

        assert.verifySteps(["edit custom"]);
    });

    QUnit.test("views in the dashboard do not have a control panel", async function (assert) {
        serverData.views["partner,4,list"] = '<tree string="Partner"><field name="foo"/></tree>';

        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" view_mode="list" string="ABC" name="51" domain="[['foo', '!=', 'False']]"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [
                            [4, "list"],
                            [5, "form"],
                        ],
                    });
                }
            },
        });

        assert.containsOnce(target, ".o-dashboard-action .o_list_view");
        assert.containsNone(target, ".o-dashboard-action .o_control_panel");
    });

    QUnit.test("can render an action without view_mode attribute", async function (assert) {
        // The view_mode attribute is automatically set to the 'action' nodes when
        // the action is added to the dashboard using the 'Add to dashboard' button
        // in the searchview. However, other dashboard views can be written by hand
        // (see openacademy tutorial), and in this case, we don't want hardcode
        // action's params (like context or domain), as the dashboard can directly
        // retrieve them from the action. Same applies for the view_type, as the
        // first view of the action can be used, by default.
        serverData.views["partner,4,list"] = '<tree string="Partner"><field name="foo"/></tree>';

        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" string="ABC" name="51" domain="[['foo', '!=', 'False']]"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [
                            [4, "list"],
                            [false, "form"],
                        ],
                    });
                }
            },
        });

        assert.containsOnce(target, ".o-dashboard-action .o_list_view");
    });

    QUnit.test("can sort a sub list", async function (assert) {
        serverData.views["partner,4,list"] = '<tree string="Partner"><field name="foo"/></tree>';
        serverData.models.partner.fields.foo.sortable = true;

        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" string="ABC" name="51" domain="[['foo', '!=', 'False']]"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [[4, "list"]],
                    });
                }
            },
        });

        assert.strictEqual(
            $("tr.o_data_row").text(),
            "yoplalalaabc",
            "should have correct initial data"
        );

        await click($(target).find("th.o_column_sortable:contains(Foo)")[0]);
        assert.strictEqual(
            $("tr.o_data_row").text(),
            "abclalalayop",
            "data should have been sorted"
        );
    });

    QUnit.test("can open a record", async function (assert) {
        assert.expect(1);
        const fakeActionService = {
            start() {
                return {
                    doAction(action) {
                        assert.deepEqual(action, {
                            res_id: 1,
                            res_model: "partner",
                            type: "ir.actions.act_window",
                            views: [[false, "form"]],
                        });
                        return Promise.resolve(true);
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        serverData.views["partner,4,list"] = '<tree string="Partner"><field name="foo"/></tree>';
        serverData.models.partner.fields.foo.sortable = true;

        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" string="ABC" name="51" domain="[['foo', '!=', 'False']]"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [[4, "list"]],
                    });
                }
            },
        });

        await click($(target).find("tr.o_data_row td:contains(yop)")[0]);
    });

    QUnit.test("can open record using action form view", async function (assert) {
        assert.expect(1);
        const fakeActionService = {
            start() {
                return {
                    doAction(action) {
                        assert.deepEqual(action, {
                            res_id: 1,
                            res_model: "partner",
                            type: "ir.actions.act_window",
                            views: [[5, "form"]],
                        });
                        return Promise.resolve(true);
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        serverData.views["partner,4,list"] = '<tree string="Partner"><field name="foo"/></tree>';
        serverData.views["partner,5,form"] =
            '<form string="Partner"><field name="display_name"/></form>';

        serverData.models.partner.fields.foo.sortable = true;

        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" string="ABC" name="51" domain="[['foo', '!=', 'False']]"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [
                            [4, "list"],
                            [5, "form"],
                        ],
                    });
                }
            },
        });

        await click($(target).find("tr.o_data_row td:contains(yop)")[0]);
    });

    QUnit.skip("can drag and drop a view", async function (assert) {
        serverData.views["partner,4,list"] = '<tree string="Partner"><field name="foo"/></tree>';

        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" view_mode="list" string="ABC" name="51" domain="[['foo', '!=', 'False']]"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [[4, "list"]],
                    });
                }
                if (route === "/web/view/edit_custom") {
                    assert.step("edit custom");
                    return Promise.resolve(true);
                }
            },
        });

        assert.strictEqual(
            target.querySelectorAll('.o-dashboard-column[data-idx="0"] .o-dashboard-action').length,
            1
        );
        assert.strictEqual(
            target.querySelectorAll('.o-dashboard-column[data-idx="1"] .o-dashboard-action').length,
            0
        );

        await dragAndDrop(
            '.o-dashboard-column[data-idx="0"] .o-dashboard-action-header',
            '.o-dashboard-column[data-idx="1"]'
        );

        assert.strictEqual(
            target.querySelectorAll('.o-dashboard-column[data-idx="0"] .o-dashboard-action').length,
            0
        );
        assert.strictEqual(
            target.querySelectorAll('.o-dashboard-column[data-idx="1"] .o-dashboard-action').length,
            1
        );
        assert.verifySteps(["edit custom"]);
    });

    QUnit.test("twice the same action in a dashboard", async function (assert) {
        serverData.views["partner,4,list"] = '<tree string="Partner"><field name="foo"/></tree>';
        serverData.views["partner,5,kanban"] = `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t>
                </templates>
            </kanban>`;

        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{}" view_mode="list" string="ABC" name="51" domain="[]"></action>
                            <action context="{}" view_mode="kanban" string="DEF" name="51" domain="[]"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [
                            [4, "list"],
                            [5, "kanban"],
                        ],
                    });
                }
                if (route === "/web/view/edit_custom") {
                    assert.step("edit custom");
                    return Promise.resolve(true);
                }
            },
        });

        var $firstAction = $(".o-dashboard-action:eq(0)");
        assert.strictEqual(
            $firstAction.find(".o_list_view").length,
            1,
            "list view should be displayed in 'ABC' block"
        );
        var $secondAction = $(".o-dashboard-action:eq(1)");
        assert.strictEqual(
            $secondAction.find(".o_kanban_view").length,
            1,
            "kanban view should be displayed in 'DEF' block"
        );
    });

    QUnit.test("clicking on a kanban's button should trigger the action", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" view_mode="list" string="ABC" name="51" domain="[['foo', '!=', 'False']]"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    // server answer if the action doesn't exist anymore
                    return Promise.resolve(false);
                }
            },
        });

        assert.containsOnce(target, "h3 span:contains(ABC)");
        assert.containsOnce(target, "div.text-center:contains(Invalid action)");
    });

    QUnit.test("twice the same action in a dashboard", async function (assert) {
        assert.expect(4);
        serverData.views["partner,false,kanban"] = `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <div><field name="foo"/></div>
                            <button name="sitting_on_a_park_bench" type="object">Eying little girls with bad intent</button>
                        </div>
                    </t>
                </templates>
            </kanban>`;

        const view = await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action name="149" string="Partner" view_mode="kanban" id="action_0_1"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        view_mode: "kanban",
                        views: [[false, "kanban"]],
                    });
                }
            },
        });

        patchWithCleanup(view.env.services.action, {
            doActionButton(params) {
                assert.strictEqual(params.resModel, "partner");
                assert.strictEqual(params.resId, 1);
                assert.strictEqual(params.name, "sitting_on_a_park_bench");
                assert.strictEqual(params.type, "object");
            },
        });

        await click(document.querySelector(".btn.oe_kanban_action"));
    });

    QUnit.test("Views should be loaded in the user's language", async function (assert) {
        assert.expect(2);
        patchWithCleanup(session.user_context, { lang: "fr_FR" });
        serverData.views["partner,4,list"] = '<tree string="Partner"><field name="foo"/></tree>';

        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                        <action context="{'lang': 'en_US'}" view_mode="list" string="ABC" name="51" domain="[]"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [[4, "list"]],
                    });
                }
                if (args.method === "get_views") {
                    assert.strictEqual(args.kwargs.context.lang, "fr_FR");
                }
            },
        });
    });

    QUnit.test("Dashboard should use correct groupby", async function (assert) {
        assert.expect(1);
        serverData.views["partner,4,list"] = '<tree string="Partner"><field name="foo"/></tree>';

        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{'group_by': ['bar']}" string="ABC" name="51"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [[4, "list"]],
                    });
                }
                if (args.method === "web_read_group") {
                    assert.deepEqual(args.kwargs.groupby, ["bar"]);
                }
            },
        });
    });

    QUnit.test(
        "Dashboard should use correct groupby when defined as a string of one field",
        async function (assert) {
            assert.expect(1);
            serverData.views["partner,4,list"] =
                '<tree string="Partner"><field name="foo"/></tree>';

            await makeView({
                serverData,
                type: "form",
                resModel: "board",
                arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{'group_by': 'bar'}" string="ABC" name="51"></action>
                        </column>
                    </board>
                </form>`,
                mockRPC(route, args) {
                    if (route === "/web/action/load") {
                        return Promise.resolve({
                            res_model: "partner",
                            views: [[4, "list"]],
                        });
                    }
                    if (args.method === "web_read_group") {
                        assert.deepEqual(args.kwargs.groupby, ["bar"]);
                    }
                },
            });
        }
    );

    QUnit.test("click on a cell of pivot view inside dashboard", async function (assert) {
        serverData.views["partner,4,pivot"] =
            '<pivot><field name="int_field" type="measure"/></pivot>';
        const fakeActionService = {
            start() {
                return {
                    doAction(action) {
                        assert.step("do action");
                        assert.deepEqual(action.views, [
                            [false, "list"],
                            [false, "form"],
                        ]);
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                        <action view_mode="pivot" string="ABC" name="51"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [[4, "pivot"]],
                    });
                }
                if (args.method === "web_read_group") {
                    assert.deepEqual(args.kwargs.groupby, ["bar"]);
                }
            },
        });

        assert.verifySteps([]);

        await click(document.querySelector(".o_pivot_view .o_pivot_cell_value"));

        assert.verifySteps(["do action"]);
    });

    QUnit.test("graphs in dashboard aren't squashed", async function (assert) {
        serverData.views["partner,4,graph"] =
            '<graph><field name="int_field" type="measure"/></graph>';

        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action string="ABC" name="51"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [[4, "graph"]],
                    });
                }
            },
        });

        assert.containsOnce(target, ".o-dashboard-action .o_graph_renderer");
        assert.strictEqual(
            target.querySelector(".o-dashboard-action .o_graph_renderer canvas").offsetHeight,
            300
        );
    });
});
