import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAllTexts, queryOne } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
    serverState,
} from "@web/../tests/web_test_helpers";
import { BoardAction } from "@board/board_action";

class Board extends models.Model {}

class Partner extends models.Model {
    name = fields.Char({ string: "Displayed name", searchable: true });
    foo = fields.Char({
        string: "Foo",
        default: "My little Foo Value",
        searchable: true,
    });
    bar = fields.Boolean({ string: "Bar" });
    int_field = fields.Integer({
        string: "Integer field",
        aggregator: "sum",
    });

    _records = [
        {
            id: 1,
            name: "first record",
            foo: "yop",
            int_field: 3,
        },
        {
            id: 2,
            name: "second record",
            foo: "lalala",
            int_field: 5,
        },
        {
            id: 4,
            name: "aaa",
            foo: "abc",
            int_field: 2,
        },
    ];

    _views = {
        "form,100000001": "<form/>",
        "search,100000002": "<search/>",
        "list,4": '<list string="Partner"><field name="foo"/></list>',
    };
}

defineModels([Board, Partner]);
defineMailModels();

beforeEach(() => {
    BoardAction.cache = {};
});

describe.tags("desktop")("board_desktop", () => {
    test("display the no content helper", async () => {
        await mountView({
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column></column>
                    </board>
                </form>`,
        });
        expect(".o_view_nocontent").toHaveCount(1);
    });

    test("basic functionality, with one sub action", async () => {
        expect.assertions(19);
        onRpc("/web/action/load", () => {
            expect.step("load action");
            return {
                res_model: "partner",
                views: [[4, "list"]],
            };
        });
        onRpc("web_search_read", (args) => {
            expect(args.kwargs.domain).toEqual([["foo", "!=", "False"]], {
                message: "the domain should be passed",
            });
            expect(args.kwargs.context.orderedBy).toEqual(
                [
                    {
                        name: "foo",
                        asc: true,
                    },
                ],
                {
                    message:
                        "orderedBy is present in the search read when specified on the custom action",
                }
            );
        });
        onRpc("/web/view/edit_custom", () => {
            expect.step("edit custom");
            return true;
        });
        onRpc("partner", "get_views", (args) => {
            expect(args.kwargs.views.find((v) => v[1] === "list")).toEqual([4, "list"]);
        });
        await mountView({
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
        });

        expect(".o-dashboard-header").toHaveCount(1, { message: "should have rendered a header" });
        expect("div.o-dashboard-layout-2-1").toHaveCount(1, {
            message: "should have rendered a div with layout",
        });
        expect("td.o_list_record_selector").toHaveCount(0, {
            message: "td should not have a list selector",
        });
        expect("h3 span:contains(ABC)").toHaveCount(1, {
            message: "should have rendered a header with action string",
        });
        expect("tr.o_data_row").toHaveCount(3, { message: "should have rendered 3 data rows" });

        expect(".o-dashboard-action .o_list_view").toHaveCount(1);

        await contains("h3 i.fa-window-minimize").click();

        expect(".o-dashboard-action .o_list_view").toHaveCount(0);

        await contains("h3 i.fa-window-maximize").click();

        // content is visible again
        expect(".o-dashboard-action .o_list_view").toHaveCount(1);
        expect.verifySteps(["load action", "edit custom", "edit custom"]);

        // header should have dropdown with correct image
        expect(
            ".o-dashboard-header .dropdown img[data-src='/board/static/img/layout_2-1.png']"
        ).toHaveCount(1);

        // change layout to 1-1
        await contains(".o-dashboard-header .dropdown img").click();
        await contains(".dropdown-item:nth-child(2)").click();
        expect(
            ".o-dashboard-header .dropdown img[data-src='/board/static/img/layout_1-1.png']"
        ).toHaveCount(1);
        expect("div.o-dashboard-layout-1-1").toHaveCount(1, {
            message: "should have rendered a div with layout",
        });

        expect.verifySteps(["edit custom"]);
    });

    test("views in the dashboard do not have a control panel", async () => {
        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [
                    [4, "list"],
                    [5, "form"],
                ],
            });
        });
        await mountView({
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
        });

        expect(".o-dashboard-action .o_list_view").toHaveCount(1);
        expect(".o-dashboard-action .o_control_panel").toHaveCount(0);
    });

    test("can render an action without view_mode attribute", async () => {
        // The view_mode attribute is automatically set to the 'action' nodes when
        // the action is added to the dashboard using the 'Add to dashboard' button
        // in the searchview. However, other dashboard views can be written by hand
        // (see openacademy tutorial), and in this case, we don't want hardcode
        // action's params (like context or domain), as the dashboard can directly
        // retrieve them from the action. Same applies for the view_type, as the
        // first view of the action can be used, by default.
        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [
                    [4, "list"],
                    [false, "form"],
                ],
            });
        });

        await mountView({
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
        });

        expect(".o-dashboard-action .o_list_view").toHaveCount(1);
    });

    test("can sort a sub list", async () => {
        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [[4, "list"]],
            });
        });
        await mountView({
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
        });

        expect(queryAllTexts("tr.o_data_row")).toEqual(["yop", "lalala", "abc"], {
            message: "should have correct initial data",
        });

        await contains("th.o_column_sortable:contains(Foo)").click();
        expect(queryAllTexts("tr.o_data_row")).toEqual(["abc", "lalala", "yop"], {
            message: "data should have been sorted",
        });
    });

    test("can open a record", async () => {
        expect.assertions(1);
        mockService("action", {
            doAction(action) {
                expect(action).toEqual({
                    res_id: 1,
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                });
                return Promise.resolve(true);
            },
        });
        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [[4, "list"]],
            });
        });
        await mountView({
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
        });

        await contains("tr.o_data_row td:contains(yop)").click();
    });

    test("can open record using action form view", async () => {
        expect.assertions(1);
        Partner._views["form,5"] = '<form string="Partner"><field name="name"/></form>';
        mockService("action", {
            doAction(action) {
                expect(action).toEqual({
                    res_id: 1,
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[5, "form"]],
                });
                return Promise.resolve(true);
            },
        });

        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [
                    [4, "list"],
                    [5, "form"],
                ],
            });
        });

        await mountView({
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
        });

        await contains("tr.o_data_row td:contains(yop)").click();
    });

    test("can drag and drop a view", async () => {
        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [[4, "list"]],
            });
        });
        onRpc("/web/view/edit_custom", () => {
            expect.step("edit custom");
            return Promise.resolve(true);
        });
        await mountView({
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
        });

        expect('.o-dashboard-column[data-idx="0"] .o-dashboard-action').toHaveCount(1);
        expect('.o-dashboard-column[data-idx="1"] .o-dashboard-action').toHaveCount(0);

        await contains('.o-dashboard-column[data-idx="0"] .o-dashboard-action-header').dragAndDrop(
            '.o-dashboard-column[data-idx="1"]'
        );

        expect('.o-dashboard-column[data-idx="0"] .o-dashboard-action').toHaveCount(0);
        expect('.o-dashboard-column[data-idx="1"] .o-dashboard-action').toHaveCount(1);
        expect.verifySteps(["edit custom"]);
    });

    test("twice the same action in a dashboard", async () => {
        Partner._views["kanban,5"] = `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`;
        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [
                    [4, "list"],
                    [5, "kanban"],
                ],
            });
        });
        onRpc("/web/view/edit_custom", () => {
            expect.step("edit custom");
            return Promise.resolve(true);
        });
        await mountView({
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
        });

        expect(".o-dashboard-action:eq(0) .o_list_view").toHaveCount(1);
        expect(".o-dashboard-action:eq(1) .o_kanban_view").toHaveCount(1);
    });

    test("non-existing action in a dashboard", async () => {
        onRpc("/web/action/load", () => {
            // server answer if the action doesn't exist anymore
            return Promise.resolve(false);
        });
        await mountView({
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
        });

        expect("h3 span:contains(ABC)").toHaveCount(1);
        expect(".o-dashboard-action div:contains(Invalid action)").toHaveCount(1);
    });

    test(`clicking on a kanban's button should trigger the action`, async () => {
        expect.assertions(4);
        Partner._views.kanban = `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <button name="sitting_on_a_park_bench" type="object">Eying little girls with bad intent</button>
                    </t>
                </templates>
            </kanban>`;
        mockService("action", {
            doActionButton(params) {
                expect(params.resModel).toBe("partner");
                expect(params.resId).toBe(1);
                expect(params.name).toBe("sitting_on_a_park_bench");
                expect(params.type).toBe("object");
            },
        });
        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                view_mode: "kanban",
                views: [[false, "kanban"]],
            });
        });
        await mountView({
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
        });

        await contains(".btn.oe_kanban_action").click();
    });

    test("Views should be loaded in the user's language", async () => {
        expect.assertions(2);
        serverState.lang = "fr_FR";
        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [[4, "list"]],
            });
        });
        onRpc("get_views", (args) => {
            expect(args.kwargs.context.lang).toBe("fr_FR");
        });
        await mountView({
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
        });
    });

    test("Dashboard should use correct groupby", async () => {
        expect.assertions(1);
        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [[4, "list"]],
            });
        });
        onRpc("web_read_group", (args) => {
            expect(args.kwargs.groupby).toEqual(["bar"]);
        });
        await mountView({
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
        });
    });

    test("Dashboard should read comparison from context", async () => {
        expect.assertions(2);
        Partner._views["pivot,4"] = '<pivot><field name="int_field" type="measure"/></pivot>';
        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [[4, "pivot"]],
            });
        });
        await mountView({
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action
                                name="356"
                                string="Sales Analysis pivot"
                                view_mode="pivot"
                                context="{
                                    'comparison': {
                                        'fieldName': 'date',
                                        'domains': [
                                            {
                                                'arrayRepr': [],
                                                'description': 'February 2023',
                                            },
                                            {
                                                'arrayRepr': [],
                                                'description': 'January 2023',
                                            },
                                        ]
                                    },
                                }"
                            />
                        </column>
                    </board>
                </form>`,
        });
        expect(".o_pivot_origin_row:eq(0)").toHaveText("January 2023");
        expect(".o_pivot_origin_row:eq(1)").toHaveText("February 2023");
    });

    test("Dashboard should use correct groupby when defined as a string of one field", async () => {
        expect.assertions(1);
        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [[4, "list"]],
            });
        });
        onRpc("web_read_group", ({ kwargs }) => {
            expect(kwargs.groupby).toEqual(["bar"]);
        });
        await mountView({
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
        });
    });

    test("click on a cell of pivot view inside dashboard", async () => {
        Partner._views["pivot,4"] = '<pivot><field name="int_field" type="measure"/></pivot>';
        mockService("action", {
            doAction(action) {
                expect.step("do action");
                expect(action.views).toEqual([
                    [false, "list"],
                    [false, "form"],
                ]);
            },
        });

        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [[4, "pivot"]],
            });
        });
        onRpc("web_read_group", (args) => {
            expect(args.kwargs.groupby).toEqual(["bar"]);
        });

        await mountView({
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
        });

        expect.verifySteps([]);

        await contains(".o_pivot_view .o_pivot_cell_value").click();

        expect.verifySteps(["do action"]);
    });

    test("graphs in dashboard aren't squashed", async () => {
        Partner._views["graph,4"] = '<graph><field name="int_field" type="measure"/></graph>';
        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [[4, "graph"]],
            });
        });
        await mountView({
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
        });

        expect(".o-dashboard-action .o_graph_renderer").toHaveCount(1);
        expect(queryOne(".o-dashboard-action .o_graph_renderer canvas").offsetHeight).toBe(300);
    });
});

describe.tags("mobile")("board_mobile", () => {
    test("can't switch views in the dashboard", async () => {
        Partner._views["list,4"] = '<list string="Partner"><field name="foo"/></list>';

        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [[4, "list"]],
            });
        });
        await mountView({
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
        });

        expect(".o-dashboard-header").toHaveCount(0, {
            message: "Couldn't allow user to Change layout",
        });
        expect(".o-dashboard-layout-1").toHaveCount(1, {
            message: "The display layout is force to 1",
        });
        expect(".o-dashboard-action .o_control_panel").not.toBeVisible();
        expect(".o-dashboard-action-header .fa-close").toHaveCount(0, {
            message: "Should not have a close action button",
        });
    });

    test("Correctly soft switch to '1' layout on small screen", async () => {
        Partner._views["list,4"] = '<list string="Partner"><field name="foo"/></list>';

        onRpc("/web/action/load", () => {
            return Promise.resolve({
                res_model: "partner",
                views: [[4, "list"]],
            });
        });
        await mountView({
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" view_mode="list" string="ABC" name="51" domain="[['foo', '!=', 'False']]"></action>
                        </column>
                        <column>
                            <action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" view_mode="list" string="ABC" name="51" domain="[['foo', '!=', 'False']]"></action>
                        </column>
                    </board>
                </form>`,
        });
        expect(".o-dashboard-layout-1").toHaveCount(1, {
            message: "The display layout is force to 1",
        });
        expect(".o-dashboard-column").toHaveCount(1, {
            message: "The display layout is force to 1 column",
        });
        expect(".o-dashboard-action").toHaveCount(2, {
            message: "The display should contains the 2 actions",
        });
    });
});
