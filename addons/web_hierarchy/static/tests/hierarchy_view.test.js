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
import { hierarchyRead } from "./hierarchy_test_helpers";

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

    hierarchy_read() {
        return hierarchyRead.call(this, ...arguments);
    }
}

defineModels([Employee]);

describe.current.tags("desktop");

test("load hierarchy view: a single root is unfolded", async () => {
    onRpc("hierarchy_read", ({ kwargs }) => {
        expect.step([kwargs.parent_field_name, kwargs.roots_only]);
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect.verifySteps([["parent_id", true]]);
    expect(".o_hierarchy_view").toHaveCount(1);
    expect(".o_hierarchy_button_add").toHaveCount(1);
    expect(".o_hierarchy_view .o_hierarchy_renderer").toHaveCount(1);
    expect(".o_hierarchy_view .o_hierarchy_renderer > .o_hierarchy_container").toHaveCount(1);
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_separator").toHaveCount(1);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node > div").toHaveText("Albert", {
        message: "the only root is displayed as the parent",
    });
    expect(queryAllTexts(".o_hierarchy_row:eq(1) .o_hierarchy_node > div")).toEqual([
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);
    expect(".o_hierarchy_node > button").toHaveCount(1, {
        message: "Albert has no parent (no ancestor button), Georges has no children",
    });
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node > button[title='Unfold']").toHaveText(
        "1 Subordinates"
    );
});

test("several roots are displayed without being unfolded", async () => {
    Employee._records.push({ id: 5, name: "Zoe", parent_id: false, child_ids: [] });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_separator").toHaveCount(0);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(["Albert", "Zoe"]);
    expect(".o_hierarchy_node > button[title='Unfold']").toHaveCount(1);
    expect(".o_hierarchy_node > button[title='Unfold']").toHaveText("2 Subordinates");
    expect(".o_hierarchy_node > button[title='Show ancestor']").toHaveCount(0);
});

test("the domain of the action targets a node: it is displayed with its children", async () => {
    Employee._records.push({ id: 5, name: "Lisa", parent_id: 3, child_ids: [] });
    Employee._records.find((rec) => rec.id === 3).child_ids.push(5);
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        domain: [["parent_id", "=", 3]],
    });

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node > div").toHaveText("Josephine\nAlbert");
    expect(queryAllTexts(".o_hierarchy_row:eq(1) .o_hierarchy_node > div")).toEqual([
        "Louis\nJosephine",
        "Lisa\nJosephine",
    ]);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node > button[title='Unfold']").toHaveCount(0, {
        message: "the parent node can't be unfolded, its children are already displayed",
    });
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node > button[title='Show ancestor']").toHaveText(
        "Show manager"
    );
});

