import { beforeEach, describe, expect, queryAllTexts, test } from "@odoo/hoot";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import {
    contains,
    getMockEnv,
    makeMockEnv,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import { Model } from "@odoo/o-spreadsheet";
import { addGlobalFilter } from "@spreadsheet/../tests/helpers/commands";
import { DashboardFilterList } from "@spreadsheet_dashboard/bundle/dashboard_action/dashboard_filter_list/dashboard_filter_list";
import { getDefaultValue } from "@spreadsheet/global_filters/helpers";

describe.current.tags("headless");
defineSpreadsheetModels();

async function mountDashboardFilterList({
    searchableParentRelations = {},
    onFilterChange = (filterId, value) => expect.step(`Filter changed to ${JSON.stringify(value)}`),
    model = {},
}) {
    const globalFilters = model.getters.getGlobalFilters();
    const filtersAndValues = globalFilters.map((globalFilter) => {
        const value = model.getters.getGlobalFilterValue(globalFilter.id);
        return {
            globalFilter,
            value: value ? { ...value } : getDefaultValue(globalFilter.type),
        };
    });
    await mountWithCleanup(DashboardFilterList, {
        props: {
            filtersAndValues,
            searchableParentRelations,
            onFilterChange,
            model,
        },
    });
}

let model;
const globalFilter = {
    id: "42",
    type: "text",
    label: "Text Filter",
};
const relationalGlobalFilter = {
    id: "42",
    type: "relation",
    label: "Filter",
    modelName: "partner",
};

beforeEach(async () => {
    await makeMockEnv();
    model = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(getMockEnv()) } });
});

test("basic text filter", async function () {
    await addGlobalFilter(model, globalFilter);
    await mountDashboardFilterList({ model });
    expect(".o-filter-values").toHaveCount(1);
    expect(".fa-pencil").toHaveCount(0);
});

test("filter list with no active filters", async function () {
    await addGlobalFilter(model, globalFilter);
    await mountDashboardFilterList({ model });
    expect(".o-filter-values .o-filter-item").toHaveCount(1);
    expect(".o-filter-values .o-global-filter-text-value").toHaveText("");
});

test("filter list with active filters", async function () {
    await addGlobalFilter(model, {
        ...globalFilter,
        defaultValue: { operator: "ilike", strings: ["foo"] },
    });
    await mountDashboardFilterList({ model });
    expect(".o-filter-values .o-filter-item").toHaveCount(1);
    expect(".o-filter-values .o-global-filter-text-value").toHaveText("foo");
});

test("editing text filter triggers onFilterChange", async function () {
    await addGlobalFilter(model, globalFilter);
    await mountDashboardFilterList({ model });
    await contains(".o-filter-values .o-filter-item .o-autocomplete input").edit("foo");
    await contains(".o-filter-values .o-filter-item .o-autocomplete input").press("Enter");
    expect.verifySteps([
        `Filter changed to ${JSON.stringify({
            operator: "ilike",
            strings: ["foo"],
        })}`,
    ]);
});

test("Changing operator triggers onFilterChange", async function () {
    await addGlobalFilter(model, globalFilter);
    await mountDashboardFilterList({ model });
    await contains(".o-filter-values select").select("not ilike");
    expect.verifySteps([
        `Filter changed to ${JSON.stringify({
            strings: [],
            operator: "not ilike",
        })}`,
    ]);
});

test("Clear button trigger onFilterChange with undefined value", async function () {
    await addGlobalFilter(model, {
        ...globalFilter,
        defaultValue: { operator: "ilike", strings: ["foo"] },
    });
    await mountDashboardFilterList({ model });
    await contains(".o-filter-clear button").click();
    expect.verifySteps([`Filter changed to undefined`]);
});

test("Default value for relation filter is correctly displayed", async function () {
    await addGlobalFilter(model, {
        ...relationalGlobalFilter,
        modelName: "product",
        defaultValue: { operator: "in", ids: [37] },
    });
    await mountDashboardFilterList({ model });
    expect(".o_tag").toHaveCount(1);
    expect(queryAllTexts(".o_tag")).toEqual(["xphone"]);
});

test("Relational global filter with no parent/child model do not have the child of operator", async function () {
    await addGlobalFilter(model, {
        ...relationalGlobalFilter,
        defaultValue: { operator: "in", ids: [37] },
    });
    await mountDashboardFilterList({ searchableParentRelations: { partner: false }, model });
    expect('option[value="child_of"]').toHaveCount(0);
});

test("Relational global filter with a parent/child model adds the child of operator", async function () {
    await addGlobalFilter(model, {
        ...relationalGlobalFilter,
        defaultValue: { operator: "in", ids: [38] },
    });
    await mountDashboardFilterList({ searchableParentRelations: { partner: true }, model });
    expect('option[value="child_of"]').toHaveCount(1);
});

test(`Relational global filter with "set" operator doesn't have a record selector input`, async function () {
    await addGlobalFilter(model, {
        ...relationalGlobalFilter,
        defaultValue: { operator: "set" },
    });
    await mountDashboardFilterList({ model });
    expect(".o-filter-value input").toHaveCount(0);
});

test("relational global filter operator options", async function () {
    await addGlobalFilter(model, {
        ...relationalGlobalFilter,
        defaultValue: { operator: "in", ids: [38] },
    });
    await mountDashboardFilterList({ searchableParentRelations: { partner: true }, model });
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
    await addGlobalFilter(model, globalFilter);
    await mountDashboardFilterList({ model });
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
