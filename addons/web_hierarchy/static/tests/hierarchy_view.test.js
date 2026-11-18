import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts, queryOne } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    getService,
    getPagerLimit,
    getPagerValue,
    MockServer,
    mockService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    pagerNext,
    patchWithCleanup,
    removeFacet,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { WebClient } from "@web/webclient/webclient";

async function enableFilters(filterNames = []) {
    await toggleSearchBarMenu();
    for (const filter of filterNames) {
        await toggleMenuItem(filter);
    }
}

class Employee extends models.Model {
    _name = "hr.employee";

    name = fields.Char();
    parent_id = fields.Many2one({ string: "Manager", relation: "hr.employee" });
    child_ids = fields.One2many({
        string: "Subordinates",
        relation: "hr.employee",
        relation_field: "parent_id",
    });
    avatar_128 = fields.Image();

    _records = [
        { id: 1, name: "Albert", parent_id: false, child_ids: [2, 3] },
        { id: 2, name: "Georges", parent_id: 1, child_ids: [] },
        { id: 3, name: "Josephine", parent_id: 1, child_ids: [4] },
        { id: 4, name: "Louis", parent_id: 3, child_ids: [] },
    ];

    _views = {
        hierarchy: `
            <hierarchy child_field="child_ids">
                <templates>
                    <t t-name="card">
                        <div>
                            <field name="name"/>
                        </div>
                        <div>
                            <field name="parent_id"/>
                        </div>
                    </t>
                </templates>
            </hierarchy>
        `,
        form: `
            <form>
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="parent_id"/>
                    </group>
                </sheet>
            </form>
        `,
    };
}

defineModels([Employee]);

describe.current.tags("desktop");

test("load hierarchy view", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect(".o_hierarchy_view").toHaveCount(1);
    expect(".o_hierarchy_button_add").toHaveCount(1);
    expect(".o_hierarchy_view .o_hierarchy_renderer").toHaveCount(1);
    expect(".o_hierarchy_view .o_hierarchy_renderer > .o_hierarchy_container").toHaveCount(1);
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node_container").toHaveCount(1);
    expect(".o_hierarchy_node").toHaveCount(1);
    expect(".o_hierarchy_node > div").toHaveText("Albert");
    expect(".o_hierarchy_node > button").toHaveCount(1);
    expect(".o_hierarchy_node > button[title='Unfold']").toHaveText("2 Unfold");
});

