import {
    defineDocumentSpreadsheetModels,
    getBasicData,
    getBasicServerData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { createSpreadsheetFromPivotView } from "@documents_spreadsheet/../tests/helpers/pivot_helpers";
import { getHighlightsFromStore } from "@documents_spreadsheet/../tests/helpers/store_helpers";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { registries } from "@odoo/o-spreadsheet";
import { Partner, getBasicPivotArch } from "@spreadsheet/../tests/helpers/data";
import {
    getZoneOfInsertedDataSource,
    insertPivotInSpreadsheet,
} from "@spreadsheet/../tests/helpers/pivot";
import * as dsHelpers from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import { contains, fields, makeServerError, onRpc } from "@web/../tests/web_test_helpers";

defineDocumentSpreadsheetModels();
describe.current.tags("desktop");

const { coreViewsPluginRegistry } = registries;

let target;

beforeEach(() => {
    target = getFixture();
});

test("Open pivot properties", async function () {
    const { env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                            <pivot string="Partner" display_quantity="true">
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    expect(".o-sidePanel").toHaveCount(1);
});

test("Pivot properties panel shows ascending sorting", async function () {
    const { env, pivotId } = await createSpreadsheetFromPivotView({
        actions: async (target) => {
            await contains("thead .o_pivot_measure_row").click();
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();

    const sections = target.querySelectorAll(".o_spreadsheet_pivot_side_panel div .o-section");
    expect(sections.length).toBe(6, { message: "it should have 6 sections" });
    const pivotSorting = sections[4];

    expect(pivotSorting.children[0]).toHaveText("Sorting");
    expect(pivotSorting.children[1]).toHaveText("Probability (ascending)");
});

test("Pivot properties panel shows descending sorting", async function () {
    const { pivotId, env } = await createSpreadsheetFromPivotView({
        actions: async (target) => {
            await contains("thead .o_pivot_measure_row").click();
            await contains("thead .o_pivot_measure_row").click();
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();

    const sections = target.querySelectorAll(".o_spreadsheet_pivot_side_panel div .o-section");
    expect(sections.length).toBe(6, { message: "it should have 6 sections" });
    const pivotSorting = sections[4];

    expect(pivotSorting.children[0]).toHaveText("Sorting");
    expect(pivotSorting.children[1]).toHaveText("Probability (descending)");
});

test("Removing the measure removes the sortedColumn", async function () {
    const { env, pivotId, model } = await createSpreadsheetFromPivotView({
        actions: async () => {
            await contains("thead .o_pivot_measure_row").click();
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    expect(model.getters.getPivot(pivotId).definition.sortedColumn).not.toBe(undefined);

    await contains(".pivot-measure .fa-trash").click();
    expect(model.getters.getPivot(pivotId).definition.sortedColumn).toBe(undefined);
});

test("Removing a column removes the sortedColumn", async function () {
    const { env, pivotId, model } = await createSpreadsheetFromPivotView({
        actions: async () => {
            await contains("thead .o_pivot_measure_row").click();
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();

    expect(model.getters.getPivot(pivotId).definition.sortedColumn).not.toBe(undefined);
    await contains(".pivot-dimension .fa-trash").click();
    expect(model.getters.getPivot(pivotId).definition.sortedColumn).toBe(undefined);
});

test("Open pivot properties properties with non-loaded field", async function () {
    const PivotUIPlugin = coreViewsPluginRegistry.get("pivot_ui");
    const { model, env, pivotId } = await createSpreadsheetFromPivotView();
    const pivotPlugin = model["handlers"].find((handler) => handler instanceof PivotUIPlugin);
    const dataSource = Object.values(pivotPlugin.pivots)[0];
    // remove all loading promises and the model to simulate the data source is not loaded
    dataSource._loadPromise = undefined;
    dataSource._createModelPromise = undefined;
    dataSource._model = undefined;
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    expect(".o-sidePanel").toHaveCount(1);
});

test("Update the pivot title from the side panel", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    const target = await contains(".os-input");
    await target.click();
    await target.edit("new name");
    expect(model.getters.getPivotName(pivotId)).toBe("new name");
});

test("Update the pivot domain from the side panel", async function () {
    onRpc("/web/domain/validate", () => true);
    const { model, env, pivotId } = await createSpreadsheetFromPivotView();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".pivot-defer-update input").click();
    await contains(".o_edit_domain").click();
    await dsHelpers.addNewRule();
    await contains(".modal-footer .btn-primary").click();
    expect(model.getters.getPivotCoreDefinition(pivotId).domain).toEqual([], {
        message: "update is deferred",
    });
    await contains(".pivot-defer-update .o-button-link").click();
    expect(model.getters.getPivotCoreDefinition(pivotId).domain).toEqual([["id", "=", 1]]);
    expect(dsHelpers.getConditionText()).toBe("Id = 1");
});

test("Opening the sidepanel of a pivot while the panel of another pivot is open updates the side panel", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView();
    const arch = /* xml */ `
                    <pivot string="Product">
                        <field name="name" type="col"/>
                        <field name="active" type="row"/>
                        <field name="__count" type="measure"/>
                    </pivot>`;
    const pivotId2 = "PIVOT#2";
    await insertPivotInSpreadsheet(model, "PIVOT#2", {
        arch,
        resModel: "product",
        id: pivotId2,
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    expect(".o-section .o_model_name").toHaveText("Partner (partner)");

    env.openSidePanel("PivotSidePanel", { pivotId: pivotId2 });
    await animationFrame();
    expect(".o-section .o_model_name").toHaveText("Product (product)");
});

test("Duplicate the pivot from the side panel", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();

    expect(model.getters.getPivotIds().length).toBe(1);
    expect(".os-pivot-title").toHaveValue("Partners by Foo");

    await contains(".os-cog-wheel-menu-icon").click();
    await contains(".o-popover .fa-clone").click();
    expect(model.getters.getPivotIds().length).toBe(2);
    expect(".os-pivot-title").toHaveValue("Partners by Foo (copy)");
});

test("A warning is displayed in the side panel if the pivot is unused", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();

    expect(".o-validation-warning").toHaveCount(0);

    model.dispatch("CREATE_SHEET", { sheetId: "sh2", name: "Sheet2" });
    const activeSheetId = model.getters.getActiveSheetId();
    model.dispatch("ACTIVATE_SHEET", { sheetIdFrom: activeSheetId, sheetIdTo: "sh2" });
    model.dispatch("DELETE_SHEET", { sheetId: activeSheetId });
    await animationFrame();

    expect(".o-validation-warning").toHaveCount(1);

    model.dispatch("REQUEST_UNDO");
    await animationFrame();
    expect(".o-validation-warning").toHaveCount(0);
});

test("An error is displayed in the side panel if the pivot has invalid model", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        mockRPC: async function (route, { model, method, kwargs }) {
            if (model === "unknown" && method === "fields_get") {
                throw makeServerError({ code: 404 });
            }
        },
    });
    const pivot = model.getters.getPivotCoreDefinition(pivotId);
    env.model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...pivot,
            model: "unknown",
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();

    expect(".o-validation-error").toHaveCount(1);
});

test("Deleting the pivot open the side panel with all pivots", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView();
    await insertPivotInSpreadsheet(model, "pivot2", { arch: getBasicPivotArch() });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    expect(".o-sidePanelTitle").toHaveText("Pivot #1");

    model.dispatch("REMOVE_PIVOT", { pivotId });
    await animationFrame();
    expect(".o-sidePanel").toHaveCount(0);
});

test("Undo a pivot insertion open the side panel with all pivots", async function () {
    const { model, env } = await createSpreadsheetFromPivotView();
    await insertPivotInSpreadsheet(model, "pivot2", { arch: getBasicPivotArch() });
    env.openSidePanel("PivotSidePanel", { pivotId: "pivot2" });
    await animationFrame();
    expect(".o-sidePanelTitle").toHaveText("Pivot #2");

    /**
     * This is a bit bad because we need three undo to remove the pivot
     * - AUTORESIZE
     * - INSERT_PIVOT
     * - ADD_PIVOT
     */
    model.dispatch("REQUEST_UNDO");
    model.dispatch("REQUEST_UNDO");
    model.dispatch("REQUEST_UNDO");
    await animationFrame();
    expect(".o-sidePanel").toHaveCount(0);
});

test("can drag a column dimension to row", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".pivot-defer-update input").click();
    expect("pivot-defer-update").toHaveCount(0, {
        message: "defer updates is not displayed by default",
    });
    expect(".pivot-defer-update .btn").toHaveCount(0, {
        message: "it should not show the update/discard buttons",
    });
    let definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    expect(definition.columns).toEqual([{ fieldName: "foo" }]);
    expect(definition.rows).toEqual([{ fieldName: "bar" }]);
    await contains(".pivot-dimensions div:nth-child(2)").dragAndDrop(
        ".pivot-dimensions div:nth-child(4)",
        { position: "bottom" }
    );
    await animationFrame();
    expect(".pivot-defer-update .fa-undo").toHaveCount(1);
    expect(".pivot-defer-update .sp_apply_update").toHaveCount(1);
    // TODO use a snapshot
    definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    // update is not applied until the user clicks on the save button
    expect(definition.columns).toEqual([{ fieldName: "foo" }]);
    expect(definition.rows).toEqual([{ fieldName: "bar" }]);
    await contains(".pivot-defer-update .o-button-link").click();
    expect(".pivot-defer-update .btn").toHaveCount(0, {
        message: "it should not show the update/discard buttons",
    });
    definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    expect(definition.columns).toEqual([]);
    expect(definition.rows).toEqual([{ fieldName: "bar" }, { fieldName: "foo" }]);
});

test("updates are applied immediately after defer update checkbox has been unchecked", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".pivot-dimensions div:nth-child(2)").dragAndDrop(
        ".pivot-dimensions div:nth-child(4)",
        { position: "bottom" }
    );
    await animationFrame();
    expect(".pivot-defer-update .btn").toHaveCount(0, {
        message: "it should not show the update/discard buttons",
    });
    const definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    expect(definition.columns).toEqual([]);
    expect(definition.rows).toEqual([{ fieldName: "bar" }, { fieldName: "foo" }]);
});

test("remove pivot dimension", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".pivot-defer-update input").click();
    await contains(".pivot-dimensions .fa-trash").click();
    await animationFrame();
    await contains(".pivot-defer-update .o-button-link").click();
    const definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    expect(definition.columns).toEqual([]);
    expect(definition.rows).toEqual([{ fieldName: "bar" }]);
});

test("remove pivot date time dimension", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="date" type="row" interval="year"/>
                                <field name="date" type="row" interval="month"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".pivot-defer-update input").click();
    await contains(".pivot-dimensions .fa-trash").click();
    await animationFrame();
    await contains(".pivot-defer-update .o-button-link").click();
    const definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    expect(definition.rows).toEqual([{ fieldName: "date", granularity: "month" }]);
});

