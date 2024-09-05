import { describe, expect, test } from "@odoo/hoot";
import { press, queryAllTexts, queryOne, scroll } from "@odoo/hoot-dom";
import { advanceFrame, animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    makeServerError,
    mockService,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
    removeFacet,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { HierarchyModel } from "@web_hierarchy/hierarchy_model";

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

    _records = [
        { id: 1, name: "Albert", parent_id: false, child_ids: [2, 3] },
        { id: 2, name: "Georges", parent_id: 1, child_ids: [] },
        { id: 3, name: "Josephine", parent_id: 1, child_ids: [4] },
        { id: 4, name: "Louis", parent_id: 3, child_ids: [] },
    ];

    _views = {
        hierarchy: `
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
        "hierarchy,1": `
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
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_separator").toHaveCount(1);
    expect(".o_hierarchy_line_part").toHaveCount(2);
    expect(".o_hierarchy_line_left").toHaveCount(1);
    expect(".o_hierarchy_line_right").toHaveCount(1);
    expect(".o_hierarchy_node_container").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(".o_hierarchy_node_button").toHaveCount(2);
    expect(".o_hierarchy_node_button.btn-primary").toHaveCount(1);
    expect(".o_hierarchy_node_button.btn-primary.d-grid").toHaveCount(1);
    expect(".o_hierarchy_node_button.btn-primary.rounded-0").toHaveCount(1);
    expect(".o_hierarchy_node_button.btn-primary .o_hierarchy_icon").toHaveCount(1);
    expect(".o_hierarchy_node_button.btn-primary").toHaveText("Unfold\n1");

    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node").toHaveCount(1);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node_content").toHaveText("Albert");
    expect(".o_hierarchy_node_button.btn-secondary").toHaveCount(1);
    expect(".o_hierarchy_node_button.btn-secondary").toHaveText("Fold");
});

test("display child nodes", async () => {
    onRpc("search_read", () => {
        expect.step("get child data");
    });
    onRpc("read_group", () => {
        expect.step("fetch descendants");
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node_button").toHaveCount(2);
    expect(".o_hierarchy_node_button.btn-secondary").toHaveCount(1);
    expect(".o_hierarchy_node_button.btn-primary").toHaveCount(1);
    await contains(".o_hierarchy_node_button.btn-primary").click();
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_separator").toHaveCount(2);
    expect(".o_hierarchy_line_part").toHaveCount(4);
    expect(".o_hierarchy_line_left").toHaveCount(2);
    expect(".o_hierarchy_line_right").toHaveCount(2);
    expect(".o_hierarchy_node_container").toHaveCount(4);
    expect(".o_hierarchy_node").toHaveCount(4);
    expect(".o_hierarchy_node_button").toHaveCount(2);
    expect(".o_hierarchy_node_button.btn-primary").toHaveCount(0);
    expect(".o_hierarchy_node_button.btn-secondary").toHaveCount(2);
    expect(".o_hierarchy_node_button.btn-secondary").toHaveText("Fold");
    // check nodes in each row
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node").toHaveCount(1);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node_content").toHaveText("Albert");

    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_row:eq(1) .o_hierarchy_node_content")).toEqual([
        // Name + Parent name
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);

    expect(".o_hierarchy_row:eq(2) .o_hierarchy_node").toHaveCount(1);
    expect(".o_hierarchy_row:eq(2) .o_hierarchy_node_content").toHaveText("Louis\nJosephine");
    expect.verifySteps(["get child data", "fetch descendants"]);
});

test("display child nodes with child_field set on the view", async () => {
    onRpc("search_read", () => {
        expect.step("get child data with descendants");
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        viewId: 1,
    });

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node_button").toHaveCount(2);
    expect(".o_hierarchy_node_button.btn-secondary").toHaveCount(1);
    expect(".o_hierarchy_node_button.btn-primary").toHaveCount(1);
    await contains(".o_hierarchy_node_button.btn-primary").click();
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_separator").toHaveCount(2);
    expect(".o_hierarchy_line_part").toHaveCount(4);
    expect(".o_hierarchy_line_left").toHaveCount(2);
    expect(".o_hierarchy_line_right").toHaveCount(2);
    expect(".o_hierarchy_node_container").toHaveCount(4);
    expect(".o_hierarchy_node").toHaveCount(4);
    expect(".o_hierarchy_node_button").toHaveCount(2);
    expect(".o_hierarchy_node_button.btn-primary").toHaveCount(0);
    expect(".o_hierarchy_node_button.btn-secondary").toHaveCount(2);
    expect.verifySteps(["get child data with descendants"]);
});

