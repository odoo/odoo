import { animationFrame, describe, expect, test } from "@odoo/hoot";
import { drag, queryAllTexts, queryOne, queryRect } from "@odoo/hoot-dom";
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
    pagerPrevious,
    patchWithCleanup,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { WebClient } from "@web/webclient/webclient";

const NODE = ".o_hierarchy_node";
const NODE_CONTENT = ".o_hierarchy_node > .flex-fill";

async function enableFilters(filterNames = []) {
    await toggleSearchBarMenu();
    for (const filter of filterNames) {
        await toggleMenuItem(filter);
    }
}

function getEdges() {
    return [...document.querySelectorAll(".o_hierarchy_edge")].map((el) => el.dataset.edge);
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

    _records = [
        { id: 1, name: "Albert", parent_id: false, child_ids: [2, 3] },
        { id: 2, name: "Georges", parent_id: 1, child_ids: [] },
        { id: 3, name: "Josephine", parent_id: 1, child_ids: [4] },
        { id: 4, name: "Louis", parent_id: 3, child_ids: [] },
    ];

    _views = {
        // the server adds the child field to the arch (see `_postprocess_tag_hierarchy`)
        hierarchy: `
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

test("display all the records of the domain, linked to their displayed parent", async () => {
    onRpc("hierarchy_read", ({ args, kwargs }) => {
        expect.step({ domain: args[0], parentFieldName: args[2], limit: kwargs.limit });
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect.verifySteps([{ domain: [], parentFieldName: "parent_id", limit: 80 }]);
    expect(".o_hierarchy_view .o_hierarchy_renderer").toHaveCount(1);
    expect(".o_hierarchy_button_add").toHaveCount(1);
    expect(queryAllTexts(NODE_CONTENT)).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);
    expect(getEdges()).toEqual(["1_2", "1_3", "3_4"]);
    expect(`${NODE} button`).toHaveCount(0, {
        message: "all the parents and children are displayed: nothing to unfold",
    });
    expect(".o_hierarchy_controls .o_hierarchy_zoom_level").toHaveCount(1);
});

// 1: Albert, 2: Georges, 3: Josephine, 4: Louis
const nodeRect = (id) => queryRect(`.o_hierarchy_node_container[data-id='${id}']`);

test("the nodes are laid out from top to bottom", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect(nodeRect(2).top).toBeGreaterThan(nodeRect(1).bottom);
    expect(nodeRect(3).top).toBe(nodeRect(2).top);
    expect(nodeRect(4).top).toBeGreaterThan(nodeRect(3).bottom);
    expect(nodeRect(3).left).toBeGreaterThan(nodeRect(2).right);
});

test("a card can be moved with the mouse, without opening the record", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        selectRecord: (resId) => expect.step(`open ${resId}`),
    });
    const edge = queryOne(".o_hierarchy_edge[data-edge='1_2']");
    const initialPath = edge.getAttribute("d");
    const initialRect = nodeRect(2);

    // the card is released outside of itself: the drag must not depend on the pointer capture
    const { drop } = await drag(".o_hierarchy_node_container[data-id='2'] .o_hierarchy_node");
    await drop(".o_hierarchy_renderer", { position: { x: 5, y: 5 }, relative: true });
    await animationFrame();
    expect(nodeRect(2).top).not.toBe(initialRect.top);
    expect(nodeRect(2).left).not.toBe(initialRect.left);
    expect(edge.getAttribute("d")).not.toBe(initialPath, {
        message: "the link follows the moved card",
    });
    expect(nodeRect(3).top).toBe(initialRect.top, { message: "the other cards do not move" });
    expect.verifySteps([]);

    await contains(".o_hierarchy_node_container[data-id='2'] .o_hierarchy_node").click();
    expect.verifySteps(["open 2"]);
});

test("a search only displays the matching records", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        viewId: false,
        searchViewArch: `
            <search>
                <filter name="no_josephine" domain="[['id', '!=', 3]]"/>
                <filter name="find_louis" domain="[['id', '=', 4]]"/>
            </search>
        `,
    });

    await enableFilters(["no_josephine"]);
    expect(queryAllTexts(NODE_CONTENT)).toEqual(["Albert", "Louis\nJosephine", "Georges\nAlbert"], {
        message: "the records are loaded breadth-first: Louis is a root, as his manager is not displayed",
    });
    expect(getEdges()).toEqual(["1_2"], {
        message: "Louis is not linked: his manager is not displayed",
    });
    expect(`${NODE}:contains(Albert) button[title='Unfold']`).toHaveText("2 Subordinates", {
        message: "Albert has a child which is not displayed",
    });
    expect(`${NODE}:contains(Louis) button[title='Show ancestor']`).toHaveText("Show manager");

    await toggleMenuItem("no_josephine");
    await toggleMenuItem("find_louis");
    expect(queryAllTexts(NODE_CONTENT)).toEqual(["Louis\nJosephine"]);
    expect(getEdges()).toEqual([]);
});

test("unfold opens the record and its children in a new action", async () => {
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
        domain: [["id", "in", [1, 3]]],
    });

    await contains(`${NODE}:contains(Josephine) button[title='Unfold']`).click();
    expect.verifySteps([
        {
            name: "Josephine",
            res_model: "hr.employee",
            domain: ["|", ["id", "=", 3], ["parent_id", "=", 3]],
            viewType: "hierarchy",
        },
    ]);
});

test("show ancestor opens the parent and its children in a new action", async () => {
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

    await contains(`${NODE} button[title='Show ancestor']`).click();
    expect.verifySteps([
        {
            name: "Josephine",
            domain: ["|", ["id", "=", 3], ["parent_id", "=", 3]],
            viewType: "hierarchy",
        },
    ]);
});

test("show ancestor names the action after the parent, even if the card does not display it", async () => {
    mockService("action", {
        doAction(action) {
            expect.step(action.name);
        },
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        domain: [["id", "=", 4]],
        arch: `
            <hierarchy child_field="child_ids">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </hierarchy>
        `,
    });

    await contains(`${NODE} button[title='Show ancestor']`).click();
    expect.verifySteps(["Josephine"]);
});

test("cycles and records which are their own parent are displayed", async () => {
    Employee._records = [
        { id: 1, name: "Albert", parent_id: 2, child_ids: [2] },
        { id: 2, name: "Georges", parent_id: 1, child_ids: [1] },
        { id: 3, name: "Josephine", parent_id: 3, child_ids: [3] },
    ];
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect(queryAllTexts(NODE_CONTENT)).toEqual(["Josephine\nJosephine", "Albert\nGeorges", "Georges\nAlbert"], {
        message: "Josephine is a root, the cycle is broken on its first record",
    });
    expect(getEdges()).toEqual(["1_2"]);
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
                            <field name="name"/>
                            <p invisible="not child_ids" class="o_children_text">withChildren</p>
                        </t>
                    </templates>
                </hierarchy>
            `,
    });
    expect(".o_hierarchy_node_container:eq(0) .o_children_text").toHaveCount(1);
    expect(".o_hierarchy_node_container:eq(1) .o_children_text").toHaveCount(0);
    expect(".o_hierarchy_node_container:eq(2) .o_children_text").toHaveCount(1);
    expect(".o_hierarchy_node_container:eq(3) .o_children_text").toHaveCount(0);
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
    expect(".o_hierarchy_node_container:contains(Albert) .o_root_marker").toHaveCount(1);
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
                            <div><field name="name"/></div>
                            <button type="object" name="prefix_underscore">prefix</button>
                        </t>
                    </templates>
                </hierarchy>
            `,
    });
    await contains(".o_hierarchy_node_container:eq(1) button[name='prefix_underscore']").click();
    expect(queryAllTexts(NODE_CONTENT)).toEqual(
        ["Albert\nprefix", "_Georges\nprefix", "Josephine\nprefix", "Louis\nprefix"],
        { message: "The view should have reloaded the same data" }
    );
    expect(getEdges()).toEqual(["1_2", "1_3", "3_4"]);
});

test("The view displays the No Content help", async () => {
    Employee._records = [];
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect("div.o_view_nocontent").toHaveCount(1);
    expect(NODE).toHaveCount(0);
});

test("Navigate in the hierarchy and come back with the breadcrumb", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "hr.employee",
        type: "ir.actions.act_window",
        domain: [["id", "!=", 4]],
        views: [
            [false, "hierarchy"],
            [false, "form"],
        ],
    });
    expect(queryAllTexts(NODE_CONTENT)).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);

    await contains(`${NODE}:contains(Josephine) button[title='Unfold']`).click();
    expect(queryAllTexts(NODE_CONTENT)).toEqual(["Josephine\nAlbert", "Louis\nJosephine"]);
    expect(getEdges()).toEqual(["3_4"]);

    await contains(`${NODE}:contains(Louis)`).click();
    expect(".o_hierarchy_view").toHaveCount(0);
    expect(".o_form_view").toHaveCount(1);

    await contains(".o_back_button").click();
    expect(queryAllTexts(NODE_CONTENT)).toEqual(["Josephine\nAlbert", "Louis\nJosephine"], {
        message: "coming back from the form restores the level of Josephine",
    });

    await contains(".o_back_button").click();
    expect(queryAllTexts(NODE_CONTENT)).toEqual(
        ["Albert", "Georges\nAlbert", "Josephine\nAlbert"],
        { message: "the previous action is the initial one" }
    );
});

test("Open record on new window", async () => {
    patchWithCleanup(browser, {
        open: (url) => {
            expect.step(`opened in new window: ${url}`);
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

    await contains(`.o_hierarchy_node_container ${NODE}`).click({ ctrlKey: true });
    expect(".o_hierarchy_view").toHaveCount(1);
    expect(".o_form_view").toHaveCount(0);
    expect.verifySteps(["opened in new window: /odoo/hr.employee/1"]);
});

test("zoom controls", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    await contains(".o_hierarchy_zoom_level").click();
    expect(".o_hierarchy_zoom_level").toHaveText("100%");

    await contains(".o_hierarchy_controls button[title='Zoom Out']").click();
    expect(".o_hierarchy_zoom_level").toHaveText("83%");

    await contains(".o_hierarchy_controls button[title='Zoom In']").click();
    await contains(".o_hierarchy_controls button[title='Zoom In']").click();
    expect(".o_hierarchy_zoom_level").toHaveText("120%");

    await contains(".o_hierarchy_controls button[title='Fit Graph to View']").click();
    await contains(".o_hierarchy_zoom_level").click();
    expect(".o_hierarchy_zoom_level").toHaveText("100%");
});

test("the pager changes the number of loaded nodes", async () => {
    Employee._records = Array.from({ length: 81 }, (_, i) => ({
        id: i + 1,
        name: `Emp ${i + 1}`,
        parent_id: false,
        child_ids: [],
    }));
    onRpc("hierarchy_read", ({ kwargs }) => {
        expect.step(`limit ${kwargs.limit}`);
    });
    await mountView({ type: "hierarchy", resModel: "hr.employee" });

    const controlPanel = queryOne(".o_control_panel");
    expect(NODE).toHaveCount(80);
    expect(getPagerValue(controlPanel)).toEqual([1, 80]);
    expect(getPagerLimit(controlPanel)).toBe(81);
    expect(".o_pager_previous").not.toBeEnabled({ message: "cannot load less than one step" });
    expect(".o_pager_next").toBeEnabled();
    expect.verifySteps(["limit 80"]);

    await pagerNext(controlPanel);
    expect(NODE).toHaveCount(81, { message: "the nodes are added, the first ones are kept" });
    expect(getPagerValue(controlPanel)).toEqual([1, 81]);
    expect(".o_pager_previous").toBeEnabled();
    expect(".o_pager_next").not.toBeEnabled({ message: "all the records are loaded" });
    expect.verifySteps(["limit 160"]);

    await pagerPrevious(controlPanel);
    expect(NODE).toHaveCount(80);
    expect(getPagerValue(controlPanel)).toEqual([1, 80]);
    expect.verifySteps(["limit 80"]);
});

test("the nodes are loaded breadth-first, up to the limit", async () => {
    // Albert (1) has 80 subordinates (2 to 81), Georges (82) is another root
    const subordinates = Array.from({ length: 80 }, (_, i) => ({
        id: i + 2,
        name: `Emp ${i + 2}`,
        parent_id: 1,
        child_ids: [],
    }));
    Employee._records = [
        { id: 1, name: "Albert", parent_id: false, child_ids: subordinates.map(({ id }) => id) },
        ...subordinates,
        { id: 82, name: "Georges", parent_id: false, child_ids: [] },
    ];
    await mountView({ type: "hierarchy", resModel: "hr.employee" });
    expect(NODE).toHaveCount(80);
    expect(`${NODE}:contains(Georges)`).toHaveCount(1, {
        message: "the roots are loaded before the children, whatever their ids",
    });
    expect(`${NODE}:contains(Albert) button[title='Unfold']`).toHaveCount(1, {
        message: "some children of Albert are not loaded",
    });
});
