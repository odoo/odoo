import { describe, expect, test } from "@odoo/hoot";
import { click, edit, queryAllTexts } from "@odoo/hoot-dom";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { contains, makeMockEnv, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

import { Model } from "@odoo/o-spreadsheet";
import { addGlobalFilter } from "@spreadsheet/../tests/helpers/commands";

import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import { Component, onWillUnmount, xml } from "@odoo/owl";
import { FilterValuesList } from "@spreadsheet/global_filters/components/filter_values_list/filter_values_list";

describe.current.tags("headless");
defineSpreadsheetModels();

class FilterValuesListWrapper extends Component {
    static template = xml`<FilterValuesList t-props="props" />`;
    static components = { FilterValuesList };
    static props = {
        ...FilterValuesList.props,
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
async function mountFilterValuesList(env, props) {
    //@ts-ignore
    env.dialogData = {
        isActive: true,
        close: () => {},
    };
    await mountWithCleanup(FilterValuesListWrapper, { props });
}

test("basic text filter", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    await mountFilterValuesList(env, { model });
    expect(".o-filter-values").toHaveCount(1);
    expect(".fa-pencil").toHaveCount(0);
});

test("Edit filter is displayed when the props openFiltersEditor is set", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await mountFilterValuesList(env, {
        model,
        openFiltersEditor: () => {},
    });
    expect(queryAllTexts(".o-filter-values-footer button")).toEqual(["Filter", "Edit", "Discard"]);
});

test("filter search dialog with no active filters", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    await mountFilterValuesList(env, { model });
    expect(".o-filter-values .o-filter-item").toHaveCount(1);
    expect(".o-filter-values .o-global-filter-text-value").toHaveText("");
});

test("filter search dialog with active filters", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: { operator: "ilike", strings: ["foo"] },
    });
    await mountFilterValuesList(env, { model });
    expect(".o-filter-values .o-filter-item").toHaveCount(1);
    expect(".o-filter-values .o-global-filter-text-value").toHaveText("foo");
});

test("Can set a text filter value", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    await mountFilterValuesList(env, { model });
    await contains(".o-filter-values select").select("not ilike");
    await contains(".o-filter-values .o-filter-item .o-autocomplete input").edit("foo");
    await contains(".o-filter-values .o-filter-item .o-autocomplete input").press("Enter");
    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined, {
        message: "value is not directly set",
    });
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toEqual(
        { operator: "not ilike", strings: ["foo"] },
        { message: "value is set" }
    );
});

test("Can set a numeric filter value with basic operator", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "numeric",
        label: "Numeric Filter",
    });
    await mountFilterValuesList(env, { model });
    await contains(".o-filter-values select").select(">");
    await contains("input").edit(1998);
    await contains("input").press("Enter");
    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined, {
        message: "value is not directly set",
    });
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toEqual(
        { operator: ">", targetValue: 1998 },
        { message: "value is set" }
    );
});

test("Can set a numeric filter value with between operator", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "numeric",
        label: "Numeric Filter",
    });
    await mountFilterValuesList(env, { model });
    await contains(".o-filter-values select").select("between");
    const inputs = document.querySelectorAll(".o-global-filter-numeric-value");
    expect(inputs).toHaveLength(2);
    await click(inputs[0]);
    await edit(1);
    await click(inputs[1]);
    await edit(99);
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toEqual(
        { operator: "between", minimumValue: 1, maximumValue: 99 },
        { message: "value is set" }
    );
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
    await mountFilterValuesList(env, { model });
    await contains(".o-filter-values select").select("not in");
    await contains("input.o-autocomplete--input").click();
    await contains(".o-autocomplete--dropdown-item:first").click();
    expect(".o_tag").toHaveCount(1);
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toEqual(
        { operator: "not in", ids: [37] },
        {
            message: "value is set",
        }
    );
    await contains(".o_tag .o_delete", { visible: false }).click();
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
        defaultValue: { operator: "in", ids: [37] },
    });
    await mountFilterValuesList(env, { model });
    expect(".o_tag").toHaveCount(1);
    await contains(".o_tag .o_delete", { visible: false }).click();
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
        defaultValue: { operator: "in", ids: [37] },
    });
    await mountFilterValuesList(env, { model });
    expect(".o_tag").toHaveCount(1);
    expect(queryAllTexts(".o_tag")).toEqual(["xphone"]);
});