test("collapse child nodes", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_separator").toHaveCount(1);
    expect(".o_hierarchy_line_part").toHaveCount(2);
    expect(".o_hierarchy_line_left").toHaveCount(1);
    expect(".o_hierarchy_line_right").toHaveCount(1);
    expect(".o_hierarchy_node_container").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(3);
    await contains(".o_hierarchy_node_button.btn-secondary").click();
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_separator").toHaveCount(0);
    expect(".o_hierarchy_line_part").toHaveCount(0);
    expect(".o_hierarchy_line_left").toHaveCount(0);
    expect(".o_hierarchy_line_right").toHaveCount(0);
    expect(".o_hierarchy_node_container").toHaveCount(1);
    expect(".o_hierarchy_node").toHaveCount(1);
    expect(".o_hierarchy_node_button.btn-secondary").toHaveCount(0);
    expect(".o_hierarchy_node_button").toHaveCount(1);
    expect(".o_hierarchy_node_container:not(.o_hierarchy_node_button)").toHaveCount(1);
    expect(queryAllTexts(".o_hierarchy_row .o_hierarchy_node_content")).toEqual(["Albert"]);
});

test("display the parent above the line when many records on the parent row", async () => {
    Employee._records.push({
        name: "Alfred",
        parent_id: false,
        child_ids: [],
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_separator").toHaveCount(0);
    expect(".o_hierarchy_node").toHaveCount(2);
    expect(".o_hierarchy_node_button.btn-primary").toHaveCount(1);
    await contains(".o_hierarchy_node_button.btn-primary").click();
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_separator").toHaveCount(1);
    expect(".o_hierarchy_line_left").toHaveCount(1);
    expect(".o_hierarchy_line_right").toHaveCount(1);
    expect(".o_hierarchy_parent_node_container").toHaveCount(1);
    expect(".o_hierarchy_parent_node_container").toHaveText("Albert");
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
        arch: Employee._views["hierarchy,false"],
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
    expect(".o_hierarchy_node").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(["B", "D\nB"], {
        message: `A (and F) should be hidden by the globalDomain, C is hidden because of the search_default and
            E (and F) are hidden because the custom domain leaf [['parent_id', '=', false]] is applied
            since the view is in its "default state", D is shown because the query has only one result (B) so
            its direct children are also fetched`,
    });
    await removeFacet("exclude_third");
    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(["B", "C"], {
        message: `C is now visible because the search_default was removed. E (and F) are still hidden because
            the custom domain leaf [['parent_id', '=', false]] is also applied when the search query is
            empty, D is hidden because the query now has more than one "root" record (B and C)`,
    });
    await enableFilters(["find_fifth"]);
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(["D\nB", "E\nD", "F\nD"], {
        message: `E is shown because it matches the query and the custom domain leaf [['parent_id', '=', false]]
            is not applied since the view is not in its "default state", nor is the query empty. D and F are
            shown since E was the only record matching the query, so its parent and siblings are fetched`,
    });
    await removeFacet("find_fifth");
    await enableFilters(["exclude_third"]);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(["B", "D\nB"], {
        message: `Manually going back to the "default state" of the view should give the same result as the
            first load.`,
    });
});

test("search record in hierarchy view", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        arch: Employee._views["hierarchy,false"],
        searchViewArch: `
            <search>
                <filter name="test_filter" domain="[['id', '=', 4]]"/>
            </search>
        `,
    });
    await enableFilters(["test_filter"]);

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(2);
    expect(".o_hierarchy_separator").toHaveCount(1);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);
});

test("search record in hierarchy view with child field name defined in the arch", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        viewId: 1,
        arch: Employee._views["hierarchy,false"],
        searchViewArch: `
            <search>
                <filter name="test_filter" domain="[['id', '=', 4]]"/>
            </search>
        `,
    });
    await enableFilters(["test_filter"]);

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(2);
    expect(".o_hierarchy_separator").toHaveCount(1);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);
});

test("fetch parent record", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        arch: Employee._views["hierarchy,false"],
        searchViewArch: `
            <search>
                <filter name="test_filter" domain="[['id', '=', 4]]"/>
            </search>
        `,
    });
    await enableFilters(["test_filter"]);

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(2);
    expect(".o_hierarchy_separator").toHaveCount(1);

    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node_content").toHaveText("Josephine\nAlbert");

    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node_content").toHaveText("Louis\nJosephine");
    expect(".o_hierarchy_node_container button .fa-chevron-up").toHaveCount(1, {
        message:
            "Button to fetch the parent node should be visible on the first node displayed in the view.",
    });
    await contains(".o_hierarchy_node_container button .fa-chevron-up").click();
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(4);
    expect(".o_hierarchy_separator").toHaveCount(2);

    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node_content").toHaveText("Albert");
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_row:eq(1) .o_hierarchy_node_content")).toEqual([
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);

    expect(".o_hierarchy_row:eq(2) .o_hierarchy_node_content").toHaveText("Louis\nJosephine");
});