test("Expand and collapse child nodes", async () => {
    onRpc("web_search_read", () => {
        expect.step("web_search_read");
    });
    onRpc("web_read_group", () => {
        expect.step("web_read_group");
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect.verifySteps(["web_search_read"]);

    await contains(".o_hierarchy_node > button[title='Unfold']").click();

    expect.verifySteps(["web_read_group"]);
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_separator").toHaveCount(1);
    expect(".o_hierarchy_line_part").toHaveCount(2);
    expect(".o_hierarchy_line_left").toHaveCount(1);
    expect(".o_hierarchy_line_right").toHaveCount(1);
    expect(".o_hierarchy_node_container").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node > div").toHaveText("Albert");
    expect(queryAllTexts(".o_hierarchy_row:eq(1) .o_hierarchy_node > div")).toEqual([
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);
    expect(".o_hierarchy_node > button").toHaveCount(2);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node > button[title='Fold']").toHaveText("2 Fold");
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node > button[title='Unfold']").toHaveText("1 Unfold");

    await contains(".o_hierarchy_row:eq(1) .o_hierarchy_node > button[title='Unfold']").click();

    expect.verifySteps(["web_read_group"]);
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_separator").toHaveCount(2);
    expect(".o_hierarchy_line_part").toHaveCount(4);
    expect(".o_hierarchy_line_left").toHaveCount(2);
    expect(".o_hierarchy_line_right").toHaveCount(2);
    expect(".o_hierarchy_node_container").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node > div").toHaveText("Albert");
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node > div").toHaveText("Josephine\nAlbert");
    expect(".o_hierarchy_row:eq(2) .o_hierarchy_node > div").toHaveText("Louis\nJosephine");
    expect(".o_hierarchy_node > button").toHaveCount(2);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node > button[title='Fold']").toHaveText("2 Fold");
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node > button[title='Fold']").toHaveText("1 Fold");

    await contains(".o_hierarchy_row:eq(0) .o_hierarchy_node > button[title='Fold']").click();

    expect.verifySteps(["web_search_read"]);
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node > div").toHaveText("Albert");
    expect(".o_hierarchy_node > button[title='Unfold']").toHaveText("2 Unfold");
    expect(".o_hierarchy_separator").toHaveCount(0);
    expect(".o_hierarchy_line_part").toHaveCount(0);
    expect(".o_hierarchy_line_left").toHaveCount(0);
    expect(".o_hierarchy_line_right").toHaveCount(0);
});

test("Add a custom domain leaf on default state of the view with a globalDomain and search default filters", async () => {
    Employee._records = [
        { id: 1, name: "A", parent_id: false, child_ids: [] },
        { id: 2, name: "B", parent_id: false, child_ids: [3, 4] },
        { id: 3, name: "C", parent_id: false, child_ids: [] },
        { id: 4, name: "D", parent_id: 2, child_ids: [5, 6] },
        { id: 5, name: "E", parent_id: 4, child_ids: [] },
        { id: 6, name: "F", parent_id: 4, child_ids: [] },
    ];
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        viewId: false,
        searchViewArch: `
                <search>
                    <filter name="exclude_third" domain="[['id', '!=', 3]]"/>
                    <filter name="find_fifth" domain="[['id', '=', 5]]"/>
                </search>
            `,
        context: { search_default_exclude_third: true },
        domain: [["id", "not in", [1, 6]]],
    });
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node").toHaveCount(1);
    expect(".o_hierarchy_node > div").toHaveText("B", {
        message: `A and F should be hidden by the globalDomain, C is hidden because of the search_default, and
            E, F and D are hidden because the custom domain leaf [['parent_id', '=', false]] is applied
            since the view is in its "default state". B is shown because it is the only one result.`,
    });
    await removeFacet("exclude_third");
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(["B", "C"], {
        message: `C is now visible because the search_default was removed. E, F and D are still hidden because
            the custom domain leaf [['parent_id', '=', false]] is also applied when the search query is empty.`,
    });
    await enableFilters(["find_fifth"]);
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node").toHaveCount(1);
    expect(".o_hierarchy_node > div").toHaveText("E\nD", {
        message: `E is shown because it matches the query and the custom domain leaf [['parent_id', '=', false]]
            is not applied since the view is not in its "default state", nor is the query empty. Other nodes are hidden
            since E was the only record matching the query.`,
    });
    await removeFacet("find_fifth");
    await enableFilters(["exclude_third"]);
    expect(".o_hierarchy_node > div").toHaveText("B", {
        message: `Manually going back to the "default state" of the view should give the same result as the
            first load.`,
    });
});

test("can properly evaluate invisible elements in a hierarchy card", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        arch: `
                <hierarchy child_field="child_ids">
                    <field name="child_ids" invisible="1"/>
                    <templates>
                        <t t-name="card">
                            <div>
                                <field name="name"/>
                            </div>
                            <div>
                                <field name="parent_id"/>
                            </div>
                            <p invisible="not child_ids" class="o_children_text">withChildren</p>
                        </t>
                    </templates>
                </hierarchy>
            `,
    });
    await contains(".o_hierarchy_node > button[title='Unfold']").click();
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(".o_hierarchy_node_container:eq(0) .o_hierarchy_node > div").toHaveText(
        "Albert\n\nwithChildren"
    );
    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node > div").toHaveText(
        "Georges\nAlbert"
    );
    expect(".o_hierarchy_node_container:eq(2) .o_hierarchy_node > div").toHaveText(
        "Josephine\nAlbert\n\nwithChildren"
    );
    expect(".o_hierarchy_node_container:eq(0) .o_children_text").toHaveCount(1);
    expect(".o_hierarchy_node_container:eq(1) .o_children_text").toHaveCount(0);
    expect(".o_hierarchy_node_container:eq(2) .o_children_text").toHaveCount(1);
});