test("Can change a boolean filter value", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "boolean",
        label: "Boolean Filter",
    });
    await mountFilterValuesList(env, { model });
    expect(".o-filter-values select").toHaveValue("");
    await contains(".o-filter-values select").select("not set");
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toEqual({ operator: "not set" });

    await contains(".o-filter-values select").select("");
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);
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
    await mountFilterValuesList(env, { model });
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
    await mountFilterValuesList(env, { model });
    await contains(".o-filter-values .o-filter-item .o-autocomplete input").edit("foo");
    await contains(".o-filter-values .o-filter-item .o-autocomplete input").press("Enter");
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42").strings).toEqual(["foo"], {
        message: "value is set",
    });
});

test("Can clear a filter value removing the values manually", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: { operator: "ilike", strings: ["foo"] },
    });
    await mountFilterValuesList(env, { model });
    expect(".o-filter-values .o-filter-item .o_tag").toHaveCount(1);
    await contains(".o-filter-values .o-filter-item .o_tag .o_delete", { visible: false }).click();
    expect(".o-filter-values .o-filter-item .o_tag").toHaveCount(0);
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined, {
        message: "value is cleared",
    });
});

test("Can clear a filter value with the clear button", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: { operator: "ilike", strings: ["foo"] },
    });
    await mountFilterValuesList(env, { model });
    expect(".o-filter-values .o-filter-item .o_tag").toHaveCount(1);
    await contains(".o-filter-values .o-filter-item .o-filter-clear button").click();
    expect(".o-filter-values .o-filter-item .o_tag").toHaveCount(0);
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);
});

test("clearing a filter value preserves the operator", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        defaultValue: { operator: "ilike", strings: ["foo"] },
    });
    await mountFilterValuesList(env, { model });
    await contains(".o-filter-values select").select("starts with");

    // remove the only value
    await contains(".o-filter-values .o-filter-item .o_tag .o_delete", { visible: false }).click();
    expect(".o-filter-values .o-filter-item .o_tag").toHaveCount(0);
    expect(".o-filter-values select").toHaveValue("starts with");

    // add a value back
    await contains(".o-filter-values .o-filter-item .o-autocomplete input").edit("foo");
    await contains(".o-filter-values .o-filter-item .o-autocomplete input").press("Enter");
    await contains(".btn-primary").click();
    expect(model.getters.getGlobalFilterValue("42")).toEqual({
        operator: "starts with",
        strings: ["foo"],
    });
});

test("Relational global filter with no parent/child model do not have the child of operator", async function () {
    onRpc("ir.model", "has_searchable_parent_relation", () => ({ partner: false }));
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        label: "Filter",
        modelName: "partner",
        defaultValue: { operator: "in", ids: [37] },
    });
    await mountFilterValuesList(env, { model });
    expect('option[value="child_of"]').toHaveCount(0);
});

test("Relational global filter with a parent/child model adds the child of operator", async function () {
    onRpc("ir.model", "has_searchable_parent_relation", () => ({ partner: true }));
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        label: "Filter",
        modelName: "partner",
        defaultValue: { operator: "in", ids: [38] },
    });
    await mountFilterValuesList(env, { model });
    expect('option[value="child_of"]').toHaveCount(1);
});

test(`Relational global filter with "set" operator doesn't have a record selector input`, async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        label: "Filter",
        modelName: "partner",
        defaultValue: { operator: "set" },
    });
    await mountFilterValuesList(env, { model });
    expect(".o-filter-value input").toHaveCount(0);
});

test("relational global filter operator options", async function () {
    onRpc("ir.model", "has_searchable_parent_relation", () => ({ partner: true }));
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        label: "Filter",
        modelName: "partner",
        defaultValue: { operator: "in", ids: [38] },
    });
    await mountFilterValuesList(env, { model });
    expect(queryAllTexts("option")).toEqual([
        "is in",
        "is not in",
        "child of",
        "contains",
        "does not contain",
        "is set",
        "is not set",
    ]);
});

test("text global filter operator options", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Filter",
        defaultValue: { operator: "in", strings: ["hello"] },
    });
    await mountFilterValuesList(env, { model });
    expect(queryAllTexts("option")).toEqual([
        "contains",
        "does not contain",
        "is in",
        "is not in",
        "starts with",
        "is set",
        "is not set",
    ]);
});