test("fetch parent when there are many records without the same parent in the same row", async () => {
    Employee._records.push({
        id: 5,
        name: "Lisa",
        parent_id: 2,
        child_ids: [],
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        arch: Employee._views["hierarchy,false"],
        searchViewArch: `
            <search>
                <filter name="test_filter" domain="[['name', 'ilike', 'l']]"/>
            </search>
        `,
    });
    await enableFilters(["test_filter"]);

    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node_container").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Lisa\nGeorges",
        "Louis\nJosephine",
        "Albert",
    ]);
    expect(".o_hierarchy_node_container button .fa-chevron-up").toHaveCount(2);
    await contains(".o_hierarchy_node_container button .fa-chevron-up").click();
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Georges\nAlbert",
        "Lisa\nGeorges",
    ]);
    expect(".o_hierarchy_node_container button .fa-chevron-up").toHaveCount(1);
    await contains(".o_hierarchy_node_container button .fa-chevron-up").click();
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(4);
});

test("fetch parent when parent record is in the same row", async () => {
    Employee._records.push({
        id: 5,
        name: "Lisa",
        parent_id: 2,
        child_ids: [],
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        arch: Employee._views["hierarchy,false"],
        searchViewArch: `
            <search>
                <filter name="test_filter" domain="[['id', 'in', [1, 2, 3, 4, 5]]]"/>
            </search>
        `,
    });
    await enableFilters(["test_filter"]);

    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node_container").toHaveCount(5);
    expect(".o_hierarchy_node_container button .fa-chevron-up").toHaveCount(4);
    await contains(".o_hierarchy_node_container button .fa-chevron-up").click();
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);
});

test("fetch parent of node with children displayed", async () => {
    Employee._records.push({
        id: 5,
        name: "Lisa",
        parent_id: 2,
        child_ids: [],
    });
    Employee._records.find((rec) => rec.id === 2).child_ids.push(5);
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        arch: Employee._views["hierarchy,false"],
        searchViewArch: `
            <search>
                <filter name="test_filter" domain="[['id', 'in', [1, 2, 3, 4, 5]]]"/>
            </search>
        `,
    });
    await enableFilters(["test_filter"]);

    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node_container").toHaveCount(5);
    expect(".o_hierarchy_node_container button .fa-chevron-up").toHaveCount(4);
    const georgesNode = queryOne(
        ".o_hierarchy_node_container:has(button[name=hierarchy_search_parent_node]):eq(0)"
    );
    expect(queryOne(".o_hierarchy_node_content", { root: georgesNode })).toHaveText(
        "Georges\nAlbert"
    );
    await contains(
        queryOne("button[name=hierarchy_search_subsidiaries]", { root: georgesNode })
    ).click();
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(5);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node").toHaveCount(4);
    expect(queryAllTexts(".o_hierarchy_row:eq(0) .o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node").toHaveCount(1);
    expect(".o_hierarchy_row:eq(1) .o_hierarchy_node_content").toHaveText("Lisa\nGeorges");
    await contains(".o_hierarchy_node_container button .fa-chevron-up").click();
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(4);
});

test("drag and drop is disabled by default", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);

    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node_content").toHaveText(
        "Georges\nAlbert"
    );

    await contains(".o_hierarchy_node_container:eq(1) .o_hierarchy_node").dragAndDrop(
        ".o_hierarchy_row:first-child"
    );

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);
});

test("drag and drop record on another row", async () => {
    Employee._views["hierarchy,false"] = Employee._views["hierarchy,false"].replace(
        "<hierarchy>",
        "<hierarchy draggable='1'>"
    );
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);
    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node_content").toHaveText(
        "Georges\nAlbert"
    );

    await contains(".o_hierarchy_node_container:eq(1) .o_hierarchy_node").dragAndDrop(
        ".o_hierarchy_row:first-child"
    );

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(
        ["Albert", "Georges", "Josephine\nAlbert"],
        { message: "Georges should no longer have a manager" }
    );
});