test("Reload the view with the same unfolded records when clicking with a view button", async () => {
    mockService("action", {
        doActionButton({ resId, onClose }) {
            for (const record of MockServer.env["hr.employee"].browse(resId)) {
                record.name = "_" + record.name;
            }
            onClose();
        },
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        arch: `
                <hierarchy child_field="child_ids">
                    <templates>
                        <t t-name="card">
                            <div>
                                <field name="name"/>
                            </div>
                            <div>
                                <field name="parent_id"/>
                            </div>
                            <button type="object" name="prefix_underscore">prefix</button>
                        </t>
                    </templates>
                </hierarchy>
            `,
    });
    await contains(".o_hierarchy_node > button[title='Unfold']").click();
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual([
        "Albert\nprefix",
        "Georges\nAlbert\nprefix",
        "Josephine\nAlbert\nprefix",
    ]);
    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node > div").toHaveText(
        "Georges\nAlbert\nprefix"
    );
    await contains(".o_hierarchy_node_container:eq(1) button[name='prefix_underscore']").click();
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(
        [
            "Albert\nprefix",
            "_Georges\nAlbert\nprefix",
            "Josephine\nAlbert\nprefix",
        ],
        { message: "The view should have reloaded the same data" }
    );
});

test("The view displays the No Content help", async () => {
    Employee._records = [];
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect("div.o_view_nocontent").toHaveCount(1);
});

test("Keep the same hierarchy state when we go back to the view with the breadcrumb", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "hr.employee",
        type: "ir.actions.act_window",
        views: [
            [false, "hierarchy"],
            [false, "form"],
        ],
    });

    await contains(".o_hierarchy_node > button[title='Unfold']").click();
    await contains(".o_hierarchy_node > button[title='Unfold']").click();
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual([
        "Albert",
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);
    await contains(".o_hierarchy_node_container:eq(1) .o_hierarchy_node").click();
    expect(".o_hierarchy_view").toHaveCount(0);
    expect(".o_form_view").toHaveCount(1);
    await contains(".o_back_button").click();
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual([
        "Albert",
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);
});

test("Opening a branch replaces the current one", async () => {
    Employee._records.push(
        { id: 5, name: "Jean", parent_id: 2, child_ids: [6] },
        { id: 6, name: "Claude", parent_id: 5, child_ids: [] }
    );
    Employee._records.find((rec) => rec.id === 2).child_ids.push(5);
    await mountView({
        resModel: "hr.employee",
        type: "hierarchy",
    });
    await contains(".o_hierarchy_node > button[title='Unfold']").click();
    await contains(".o_hierarchy_node > button[title='Unfold']:eq(0)").click();
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Jean\nGeorges",
    ]);
    expect(".o_hierarchy_node > button[title='Unfold']").toHaveCount(1);
    await contains(".o_hierarchy_node > button[title='Unfold']").click();
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Jean\nGeorges",
        "Claude\nJean",
    ]);
    expect(".o_hierarchy_node > button[title='Fold']").toHaveCount(3);
    await contains(".o_hierarchy_node > button[title='Fold']:eq(0)").click();
    expect(".o_hierarchy_node > div").toHaveText("Albert");
    expect(".o_hierarchy_node > button[title='Unfold']").toHaveCount(1);
    await contains(".o_hierarchy_node > button[title='Unfold']").click();
    await contains(".o_hierarchy_node > button[title='Unfold']:eq(1)").click();
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual([
        "Albert",
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);
});

test("Open record on new window", async () => {
    patchWithCleanup(browser, {
        open: (url) => {
            expect.step(`opened in new window: ${url}`);
        },
    });
    patchWithCleanup(browser.sessionStorage, {
        setItem(key, value) {
            expect.step(`set ${key}-${value}`);
            super.setItem(key, value);
        },
        getItem(key) {
            const res = super.getItem(key);
            expect.step(`get ${key}-${res}`);
            return res;
        },
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "hr.employee",
        type: "ir.actions.act_window",
        views: [
            [false, "hierarchy"],
            [false, "form"],
        ],
    });

    await contains(".o_hierarchy_node_container .o_hierarchy_node").click({ ctrlKey: true });
    expect(".o_hierarchy_view").toHaveCount(1);
    expect(".o_form_view").toHaveCount(0);
    expect.verifySteps([
        "get menu_id-null",
        "get current_lang-null",
        "get current_state-null",
        "get current_action-null",
        'set current_state-{"actionStack":[{"displayName":"","model":"hr.employee","view_type":"hierarchy"}],"model":"hr.employee"}',
        'set current_action-{"res_model":"hr.employee","type":"ir.actions.act_window","views":[[false,"hierarchy"],[false,"form"]]}',
        "set current_lang-en",
        'get current_action-{"res_model":"hr.employee","type":"ir.actions.act_window","views":[[false,"hierarchy"],[false,"form"]]}',
        'get current_state-{"actionStack":[{"displayName":"","model":"hr.employee","view_type":"hierarchy"}],"model":"hr.employee"}',
        'set current_action-{"res_model":"hr.employee","type":"ir.actions.act_window","views":[[false,"hierarchy"],[false,"form"]]}',
        'set current_state-{"actionStack":[{"displayName":"","model":"hr.employee","view_type":"hierarchy"},{"displayName":"","model":"hr.employee","view_type":"form","resId":1}],"resId":1,"model":"hr.employee"}',
        "opened in new window: /odoo/hr.employee/1",
        'set current_action-{"res_model":"hr.employee","type":"ir.actions.act_window","views":[[false,"hierarchy"],[false,"form"]]}',
        'set current_state-{"actionStack":[{"displayName":"","model":"hr.employee","view_type":"hierarchy"}],"model":"hr.employee"}',
    ]);
});