test("add column dimension", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".add-dimension.o-button").click();
    await contains(".o-popover .o-autocomplete-value").click();
    await contains(".pivot-defer-update .o-checkbox").click();
    const definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    expect(definition.columns).toEqual([{ fieldName: "bar", order: "asc" }]);
    expect(definition.rows).toEqual([]);
});

test("add row dimension", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".add-dimension.o-button:eq(1)").click();
    await contains(".o-popover .o-autocomplete-value").click();
    await contains(".pivot-defer-update .o-checkbox").click();
    const definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    expect(definition.columns).toEqual([]);
    expect(definition.rows).toEqual([{ fieldName: "bar", order: "asc" }]);
});

test("select dimensions with arrow keys", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".add-dimension.o-button").click();
    expect(".o-popover .o-autocomplete-dropdown > div").not.toHaveClass(
        "o-autocomplete-value-focus"
    );
    await contains(".o-popover input").press("ArrowDown");
    expect(".o-popover .o-autocomplete-dropdown > div:eq(0)").toHaveClass(
        "o-autocomplete-value-focus"
    );
    expect(".o-popover .o-autocomplete-dropdown > div:eq(1)").not.toHaveClass(
        "o-autocomplete-value-focus"
    );
    await contains(".o-popover input").press("ArrowDown");
    expect(".o-popover .o-autocomplete-dropdown > div:eq(0)").not.toHaveClass(
        "o-autocomplete-value-focus"
    );
    expect(".o-popover .o-autocomplete-dropdown > div:eq(1)").toHaveClass(
        "o-autocomplete-value-focus"
    );
    await contains(".o-popover input").press("ArrowUp");
    expect(".o-popover .o-autocomplete-dropdown > div:eq(0)").toHaveClass(
        "o-autocomplete-value-focus"
    );
    expect(".o-popover .o-autocomplete-dropdown > div:eq(1)").not.toHaveClass(
        "o-autocomplete-value-focus"
    );
    await contains(".o-popover input").press("Enter");
    await contains(".pivot-defer-update .o-checkbox").click();
    const definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    expect(definition.columns).toEqual([{ fieldName: "bar", order: "asc" }]);
    expect(definition.rows).toEqual([]);
});