test("drag and drop record at an invalid position", async () => {
    expect.assertions(8);
    Employee._views["hierarchy,false"] = Employee._views["hierarchy,false"].replace(
        "<hierarchy>",
        "<hierarchy draggable='1'>"
    );
    patchWithCleanup(HierarchyModel.prototype, {
        async updateParentId(node, parentResId = false) {
            return this.orm.call(this.resModel, "custom_update_parent_id", [node.resId], {
                parent_id: parentResId,
            });
        },
        async updateParentNode() {
            await expect(super.updateParentNode(...arguments)).rejects.toThrow(
                makeServerError({
                    type: "ValidationError",
                    description: "Prevented update parent",
                })
            );
        },
    });
    onRpc("custom_update_parent_id", () => {
        throw makeServerError({
            type: "ValidationError",
            description: "Prevented update parent",
        });
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);

    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node_content").toHaveText(
        "Georges\nAlbert"
    );

    await contains(".o_hierarchy_node_container:eq(1) .o_hierarchy_node").dragAndDrop(
        ".o_hierarchy_row:first-child"
    );

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(
        ["Albert", "Georges\nAlbert", "Josephine\nAlbert"],
        { message: "The view should not have been modified since the position is invalid" }
    );
});

test("drag and drop record on sibling node", async () => {
    Employee._views["hierarchy,false"] = Employee._views["hierarchy,false"].replace(
        "<hierarchy>",
        "<hierarchy draggable='1'>"
    );
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);

    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node_content").toHaveText(
        "Georges\nAlbert"
    );
    expect(".o_hierarchy_node_container:eq(2) .o_hierarchy_node_content").toHaveText(
        "Josephine\nAlbert"
    );

    await contains(".o_hierarchy_node_container:eq(1) .o_hierarchy_node").dragAndDrop(
        ".o_hierarchy_node_container:eq(2)"
    );

    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(4);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(
        ["Albert", "Josephine\nAlbert", "Georges\nJosephine", "Louis\nJosephine"],
        { message: "Georges should have Josephine as manager" }
    );
});

test("drag and drop record on node of another tree", async () => {
    Employee._views["hierarchy,1"] = Employee._views["hierarchy,1"].replace(
        `<hierarchy child_field="child_ids">`,
        `<hierarchy child_field="child_ids" draggable="1">`
    );
    Employee._records = [
        { id: 1, name: "A", parent_id: false, child_ids: [3, 4] },
        { id: 2, name: "B", parent_id: false, child_ids: [] },
        { id: 3, name: "C", parent_id: 1, child_ids: [5] },
        { id: 4, name: "D", parent_id: 1, child_ids: [] },
        { id: 5, name: "E", parent_id: 3, child_ids: [] },
    ];
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        viewId: 1,
    });

    expect(".o_hierarchy_row").toHaveCount(1);
    await contains(".o_hierarchy_node_button.btn-primary").click();
    expect(".o_hierarchy_row").toHaveCount(2);
    await contains(".o_hierarchy_node_button.btn-primary").click();
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_row .o_hierarchy_node_content")).toEqual([
        "A",
        "B",
        "C\nA",
        "D\nA",
        "E\nC",
    ]);

    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node_content").toHaveText("B");
    expect(".o_hierarchy_node_container:eq(3) .o_hierarchy_node_content").toHaveText("D\nA");

    await contains(".o_hierarchy_node_container:eq(3) .o_hierarchy_node").dragAndDrop(
        ".o_hierarchy_node_container:eq(1)"
    );

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_row .o_hierarchy_node_content")).toEqual(["A", "B", "D\nB"]);

    expect(".o_hierarchy_node_container:eq(0) .o_hierarchy_node_content").toHaveText("A");

    await contains(
        ".o_hierarchy_node_container:eq(0) .o_hierarchy_node_button.btn-primary"
    ).click();

    expect(".o_hierarchy_node_container:eq(2) .o_hierarchy_node_content").toHaveText("C\nA");

    await contains(
        ".o_hierarchy_node_container:eq(2) .o_hierarchy_node_button.btn-primary"
    ).click();

    expect(queryAllTexts(".o_hierarchy_row .o_hierarchy_node_content")).toEqual(
        ["A", "B", "C\nA", "E\nC"],
        {
            message:
                "Nodes that were folded as a result of the drop operation should all still be unfoldable",
        }
    );
});

test("drag and drop node unfolded on first row", async () => {
    Employee._views["hierarchy,false"] = Employee._views["hierarchy,false"].replace(
        "<hierarchy>",
        "<hierarchy draggable='1'>"
    );
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);

    expect(".o_hierarchy_node_container:eq(2) .o_hierarchy_node_content").toHaveText(
        "Josephine\nAlbert"
    );
    await contains(
        ".o_hierarchy_node_container:eq(2) button[name='hierarchy_search_subsidiaries']"
    ).click();

    await contains(".o_hierarchy_node_container:eq(2) .o_hierarchy_node").dragAndDrop(
        ".o_hierarchy_row:first-child"
    );

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(
        ["Albert", "Josephine", "Louis\nJosephine"],
        { message: "Georges should have Josephine as manager" }
    );

    expect(".o_hierarchy_node_container:eq(2) .o_hierarchy_node_content").toHaveText(
        "Louis\nJosephine"
    );
    await contains(".o_hierarchy_node_container:eq(2) .o_hierarchy_node").dragAndDrop(
        ".o_hierarchy_row:first-child"
    );

    expect(".o_hierarchy_row").toHaveCount(1);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(["Albert", "Josephine", "Louis"], {
        message: "Louis should still be draggable after being dragged along with Josephine",
    });
});

