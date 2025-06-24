import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { contains, makeMockEnv, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Model } from "@odoo/o-spreadsheet";
import { addGlobalFilter } from "@spreadsheet/../tests/helpers/commands";

import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import { Component, onWillUnmount, xml } from "@odoo/owl";
import { FiltersSearchDialog } from "@spreadsheet/global_filters/components/filters_search_dialog/filters_search_dialog";

describe.current.tags("headless");
defineSpreadsheetModels();

class FiltersSearchDialogWrapper extends Component {
    static template = xml`<FiltersSearchDialog t-props="props" />`;
    static components = { FiltersSearchDialog };
    static props = {
        ...FiltersSearchDialog.props,
        close: { type: Function, optional: true },
    };
    static defaultProps = {
        close: () => {},
    };

    setup() {
        this.props.model.on("update", this, () => this.render(true));
        onWillUnmount(() => this.props.model.off("update", this));
    }
}

/**
 *
 * @param {object} env
 * @param {{ model: Model }} props
 */
async function mountFiltersSearchDialog(env, props) {
    //@ts-ignore
    env.dialogData = {
        isActive: true,
        close: () => {},
    };
    await mountWithCleanup(FiltersSearchDialogWrapper, { props });
}

test("basic text filter", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    await mountFiltersSearchDialog(env, { model });
    expect(".o-filters-search-dialog").toHaveCount(1);
    expect(".fa-pencil").toHaveCount(0);
});

test("Edit filter is displayed when the props openFiltersEditor is set", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await mountFiltersSearchDialog(env, {
        model,
        openFiltersEditor: () => {},
    });
    expect(".o-filters-search-dialog .fa-pencil").toHaveCount(1);
});

test("filter search dialog with no active filters", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    await mountFiltersSearchDialog(env, { model });
    expect(".o-filters-search-dialog .o-filter-item").toHaveCount(0);
    expect(".o-filters-search-dialog .o-add-global-filter").toHaveCount(1);
});

test("filter search dialog with active filters", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: ["foo"],
    });
    await mountFiltersSearchDialog(env, { model });
    expect(".o-filters-search-dialog .o-filter-item").toHaveCount(1);
    expect(".o-filters-search-dialog .o-add-global-filter").toHaveCount(0);
});

test("New filter dropdown only shows inactive filters", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: ["foo"],
    });
    await addGlobalFilter(model, {
        id: "43",
        type: "text",
        label: "Inactive Filter",
    });
    await mountFiltersSearchDialog(env, { model });
    await contains(".o-add-global-filter").click();
    expect(".o-add-global-filter-label").toHaveCount(1);
    expect(queryAllTexts(".o-add-global-filter-label")).toEqual(["Inactive Filter"]);
});

test("Can set a text filter value", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    await mountFiltersSearchDialog(env, { model });
    await contains(".o-add-global-filter").click();
    await contains(".o-add-global-filter-label").click();
    await contains(".o-filters-search-dialog .o-filter-item .o-autocomplete input").edit("foo");
    await contains(".o-filters-search-dialog .o-filter-item .o-autocomplete input").press("Enter");
    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined, {
        message: "value is not directly set",
    });
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toEqual(["foo"], { message: "value is set" });
});

test("Can set a relation filter value", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        modelName: "product",
        label: "Relation Filter",
    });
    await mountFiltersSearchDialog(env, { model });
    await contains(".o-add-global-filter").click();
    await contains(".o-add-global-filter-label").click();
    await contains("input.o-autocomplete--input").click();
    await contains(".o-autocomplete--dropdown-item:first").click();
    expect(".o_tag").toHaveCount(1);
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toEqual([37], {
        message: "value is set",
    });
    await contains(".o_tag .o_delete").click();
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);
});

test("Can remove a default relation filter value", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        modelName: "product",
        label: "Relation Filter",
        defaultValue: [37],
    });
    await mountFiltersSearchDialog(env, { model });
    expect(".o_tag").toHaveCount(1);
    await contains(".o_tag .o_delete").click();
    expect(".o_tag").toHaveCount(0);
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);
});

test("Default value for relation filter is correctly displayed", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        modelName: "product",
        label: "Relation Filter",
        defaultValue: [37],
    });
    await mountFiltersSearchDialog(env, { model });
    expect(".o_tag").toHaveCount(1);
    expect(queryAllTexts(".o_tag")).toEqual(["xphone"]);
});

test("Can set a boolean filter value", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "boolean",
        label: "Boolean Filter",
    });
    await mountFiltersSearchDialog(env, { model });
    await contains(".o-add-global-filter").click();
    await contains(".o-add-global-filter-label").click();
    await contains("input.o-autocomplete--input").click();
    await contains(".o-autocomplete--dropdown-item:first").click();
    expect(".o_tag").toHaveCount(1);
    expect(queryAllTexts(".o_tag")).toEqual(["Is set"]);
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toEqual([true], {
        message: "value is set",
    });
});

test("Can set a date filter value", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    const label = "Date Filter";
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label,
    });
    await mountFiltersSearchDialog(env, { model });
    await contains(".o-add-global-filter").click();
    await contains(".o-add-global-filter-label").click();
    await contains(".o-date-filter-input").click();
    await contains(".o-dropdown-item[data-id='last_7_days']").click();
    expect(".o-date-filter-input").toHaveValue("Last 7 Days");
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toEqual({
        period: "last_7_days",
        type: "relative",
    });
});

test("Readonly user can update a filter value", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    model.updateMode("readonly");
    await mountFiltersSearchDialog(env, { model });
    await contains(".o-add-global-filter").click();
    await contains(".o-add-global-filter-label").click();
    await contains(".o-filters-search-dialog .o-filter-item .o-autocomplete input").edit("foo");
    await contains(".o-filters-search-dialog .o-filter-item .o-autocomplete input").press("Enter");
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toEqual(["foo"], { message: "value is set" });
});

test("Can clear a filter value", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: ["foo"],
    });
    await mountFiltersSearchDialog(env, { model });
    expect(".o-filters-search-dialog .o-filter-item .o_tag").toHaveCount(1);
    await contains(".o-filters-search-dialog .o-filter-item .o_tag .o_delete").click();
    expect(".o-filters-search-dialog .o-filter-item .o_tag").toHaveCount(0);
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined, {
        message: "value is cleared",
    });
});