test("escape key closes the autocomplete popover", async function () {
    const { env, pivotId } = await createSpreadsheetFromPivotView();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".add-dimension.o-button").click();
    expect(".o-popover input").toHaveCount(1);
    await contains(".o-popover input").press("Escape");
    expect(".o-popover input").toHaveCount(0);
});

test("add pivot dimension input autofocus", async function () {
    const { env, pivotId } = await createSpreadsheetFromPivotView();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".add-dimension.o-button").click();
    expect(".o-popover input").toBeFocused();
    await contains(".o-popover input").press("Escape");
    await contains(".add-dimension.o-button").click();
    expect(".o-popover input").toBeFocused();
});

test("clicking the add button toggles the fields popover", async function () {
    const { env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    const fixture = getFixture();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    const addButton = fixture.querySelectorAll(".add-dimension.o-button")[1];
    await contains(addButton).click();
    expect(".o-popover").toHaveCount(1);
    await contains(addButton).click();
    expect(".o-popover").toHaveCount(0);
});

test("add and search dimension", async function () {
    const foo = fields.Integer({
        string: "Foo",
        store: true,
        searchable: true,
        aggregator: "sum",
        groupable: true,
    });
    const foobar = fields.Char({
        string: "FooBar",
        store: true,
        sortable: true,
        groupable: true,
        searchable: true,
    });
    Partner._fields.foobar = foobar;
    Partner._fields.foo = foo;
    Partner._records = [{ id: 1, foo: 12, bar: true, foobar: "foobar", probability: 10 }];
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            ...getBasicServerData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".pivot-defer-update input").click();
    await contains(".add-dimension.o-button").click();
    await contains(".o-popover input").edit("foo"); // does not confirm because there are more than one field
    await contains(".o-popover input").edit("fooba");
    expect(model.getters.getPivotCoreDefinition(pivotId).columns).toEqual([]);
    expect(model.getters.getPivotCoreDefinition(pivotId).rows).toEqual([]);
    await contains(".pivot-defer-update .o-button-link").click();
    expect(
        JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId))).columns
    ).toEqual([{ fieldName: "foobar", order: "asc" }]);
    expect(model.getters.getPivotCoreDefinition(pivotId).rows).toEqual([]);
});