test("drag and drop node when other node is unfolded on first row", async () => {
    Employee._views["hierarchy,false"] = Employee._views["hierarchy,false"].replace(
        "<hierarchy>",
        "<hierarchy draggable='1'>"
    );
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);

    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node_content").toHaveText(
        "Georges\nAlbert"
    );
    expect(".o_hierarchy_node_container:eq(2) .o_hierarchy_node_content").toHaveText(
        "Josephine\nAlbert"
    );
    await contains(
        ".o_hierarchy_node_container:eq(2) button[name='hierarchy_search_subsidiaries']"
    ).click();

    await contains(".o_hierarchy_node_container:eq(1) .o_hierarchy_node").dragAndDrop(
        ".o_hierarchy_row:eq(0)"
    );

    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(4);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(
        ["Albert", "Georges", "Josephine\nAlbert", "Louis\nJosephine"],
        { message: "Georges should no longer have a manager" }
    );
});

test("drag and drop node unfolded on another row", async () => {
    Employee._views["hierarchy,false"] = Employee._views["hierarchy,false"].replace(
        "<hierarchy>",
        "<hierarchy draggable='1'>"
    );
    Employee._records = [
        { id: 1, name: "Albert", parent_id: false, child_ids: [2] },
        { id: 2, name: "Georges", parent_id: 1, child_ids: [3] },
        { id: 3, name: "Josephine", parent_id: 2, child_ids: [4] },
        { id: 4, name: "Louis", parent_id: 3, child_ids: [] },
        { id: 5, name: "Kelly", parent_id: 2, child_ids: [] },
    ];
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(2);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(["Albert", "Georges\nAlbert"]);

    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node_content").toHaveText(
        "Georges\nAlbert"
    );
    await contains(
        ".o_hierarchy_node_container:eq(1) button[name='hierarchy_search_subsidiaries']"
    ).click();

    expect(".o_hierarchy_node_container:eq(2) .o_hierarchy_node_content").toHaveText(
        "Josephine\nGeorges"
    );
    await contains(
        ".o_hierarchy_node_container:eq(2) button[name='hierarchy_search_subsidiaries']"
    ).click();

    expect(".o_hierarchy_node_container:eq(2) .o_hierarchy_node_content").toHaveText(
        "Josephine\nGeorges"
    );
    expect(".o_hierarchy_node_container:eq(4) .o_hierarchy_node_content").toHaveText(
        "Louis\nJosephine"
    );
    expect(".o_hierarchy_row").toHaveCount(4);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(
        ["Albert", "Georges\nAlbert", "Josephine\nGeorges", "Kelly\nGeorges", "Louis\nJosephine"],
        { message: "Kelly should be displayed" }
    );

    await contains(".o_hierarchy_node_container:eq(2) .o_hierarchy_node").dragAndDrop(
        ":nth-child(2 of .o_hierarchy_row)"
    );

    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(4);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(
        ["Albert", "Georges\nAlbert", "Josephine\nAlbert", "Louis\nJosephine"],
        { message: "Josephine should have Albert as a manager and Kelly should be hidden" }
    );

    expect(".o_hierarchy_node_container:eq(3) .o_hierarchy_node_content").toHaveText(
        "Louis\nJosephine"
    );

    await contains(".o_hierarchy_node_container:eq(3) .o_hierarchy_node").dragAndDrop(
        ":nth-child(2 of .o_hierarchy_row)"
    );

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(4);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(
        ["Albert", "Georges\nAlbert", "Josephine\nAlbert", "Louis\nAlbert"],
        { message: "Louis should still be draggable after being dragged along with Josephine" }
    );
});