test("rows are ordered by depth, whatever the server group order", async () => {
    Employee._records = [
        { id: 4, name: "Zed", parent_id: false, child_ids: [3] },
        { id: 3, name: "Yan", parent_id: 4, child_ids: [2] },
        { id: 2, name: "Xavier", parent_id: 3, child_ids: [1] },
        { id: 1, name: "Will", parent_id: 2, child_ids: [] },
    ];
    await mountView({ type: "hierarchy", resModel: "hr.employee" });

    await contains(".o_hierarchy_node > button[title='Unfold']").click();
    await contains(".o_hierarchy_row:eq(1) .o_hierarchy_node > button[title='Unfold']").click();
    await contains(".o_hierarchy_row:eq(2) .o_hierarchy_node > button[title='Unfold']").click();

    expect(".o_hierarchy_row").toHaveCount(4);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(
        ["Zed", "Yan\nZed", "Xavier\nYan", "Will\nXavier"],
        { message: "groups should be sorted from the root to the deepest level" }
    );
});

test("hierarchy with a cycle or a self parent does not loop", async () => {
    Employee._records = [
        { id: 1, name: "A", parent_id: 2, child_ids: [2] },
        { id: 2, name: "B", parent_id: 1, child_ids: [1] },
        { id: 3, name: "Self", parent_id: 3, child_ids: [3] },
    ];
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        viewId: false,
        searchViewArch: `
            <search>
                <filter name="find_cycle" domain="[['id', 'in', [1, 2]]]"/>
                <filter name="find_self" domain="[['id', '=', 3]]"/>
            </search>
        `,
    });

    await enableFilters(["find_cycle"]);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(["A\nB", "B\nA"]);
    await contains(".o_hierarchy_node > button[title='Unfold']:eq(0)").click();
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(["B\nA", "A\nB"]);

    await removeFacet("find_cycle");
    await enableFilters(["find_self"]);
    expect(".o_hierarchy_node > div").toHaveText("Self\nSelf");
    await contains(".o_hierarchy_node > button[title='Unfold']").click();
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node").toHaveCount(1);
    expect(".o_hierarchy_node > button").toHaveText("1 Fold");
});

test("group pager between rows", async () => {
    Employee._records = [
        { id: 1, name: "Albert", parent_id: false, child_ids: [] },
        ...Array.from({ length: 81 }, (_, i) => ({
            id: i + 2,
            name: `Emp ${i + 2}`,
            parent_id: 1,
            child_ids: [],
        })),
    ];
    Employee._records[0].child_ids = Employee._records.slice(1).map((r) => r.id);
    await mountView({ type: "hierarchy", resModel: "hr.employee" });

    await contains(".o_hierarchy_node > button[title='Unfold']").click();
    expect(".o_control_panel .o_pager").toHaveCount(0, {
        message: "no control panel pager in grouped mode",
    });
    expect(".o_hierarchy_pager .o_pager").toHaveCount(1);
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node").toHaveCount(80);
    expect(getPagerValue(queryOne(".o_hierarchy_pager"))).toEqual([1, 80]);
    expect(getPagerLimit(queryOne(".o_hierarchy_pager"))).toBe(81);

    await pagerNext(queryOne(".o_hierarchy_pager"));
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node").toHaveCount(1);
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node > div").toHaveText("Emp 82\nAlbert");
    expect(getPagerValue(queryOne(".o_hierarchy_pager"))).toEqual([81, 81]);
});