test("remove pivot measure", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".pivot-defer-update input").click();
    await contains(".pivot-dimensions .fa-trash:last").click();
    await animationFrame();
    await contains(".pivot-defer-update .o-button-link").click();
    const definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    expect(definition.columns).toEqual([{ fieldName: "foo" }]);
    expect(definition.rows).toEqual([{ fieldName: "bar" }]);
    expect(definition.measures).toEqual([]);
});

test("add measure", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    const fixture = getFixture();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(fixture.querySelectorAll(".add-dimension.o-button")[2]).click();
    await contains(fixture.querySelectorAll(".o-popover .o-autocomplete-value")[0]).click();
    await contains(".pivot-defer-update .o-checkbox").click();
    const definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    expect(definition.columns).toEqual([{ fieldName: "foo" }]);
    expect(definition.rows).toEqual([{ fieldName: "bar" }]);
    expect(definition.measures).toEqual([
        { id: "probability:avg", fieldName: "probability", aggregator: "avg" },
        { id: "__count:sum", fieldName: "__count", aggregator: "sum" },
    ]);
});

test("change measure aggregator", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    const fixture = getFixture();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".pivot-defer-update input").click();
    expect(fixture.querySelector(".pivot-measure select")).toHaveValue("avg");
    await contains(".pivot-measure select").select("min");
    expect(".pivot-measure select option:checked").toHaveText("Minimum");
    await contains(".pivot-defer-update .o-button-link").click();
    expect(fixture.querySelector(".pivot-measure select")).toHaveValue("min");
    const definition = model.getters.getPivotCoreDefinition(pivotId);
    expect(definition.measures).toEqual([
        {
            id: "probability:min",
            fieldName: "probability",
            aggregator: "min",
            userDefinedName: undefined,
            computedBy: undefined,
            format: undefined,
            isHidden: undefined,
            display: undefined,
        },
    ]);
});