test("drag and drop node as a child of a sibling of its parent", async () => {
    Employee._views["hierarchy,1"] = Employee._views["hierarchy,1"].replace(
        `<hierarchy child_field="child_ids">`,
        `<hierarchy child_field="child_ids" draggable="1">`
    );
    Employee._records = [
        { id: 1, name: "A", parent_id: false, child_ids: [2, 3] },
        { id: 2, name: "B", parent_id: 1, child_ids: [4, 5] },
        { id: 3, name: "C", parent_id: 1, child_ids: [] },
        { id: 4, name: "D", parent_id: 2, child_ids: [] },
        { id: 5, name: "E", parent_id: 2, child_ids: [] },
    ];
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        viewId: 1,
    });
    expect(".o_hierarchy_row").toHaveCount(2);
    await contains(".o_hierarchy_node_button.btn-primary").click();
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_row .o_hierarchy_node_content")).toEqual([
        "A",
        "B\nA",
        "C\nA",
        "D\nB",
        "E\nB",
    ]);

    expect(".o_hierarchy_node_container:eq(2) .o_hierarchy_node_content").toHaveText("C\nA");
    expect(".o_hierarchy_node_container:eq(4) .o_hierarchy_node_content").toHaveText("E\nB");

    await contains(".o_hierarchy_node_container:eq(4) .o_hierarchy_node").dragAndDrop(
        ".o_hierarchy_node_container:eq(2)"
    );
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_row .o_hierarchy_node_content")).toEqual(
        ["A", "B\nA", "C\nA", "E\nC"],
        { message: "B should be folded and C unfolded" }
    );
});

test("drag and drop record and respect ordering", async () => {
    Employee._views["hierarchy,false"] = Employee._views["hierarchy,false"].replace(
        "<hierarchy>",
        "<hierarchy default_order='name' draggable='1'>"
    );
    Employee._records = [
        { id: 1, name: "F", parent_id: false, child_ids: [] },
        { id: 2, name: "E", parent_id: 6, child_ids: [] },
        { id: 3, name: "D", parent_id: 6, child_ids: [] },
        { id: 4, name: "C", parent_id: 6, child_ids: [] },
        { id: 5, name: "B", parent_id: 6, child_ids: [] },
        { id: 6, name: "A", parent_id: false, child_ids: [2, 3, 4, 5] },
    ];
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect(".o_hierarchy_row").toHaveCount(1);
    await contains(".o_hierarchy_node_button.btn-primary").click();

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(6);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "A",
        "F",
        "B\nA",
        "C\nA",
        "D\nA",
        "E\nA",
    ]);

    await contains(".o_hierarchy_node_container:eq(4) .o_hierarchy_node").dragAndDrop(
        ".o_hierarchy_row:first-child"
    );

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(6);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "A",
        "D",
        "F",
        "B\nA",
        "C\nA",
        "E\nA",
    ]);

    await contains(".o_hierarchy_node_container:eq(1) .o_hierarchy_node").dragAndDrop(
        ":nth-child(2 of .o_hierarchy_row)"
    );

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(6);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "A",
        "F",
        "B\nA",
        "C\nA",
        "D\nA",
        "E\nA",
    ]);
});

test("drag node and move it on a row", async () => {
    Employee._views["hierarchy,false"] = Employee._views["hierarchy,false"].replace(
        "<hierarchy>",
        "<hierarchy draggable='1'>"
    );
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect(".o_hierarchy_node").toHaveCount(3);
    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node_content").toHaveText(
        "Georges\nAlbert"
    );
    const { drop, moveTo } = await contains(
        ".o_hierarchy_node_container:eq(1) .o_hierarchy_node"
    ).drag();

    await moveTo(".o_hierarchy_row:eq(0)");
    expect(".o_hierarchy_node_container:eq(1)").toHaveClass("o_hierarchy_dragged");
    expect(".o_hierarchy_row:eq(0)").toHaveClass("o_hierarchy_hover");

    await drop();
    expect(".o_hierarchy_node.o_hierarchy_dragged").toHaveCount(0);
    expect(".o_hierarchy_row.o_hierarchy_hover").toHaveCount(0);
});

test("drag node and move it on another node", async () => {
    Employee._views["hierarchy,false"] = Employee._views["hierarchy,false"].replace(
        "<hierarchy>",
        "<hierarchy draggable='1'>"
    );
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect(".o_hierarchy_node").toHaveCount(3);
    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node_content").toHaveText(
        "Georges\nAlbert"
    );
    expect(".o_hierarchy_node_container:eq(2) .o_hierarchy_node_content").toHaveText(
        "Josephine\nAlbert"
    );

    const { drop, moveTo } = await contains(
        ".o_hierarchy_node_container:eq(1) .o_hierarchy_node"
    ).drag();

    await moveTo(".o_hierarchy_node_container:eq(2) .o_hierarchy_node");
    expect(".o_hierarchy_node_container:eq(1)").toHaveClass("o_hierarchy_dragged");
    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node").toHaveClass("shadow");
    expect(".o_hierarchy_node_container:eq(2)").toHaveClass("o_hierarchy_hover");

    await drop();
    expect(".o_hierarchy_node.o_hierarchy_dragged").toHaveCount(0);
    expect(".o_hierarchy_node.o_hierarchy_hover").toHaveCount(0);
    expect(".o_hierarchy_node.shadow").toHaveCount(0);
});