test("control panel pager in flat mode", async () => {
    Employee._records = Array.from({ length: 81 }, (_, i) => ({
        id: i + 1,
        name: `Emp ${i + 1}`,
        parent_id: false,
        child_ids: [],
    }));
    await mountView({ type: "hierarchy", resModel: "hr.employee" });

    const controlPanel = queryOne(".o_control_panel");
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node").toHaveCount(80);
    expect(getPagerValue(controlPanel)).toEqual([1, 80]);
    expect(getPagerLimit(controlPanel)).toBe(81);

    await pagerNext(controlPanel);
    expect(".o_hierarchy_node").toHaveCount(1);
    expect(".o_hierarchy_node > div").toHaveText("Emp 81");
    expect(getPagerValue(controlPanel)).toEqual([81, 81]);
});

test("flat mode limit is kept on reload and reset after a fold", async () => {
    Employee._records.push(
        { id: 5, name: "Zoe", parent_id: false, child_ids: [] },
        { id: 6, name: "Yann", parent_id: false, child_ids: [] }
    );
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        viewId: false,
        searchViewArch: `
            <search>
                <filter name="no_louis" domain="[['id', '!=', 4]]"/>
            </search>
        `,
    });
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(["Albert", "Zoe", "Yann"]);

    await contains(".o_control_panel .o_pager_value").click();
    await contains(".o_control_panel input.o_pager_value").edit("1-2");
    expect(".o_hierarchy_node").toHaveCount(2);
    expect(getPagerValue(queryOne(".o_control_panel"))).toEqual([1, 2]);

    await enableFilters(["no_louis"]);
    expect(".o_hierarchy_node").toHaveCount(2, {
        message: "the user limit is kept when the search changes",
    });
    expect(getPagerValue(queryOne(".o_control_panel"))).toEqual([1, 2]);
    expect(getPagerLimit(queryOne(".o_control_panel"))).toBe(5);

    await contains(".o_hierarchy_node > button[title='Unfold']").click(); // Albert
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);

    await contains(".o_hierarchy_node > button[title='Fold']").click();
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node").toHaveCount(5, {
        message: "coming back from the grouped mode resets the limit to the default one",
    });
    expect(getPagerValue(queryOne(".o_control_panel"))).toEqual([1, 5]);
});

test("Unfold keeps the search domain", async () => {
    onRpc("web_search_read", () => {
        expect.step("web_search_read");
    });
    onRpc("web_read_group", () => {
        expect.step("web_read_group");
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        viewId: false,
        searchViewArch: `
            <search>
                <filter name="no_georges" domain="[['id', '!=', 2]]"/>
            </search>
        `,
    });
    expect.verifySteps(["web_search_read"]);

    await enableFilters(["no_georges"]);
    expect.verifySteps(["web_search_read"]);
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual([
        "Albert",
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);

    await contains(".o_hierarchy_node > button[title='Unfold']:eq(0)").click(); // Albert
    expect.verifySteps(["web_read_group"]);
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(["Albert", "Josephine\nAlbert"], {
        message: "Georges is a child of Albert but is excluded by the active filter",
    });
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node > button[title='Fold']").toHaveText("2 Fold", {
        message: "the child count comes from the record, not from the filtered children",
    });

    await contains(".o_hierarchy_node > button[title='Fold']").click();
    expect.verifySteps(["web_search_read"]);
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(
        ["Albert", "Josephine\nAlbert", "Louis\nJosephine"],
        { message: "folding goes back to the filtered flat list, the filter is still applied" }
    );
});

test("use `target_parent_res_id` context to open the view on a node with its children", async () => {
    Employee._records.push({ id: 5, name: "Lisa", parent_id: 3, child_ids: [] });
    Employee._records.find((rec) => rec.id === 3).child_ids.push(5);
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        context: { target_parent_res_id: 3 }, // Lisa's manager, as computed by `parent_id or id`
    });

    expect(".o_hierarchy_row").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(
        ["Albert", "Josephine\nAlbert", "Louis\nJosephine", "Lisa\nJosephine"],
        { message: "the path to Josephine and all her children are displayed" }
    );
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node > button[title='Fold']").toHaveText("2 Fold", {
        message: "Josephine's children are loaded",
    });

    await contains(".o_hierarchy_row:eq(0) .o_hierarchy_node > button[title='Fold']").click();
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(["Albert"], {
        message: "the context is only applied on the first load",
    });
});