test("unfold opens the hierarchy of the record in a new action", async () => {
    mockService("action", {
        doAction(action, options) {
            expect.step({
                name: action.name,
                res_model: action.res_model,
                domain: action.domain,
                viewType: options.viewType,
            });
        },
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
    await enableFilters(["no_georges"]);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual([
        "Albert",
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);

    await contains(".o_hierarchy_node:contains(Josephine) > button[title='Unfold']").click();
    expect.verifySteps([
        {
            name: "Josephine",
            res_model: "hr.employee",
            domain: [["parent_id", "=", 3]],
            viewType: "hierarchy",
        },
    ]);
});

test("show ancestor opens the hierarchy of the parent of the parent node", async () => {
    mockService("action", {
        doAction(action, options) {
            expect.step({ name: action.name, domain: action.domain, viewType: options.viewType });
        },
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        domain: [["parent_id", "=", 3]],
    });

    await contains(".o_hierarchy_node > button[title='Show ancestor']").click();
    expect.verifySteps([
        { name: "Albert", domain: [["parent_id", "=", 1]], viewType: "hierarchy" },
    ]);
});

test("a search displays the matching records, without filtering on the roots", async () => {
    onRpc("hierarchy_read", ({ kwargs }) => {
        expect.step(kwargs.roots_only);
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        viewId: false,
        searchViewArch: `
            <search>
                <filter name="find_josephine_louis" domain="[['id', 'in', [3, 4]]]"/>
                <filter name="find_louis" domain="[['id', '=', 4]]"/>
            </search>
        `,
    });
    expect.verifySteps([true]);

    await enableFilters(["find_josephine_louis"]);
    expect.verifySteps([false]);
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_separator").toHaveCount(0);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual([
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);

    await toggleMenuItem("find_josephine_louis");
    await toggleMenuItem("find_louis");
    expect.verifySteps([true, false]);
    expect(".o_hierarchy_row").toHaveCount(1, {
        message: "a single search result is not unfolded, only a single root is",
    });
    expect(".o_hierarchy_node > div").toHaveText("Louis\nJosephine");
});

test("Add a custom domain leaf on default state of the view with a globalDomain and search default filters", async () => {
    Employee._records = [
        { id: 1, name: "A", parent_id: false, child_ids: [] },
        { id: 2, name: "B", parent_id: false, child_ids: [4] },
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
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(["B", "D\nB"], {
        message: `A is hidden by the globalDomain and C by the search_default: the view is in its
            "default state", so only the roots are fetched and B is the only one. It is then unfolded.`,
    });

    await removeFacet("exclude_third");
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(["B", "C"], {
        message: `C is now visible because the search_default was removed. The query is empty, so only
            the roots are displayed, and there are several of them: none is unfolded.`,
    });

    await enableFilters(["find_fifth"]);
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node > div").toHaveText("E\nD", {
        message: `E matches the query. The view is not in its "default state", nor is the query empty,
            so the records are not restricted to the roots.`,
    });

    await removeFacet("find_fifth");
    await enableFilters(["exclude_third"]);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(["B", "D\nB"], {
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

test("the card template can use parentId to know if the record has a parent", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        arch: `
                <hierarchy child_field="child_ids">
                    <templates>
                        <t t-name="card">
                            <field name="name"/>
                            <span t-if="!parentId" class="o_root_marker">root</span>
                        </t>
                    </templates>
                </hierarchy>
            `,
    });
    expect(".o_root_marker").toHaveCount(1);
    expect(".o_hierarchy_row:eq(0) .o_root_marker").toHaveCount(1, {
        message: "only Albert, the root, has no parent",
    });
});

test("Reload the view with the same records when clicking with a view button", async () => {
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
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual([
        "Albert\nprefix",
        "Georges\nAlbert\nprefix",
        "Josephine\nAlbert\nprefix",
    ]);
    await contains(".o_hierarchy_node_container:eq(1) button[name='prefix_underscore']").click();
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(
        ["Albert\nprefix", "_Georges\nAlbert\nprefix", "Josephine\nAlbert\nprefix"],
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
    expect(".o_hierarchy_node").toHaveCount(0);
});

test("Navigate in the hierarchy and come back with the breadcrumb", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "hr.employee",
        type: "ir.actions.act_window",
        views: [
            [false, "hierarchy"],
            [false, "form"],
        ],
    });
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);

    await contains(".o_hierarchy_node:contains(Josephine) > button[title='Unfold']").click();
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual([
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);

    await contains(".o_hierarchy_row:eq(1) .o_hierarchy_node").click();
    expect(".o_hierarchy_view").toHaveCount(0);
    expect(".o_form_view").toHaveCount(1);

    await contains(".o_back_button").click();
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(
        ["Josephine\nAlbert", "Louis\nJosephine"],
        { message: "coming back from the form restores the level of Josephine" }
    );

    await contains(".o_back_button").click();
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(
        ["Albert", "Georges\nAlbert", "Josephine\nAlbert"],
        { message: "the previous action is the level of Albert" }
    );
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

test("a cycle in the hierarchy does not loop", async () => {
    Employee._records = [
        { id: 1, name: "A", parent_id: 2, child_ids: [2] },
        { id: 2, name: "B", parent_id: 1, child_ids: [1] },
    ];
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        domain: [["parent_id", "=", 1]],
    });
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(["A\nB", "B\nA"]);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node > button[title='Show ancestor']").toHaveCount(1);
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node > button[title='Unfold']").toHaveCount(1);
});

test("a record that is its own parent is displayed as parent and as child", async () => {
    Employee._records = [{ id: 1, name: "Self", parent_id: 1, child_ids: [1] }];
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        domain: [["parent_id", "=", 1]],
    });
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_node > div")).toEqual(["Self\nSelf", "Self\nSelf"]);
});

test("control panel pager without parent", async () => {
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

test("control panel pager paginates the children of the unfolded root", async () => {
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

    const controlPanel = queryOne(".o_control_panel");
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node > div").toHaveText("Albert");
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node").toHaveCount(80);
    expect(getPagerValue(controlPanel)).toEqual([1, 80]);
    expect(getPagerLimit(controlPanel)).toBe(81, {
        message: "the pager counts the children only, not the parent",
    });

    await pagerNext(controlPanel);
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node > div").toHaveText("Albert", {
        message: "the parent is still displayed on the next pages",
    });
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node").toHaveCount(1);
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node > div").toHaveText("Emp 82\nAlbert");
    expect(getPagerValue(controlPanel)).toEqual([81, 81]);
});

test("the user limit is kept when the search changes", async () => {
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
});