test("drag node to scroll", async () => {
    Employee._views["hierarchy,false"] = Employee._views["hierarchy,false"].replace(
        "<hierarchy>",
        "<hierarchy draggable='1'>"
    );
    Employee._records = [
        { id: 1, name: "A", parent_id: false, child_ids: [2] },
        { id: 2, name: "B", parent_id: 1, child_ids: [3] },
        { id: 3, name: "C", parent_id: 2, child_ids: [4] },
        { id: 4, name: "D", parent_id: 3, child_ids: [5] },
        { id: 5, name: "E", parent_id: 4, child_ids: [] },
        { id: 6, name: "F", parent_id: false, child_ids: [] },
    ];
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    // Fully open the view
    expect(".o_hierarchy_row").toHaveCount(1);
    await contains(".o_hierarchy_node_button.btn-primary").click();
    expect(".o_hierarchy_row").toHaveCount(2);
    await contains(".o_hierarchy_node_button.btn-primary").click();
    expect(".o_hierarchy_row").toHaveCount(3);
    await contains(".o_hierarchy_node_button.btn-primary").click();
    expect(".o_hierarchy_row").toHaveCount(4);
    await contains(".o_hierarchy_node_button.btn-primary").click();
    expect(".o_hierarchy_row").toHaveCount(5);
    expect(queryAllTexts(".o_hierarchy_row .o_hierarchy_node_content")).toEqual([
        "A",
        "F",
        "B\nA",
        "C\nB",
        "D\nC",
        "E\nD",
    ]);
    await animationFrame();
    const content = queryOne(".o_content");
    await scroll(content, { top: 0 });

    // Limit the height and enable scrolling
    content.setAttribute("style", "min-height:600px;max-height:600px;overflow-y:auto;");
    expect(content.scrollTop).toBe(0);
    expect(content).toHaveRect({ height: 600 });

    const dragActions = await contains(".o_hierarchy_node:contains(F)").drag();
    await dragActions.moveTo(".o_hierarchy_row:eq(4)");
    await animationFrame();

    expect(content.scrollTop).toBeGreaterThan(0);
    expect(".o_hierarchy_node_container.o_hierarchy_dragged").toHaveCount(1);

    await advanceFrame(50);

    // should be at the end of the content
    expect(content.clientHeight + content.scrollTop).toBe(content.scrollHeight);

    await dragActions.moveTo(".o_hierarchy_row:eq(0)");
    await animationFrame();

    expect(content.clientHeight + content.scrollTop).toBeLessThan(content.scrollHeight);
    expect(".o_hierarchy_node_container.o_hierarchy_dragged").toHaveCount(1);

    await advanceFrame(50);

    // should be at the top of the content
    expect(content.scrollTop).toBe(0);

    // cancel drag: press "Escape"
    await press("Escape");
    await animationFrame();

    expect(".o_hierarchy_node_container.o_hierarchy_dragged").toHaveCount(0);
});

test("check default icon is correctly used inside button to display child nodes", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect(".o_hierarchy_node button[name=hierarchy_search_subsidiaries].btn-primary").toHaveCount(
        1
    );
    expect(".o_hierarchy_node button[name=hierarchy_search_subsidiaries].btn-primary").toHaveText(
        "Unfold\n1"
    );
    expect(
        ".o_hierarchy_node button[name=hierarchy_search_subsidiaries] i.fa-share-alt.o_hierarchy_icon"
    ).toHaveCount(1, {
        message:
            "The default icon of the hierarchy view should be displayed inside the button to unfold the node.",
    });
});

test("use other icon used next to Unfold string displayed inside the button", async () => {
    Employee._views["hierarchy,false"] = Employee._views["hierarchy,false"].replace(
        "<hierarchy>",
        "<hierarchy icon='fa-users'>"
    );
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect(".o_hierarchy_node button[name=hierarchy_search_subsidiaries].btn-primary").toHaveCount(
        1
    );
    expect(".o_hierarchy_node button[name=hierarchy_search_subsidiaries].btn-primary").toHaveText(
        "Unfold\n1"
    );
    expect(".o_hierarchy_node button[name=hierarchy_search_subsidiaries] i.fa-users").toHaveCount(
        1,
        {
            message:
                "The icon defined in the attribute icon in hierarchy tag should be displayed inside the button to unfold the node instead of the default one.",
        }
    );
});