test("pivot with a reference field measure", async function () {
    const currency_reference = fields.Reference({
        string: "Currency reference",
        store: true,
        sortable: true,
        groupable: true,
        searchable: true,
        aggregator: "count_distinct",
        selection: [["res.currency", "Currency"]],
    });
    Partner._fields.currency_reference = currency_reference;
    Partner._records = [{ id: 1, currency_reference: "res.currency,1" }];

    const { env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            ...getBasicServerData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="currency_reference" type="measure"/>
                            </pivot>`,
            },
        },
    });
    const fixture = getFixture();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    expect(fixture.querySelector(".pivot-measure select")).toHaveValue("count_distinct");
});

test("change dimension order", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="foo" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    const fixture = getFixture();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".pivot-defer-update input").click();
    expect(fixture.querySelector(".pivot-dimensions select")).toHaveValue("");
    await contains(".pivot-dimensions select").select("desc");
    expect(fixture.querySelector(".pivot-dimensions select")).toHaveValue("desc");
    await contains(".pivot-defer-update .o-button-link").click();
    let definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    expect(definition.rows).toEqual([{ fieldName: "foo", order: "desc" }]);

    // reset to automatic
    await contains(".pivot-dimensions select").select("");
    await contains(".pivot-defer-update .o-button-link").click();
    definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    expect(definition.rows).toEqual([{ fieldName: "foo" }]);
});

test("change date dimension granularity", async function () {
    const { model, env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                            <pivot>
                                <field name="date" interval="day" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    const fixture = getFixture();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    await contains(".pivot-defer-update input").click();
    expect(fixture.querySelectorAll(".pivot-dimensions select")[0]).toHaveValue("day");
    await contains(fixture.querySelectorAll(".pivot-dimensions select")[0]).select("week");
    expect(fixture.querySelectorAll(".pivot-dimensions select")[0]).toHaveValue("week");
    await contains(".pivot-defer-update .o-button-link").click();
    const definition = JSON.parse(JSON.stringify(model.getters.getPivotCoreDefinition(pivotId)));
    expect(definition.rows).toEqual([{ fieldName: "date", granularity: "week" }]);
});

test("pivot with twice the same date field with different granularity", async function () {
    const { env, pivotId } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                                <pivot>
                                    <field name="date" interval="year" type="row"/>
                                    <field name="date" interval="day" type="row"/>
                                    <field name="probability" type="measure"/>
                                </pivot>`,
            },
        },
    });
    const fixture = getFixture();
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();
    const firstDateGroup = fixture.querySelectorAll(".pivot-dimensions select")[0];
    const secondDateGroup = fixture.querySelectorAll(".pivot-dimensions select")[2];
    expect(firstDateGroup).toHaveValue("year");
    expect(secondDateGroup).toHaveValue("day");
    expect(firstDateGroup).toHaveText(
        "Year\nQuarter\nQuarter & Year\nMonth\nMonth & Year\nWeek\nWeek & Year\nDay of Month\nDay of Week"
    );
    expect(secondDateGroup).toHaveText(
        "Quarter\nQuarter & Year\nMonth\nMonth & Year\nWeek\nWeek & Year\nDay of Month\nDay\nDay of Week"
    );
});

test("Pivot cells are highlighted when their side panel is open", async function () {
    const { model, env } = await createSpreadsheetFromPivotView();
    const sheetId = model.getters.getActiveSheetId();
    const pivotId = model.getters.getPivotIds()[0];
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();

    const zone = getZoneOfInsertedDataSource(model, "pivot", pivotId);
    expect(getHighlightsFromStore(env)).toEqual([
        { color: "#37A850", sheetId, zone, noFill: true },
    ]);
    await contains(".o-sidePanelClose").click();
    expect(getHighlightsFromStore(env)).toEqual([]);
});

test("Can change measure display as from the side panel", async function () {
    const { model, env } = await createSpreadsheetFromPivotView();
    const pivotId = model.getters.getPivotIds()[0];
    env.openSidePanel("PivotSidePanel", { pivotId });
    await animationFrame();

    await contains(".pivot-measure .fa-cog").click();
    await contains(".o-sidePanel select").select("%_of");

    expect(model.getters.getPivotCoreDefinition(pivotId).measures[0]).toEqual({
        id: "probability:avg",
        fieldName: "probability",
        aggregator: "avg",
        display: {
            type: "%_of",
            fieldNameWithGranularity: "foo",
            value: "(previous)",
        },
    });
});