test("use `hierarchy_res_id` context to load the view at that specific node with its siblings and parent node", async () => {
    Employee._records.push({
        id: 5,
        name: "Lisa",
        parent_id: 3,
        child_ids: [],
    });
    Employee._records.find((rec) => rec.id === 3).child_ids.push(5);
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        context: {
            hierarchy_res_id: 5,
        },
    });

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Josephine\nAlbert",
        "Lisa\nJosephine",
        "Louis\nJosephine",
    ]);
    expect(".o_hierarchy_node_container button[name=hierarchy_search_parent_node]").toHaveCount(1);
});

test("cannot set the record dragged as parent", async () => {
    Employee._views["hierarchy,false"] = Employee._views["hierarchy,false"].replace(
        "<hierarchy>",
        "<hierarchy draggable='1'>"
    );
    onRpc("hr.employee", "write", () => {
        expect.step("setManager");
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);
    await contains(".o_hierarchy_node:eq(0)").dragAndDrop(".o_hierarchy_row:eq(1)");
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_bar.bg-danger").toHaveCount(1);

    expect.verifySteps([]);
});

test("cannot create cyclic", async () => {
    Employee._views["hierarchy,false"] = Employee._views["hierarchy,false"].replace(
        "<hierarchy>",
        "<hierarchy draggable='1'>"
    );
    onRpc("hr.employee", "write", () => {
        expect.step("setManager");
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);
    await contains(".o_hierarchy_node:eq(0)").dragAndDrop(".o_hierarchy_node:eq(1)");
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
    ]);
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_bar.bg-danger").toHaveCount(1);

    await contains(".o_hierarchy_node_button.btn-primary").click();
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(4);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);
    await contains(".o_hierarchy_node:eq(0)").dragAndDrop(".o_hierarchy_node:eq(3)");
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(4);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);
    expect(".o_notification").toHaveCount(2);
    expect(".o_notification_bar.bg-danger").toHaveCount(2);

    await contains(".o_hierarchy_node:eq(0)").dragAndDrop(".o_hierarchy_row:eq(2)");
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(4);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert",
        "Georges\nAlbert",
        "Josephine\nAlbert",
        "Louis\nJosephine",
    ]);
    expect(".o_notification").toHaveCount(3);
    expect(".o_notification_bar.bg-danger").toHaveCount(3);

    expect.verifySteps([]);
});

test("can properly evaluate invisible elements in a hierarchy card", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        arch: `
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
                            <div invisible="not child_ids" class="o_children_text">
                                <p>withChildren</p>
                            </div>
                        </t>
                    </templates>
                </hierarchy>
            `,
    });
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(".o_hierarchy_node_container:eq(0) .o_hierarchy_node_content").toHaveText(
        "Albert\n\nwithChildren"
    );
    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node_content").toHaveText(
        "Georges\nAlbert"
    );
    expect(".o_hierarchy_node_container:eq(2) .o_hierarchy_node_content").toHaveText(
        "Josephine\nAlbert\n\nwithChildren"
    );
    expect(".o_hierarchy_node_container:eq(0) .o_children_text").toHaveCount(1);
    expect(".o_hierarchy_node_container:eq(1) .o_children_text").toHaveCount(0);
    expect(".o_hierarchy_node_container:eq(2) .o_children_text").toHaveCount(1);
});

test("Reload the view with the same unfolded records when clicking with a view button", async () => {
    mockService("action", {
        doActionButton({ resId, onClose }) {
            const record = Employee._records[resId - 1];
            record.name = "_" + record.name;
            onClose();
        },
    });
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
        arch: `
                <hierarchy child_field="child_ids">
                    <templates>
                        <t t-name="hierarchy-box">
                            <div class="o_hierarchy_node_header">
                                <field name="name"/>
                            </div>
                            <div class="o_hierarchy_node_body">
                                <field name="parent_id"/>
                            </div>
                            <button type="object" name="prefix_underscore">prefix</button>
                        </t>
                    </templates>
                </hierarchy>
            `,
    });
    await contains(".o_hierarchy_node_button.btn-primary").click();
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(4);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual([
        "Albert\nprefix",
        "Georges\nAlbert\nprefix",
        "Josephine\nAlbert\nprefix",
        "Louis\nJosephine\nprefix",
    ]);
    expect(".o_hierarchy_node_container:eq(1) .o_hierarchy_node_content").toHaveText(
        "Georges\nAlbert\nprefix"
    );
    await contains(".o_hierarchy_node_container:eq(1) button[name='prefix_underscore']").click();
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(4);
    expect(queryAllTexts(".o_hierarchy_node_content")).toEqual(
        [
            "Albert\nprefix",
            "_Georges\nAlbert\nprefix",
            "Josephine\nAlbert\nprefix",
            "Louis\nJosephine\nprefix",
        ],
        { message: "The view should have reloaded the same data (with Louis)" }
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
