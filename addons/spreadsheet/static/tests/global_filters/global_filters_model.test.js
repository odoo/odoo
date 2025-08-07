/** @ts-check */
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, mockDate, mockTimeZone } from "@odoo/hoot-mock";

import { DispatchResult, Model, helpers, tokenize, constants } from "@odoo/o-spreadsheet";
import { Domain } from "@web/core/domain";
import {
    defineSpreadsheetModels,
    getBasicPivotArch,
    getBasicServerData,
} from "@spreadsheet/../tests/helpers/data";
import {
    createModelWithDataSource,
    createModelFromGrid,
} from "@spreadsheet/../tests/helpers/model";
import { createSpreadsheetWithPivotAndList } from "@spreadsheet/../tests/helpers/pivot_list";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";

import {
    createSpreadsheetWithChart,
    insertChartInSpreadsheet,
} from "@spreadsheet/../tests/helpers/chart";
import {
    addColumns,
    addGlobalFilter,
    deleteColumns,
    editGlobalFilter,
    moveGlobalFilter,
    removeGlobalFilter,
    setCellContent,
    setCellFormat,
    setGlobalFilterValue,
    undo,
    redo,
    addGlobalFilterWithoutReload,
} from "@spreadsheet/../tests/helpers/commands";
import {
    assertDateDomainEqual,
    getDateDomainDurationInDays,
} from "@spreadsheet/../tests/helpers/date_domain";
import {
    getCell,
    getCellFormula,
    getCellValue,
    getEvaluatedCell,
} from "@spreadsheet/../tests/helpers/getters";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/helpers/global_filter";
import {
    createSpreadsheetWithList,
    insertListInSpreadsheet,
} from "@spreadsheet/../tests/helpers/list";
import {
    createSpreadsheetWithPivot,
    insertPivotInSpreadsheet,
} from "@spreadsheet/../tests/helpers/pivot";
import { toRangeData } from "@spreadsheet/../tests/helpers/zones";
import { GlobalFiltersCoreViewPlugin } from "@spreadsheet/global_filters/plugins/global_filters_core_view_plugin";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { PivotUIGlobalFilterPlugin } from "@spreadsheet/pivot/index";
import { RELATIVE_PERIODS } from "@spreadsheet/global_filters/helpers";

describe.current.tags("headless");
defineSpreadsheetModels();

const { DateTime } = luxon;
const { toZone, toNumber } = helpers;
const { DEFAULT_LOCALE } = constants;

/**
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 *
 */

const DEFAULT_FIELD_MATCHINGS = {
    "PIVOT#1": { chain: "date", type: "date" },
};

const DEFAULT_LIST_FIELD_MATCHINGS = {
    1: { chain: "date", type: "date" },
};

function getFiltersMatchingPivot(model, formula) {
    const sheetId = model.getters.getActiveSheetId();
    const pivotUIPlugin = model["handlers"].find(
        (handler) => handler instanceof PivotUIGlobalFilterPlugin
    );
    return pivotUIPlugin._getFiltersMatchingPivot(sheetId, tokenize(formula));
}

test("Can add a global filter", async function () {
    const { model } = await createSpreadsheetWithPivotAndList();
    expect(model.getters.getGlobalFilters().length).toBe(0);
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER, {
        pivot: DEFAULT_FIELD_MATCHINGS,
    });
    expect(model.getters.getGlobalFilters().length).toBe(1);
    const computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(computedDomain.length).toBe(3);
    expect(computedDomain[0]).toBe("&");
});

test("Can add a global filter with an empty field matching (no field chain)", async function () {
    const { model } = await createSpreadsheetWithPivotAndList();
    expect(model.getters.getGlobalFilters().length).toBe(0);
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER, {
        pivot: { "PIVOT#1": {} },
    });
    expect(model.getters.getGlobalFilters().length).toBe(1);
    const computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(computedDomain).toEqual([]);
});

test("Can delete a global filter", async function () {
    const { model } = await createSpreadsheetWithPivotAndList();
    let result = await removeGlobalFilter(model, 1);
    expect(result.reasons).toEqual([CommandResult.FilterNotFound]);
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    const gf = model.getters.getGlobalFilters()[0];
    result = await removeGlobalFilter(model, gf.id);
    expect(result).toBe(DispatchResult.Success);
    expect(model.getters.getGlobalFilters().length).toBe(0);
    const computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(computedDomain).toEqual([]);
});

test("Can edit a global filter", async function () {
    const { model } = await createSpreadsheetWithPivotAndList();
    let result = await editGlobalFilter(model, {
        ...THIS_YEAR_GLOBAL_FILTER,
        id: 1,
    });
    expect(result.reasons).toEqual([CommandResult.FilterNotFound]);
    await addGlobalFilter(model, { ...THIS_YEAR_GLOBAL_FILTER, id: 1 });
    result = await editGlobalFilter(model, {
        ...THIS_YEAR_GLOBAL_FILTER,
        label: "Another label",
        id: 1,
    });
    expect(result).toBe(DispatchResult.Success);
    expect(model.getters.getGlobalFilters().length).toBe(1);
    expect(model.getters.getGlobalFilters()[0].defaultValue).toBe("this_year");
});

test("A global filter with an empty field can be evaluated", async function () {
    const { model } = await createSpreadsheetWithPivotAndList();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    const domain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(domain).toEqual([]);
});

test("Cannot have duplicated names", async function () {
    const { model } = await createSpreadsheetWithPivotAndList();
    const filter = { ...THIS_YEAR_GLOBAL_FILTER, label: "Hello" };
    await addGlobalFilter(model, filter);
    expect(model.getters.getGlobalFilters().length).toBe(1);

    // Add filter with same name
    let result = await addGlobalFilter(model, { ...filter, id: "456" });
    expect(result.reasons).toEqual([CommandResult.DuplicatedFilterLabel]);
    expect(model.getters.getGlobalFilters().length).toBe(1);

    // Edit to set same name as other filter
    await addGlobalFilter(model, { ...filter, id: "789", label: "Other name" });
    expect(model.getters.getGlobalFilters().length).toBe(2);
    result = await editGlobalFilter(model, {
        ...filter,
        label: "Other name",
    });
    expect(result.reasons).toEqual([CommandResult.DuplicatedFilterLabel]);

    // Edit to set same name
    result = await editGlobalFilter(model, {
        ...filter,
        label: "Hello",
    });
    expect(result).toBe(DispatchResult.Success);
});

test("Cannot have empty names", async function () {
    const { model } = await createSpreadsheetWithPivotAndList();
    const filter = {
        type: "text",
        id: "1",
    };
    let result = await addGlobalFilter(model, filter);
    expect(result.reasons).toEqual([CommandResult.InvalidFilterLabel]);
    expect(model.getters.getGlobalFilters().length).toBe(0);

    addGlobalFilter(model, { type: "text", label: "hello", id: "1" });
    expect(model.getters.getGlobalFilters().length).toBe(1);

    result = await editGlobalFilter(model, {
        id: "1",
        type: "text",
        label: undefined,
    });
    expect(result.reasons).toEqual([CommandResult.InvalidFilterLabel]);
});

test("Can name/rename filters with special characters", async function () {
    const { model } = await createSpreadsheetWithPivot();
    const filter = {
        ...THIS_YEAR_GLOBAL_FILTER,
        label: "{my} We)ird. |*ab(el []",
    };
    let result = await addGlobalFilter(model, filter);
    expect(result).toBe(DispatchResult.Success);
    expect(model.getters.getGlobalFilters().length).toBe(1);

    // Edit to set another name with special characters
    result = await editGlobalFilter(model, {
        ...filter,
        label: "+Othe^ we?rd name+$",
    });

    expect(result).toBe(DispatchResult.Success);

    result = await editGlobalFilter(model, { ...filter, label: "normal name" });
    expect(result).toBe(DispatchResult.Success);

    result = await editGlobalFilter(model, {
        ...filter,
        label: "?ack +.* to {my} We)ird. |*ab(el []",
    });
    expect(result).toBe(DispatchResult.Success);
});

test("Adding new DataSource will set its fieldMatching according to other ones with the same model", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER, {
        pivot: {
            [pivotId]: { chain: "created_on", type: "date", offset: 1 },
        },
    });
    const filterId = THIS_YEAR_GLOBAL_FILTER.id;

    let fieldMatching = model.getters.getPivotFieldMatching(pivotId, filterId);
    expect(fieldMatching.chain).toBe("created_on");
    expect(fieldMatching.type).toBe("date");
    expect(fieldMatching.offset).toBe(1);

    await insertPivotInSpreadsheet(model, "PIVOT#2", {
        arch: getBasicPivotArch(),
    });
    fieldMatching = model.getters.getPivotFieldMatching("PIVOT#2", filterId);
    expect(fieldMatching.chain).toBe("created_on");
    expect(fieldMatching.type).toBe("date");
    expect(fieldMatching.offset).toBe(undefined);

    insertListInSpreadsheet(model, { model: "partner", columns: ["foo"] });
    fieldMatching = model.getters.getListFieldMatching("1", filterId);
    expect(fieldMatching.chain).toBe("created_on");
    expect(fieldMatching.type).toBe("date");
    expect(fieldMatching.offset).toBe(undefined);

    insertChartInSpreadsheet(model);
    const chartId = model.getters.getOdooChartIds()[0];
    fieldMatching = model.getters.getOdooChartFieldMatching(chartId, filterId);
    expect(fieldMatching.chain).toBe("created_on");
    expect(fieldMatching.type).toBe("date");
    expect(fieldMatching.offset).toBe(undefined);
});

test("Adding new DataSource with a different model won't set up its field matching", async function () {
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER, {
        pivot: {
            "PIVOT#1": { chain: "created_on", type: "date", offset: 1 },
        },
    });
    const filterId = THIS_YEAR_GLOBAL_FILTER.id;

    insertListInSpreadsheet(model, { model: "product", columns: ["name"] });
    const fieldMatching = model.getters.getListFieldMatching("1", filterId);
    expect(fieldMatching).toBe(undefined);
});
test("Can save a value to an existing global filter", async function () {
    const { model } = await createSpreadsheetWithPivotAndList();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER, {
        pivot: DEFAULT_FIELD_MATCHINGS,
        list: DEFAULT_LIST_FIELD_MATCHINGS,
    });
    const gf = model.getters.getGlobalFilters()[0];
    const year = DateTime.local().year;
    let result = await setGlobalFilterValue(model, {
        id: gf.id,
        value: { type: "month", month: 2, year },
    });
    expect(result).toBe(DispatchResult.Success);
    expect(model.getters.getGlobalFilters().length).toBe(1);
    expect(model.getters.getGlobalFilterDefaultValue(gf.id)).toBe("this_year");
    expect(model.getters.getGlobalFilterValue(gf.id)).toEqual({
        type: "month",
        month: 2,
        year,
    });
    result = await setGlobalFilterValue(model, {
        id: gf.id,
        value: { type: "month", month: 3, year },
    });
    expect(result).toBe(DispatchResult.Success);
    expect(model.getters.getGlobalFilterValue(gf.id)).toEqual({
        type: "month",
        month: 3,
        year,
    });
    const computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(computedDomain.length).toBe(3);
    const listDomain = model.getters.getListComputedDomain("1");
    expect(listDomain.length).toBe(3);
});

test("Domain of simple date filter", async function () {
    mockDate("2022-07-14 00:00:00");
    const { model } = await createSpreadsheetWithPivotAndList();
    insertChartInSpreadsheet(model);
    const chartId = model.getters.getOdooChartIds()[0];
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER, {
        pivot: { "PIVOT#1": { chain: "date", type: "date" } },
        list: { 1: { chain: "date", type: "date" } },
        chart: { [chartId]: { chain: "date", type: "date" } },
    });
    await setGlobalFilterValue(model, {
        id: THIS_YEAR_GLOBAL_FILTER.id,
        value: { type: "year", year: 2021 },
    });
    const pivotDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(pivotDomain[0]).toBe("&");
    expect(pivotDomain[1]).toEqual(["date", ">=", "2021-01-01"]);
    expect(pivotDomain[2]).toEqual(["date", "<=", "2021-12-31"]);
    const listDomain = model.getters.getListComputedDomain("1");
    expect(listDomain[0]).toBe("&");
    expect(listDomain[1]).toEqual(["date", ">=", "2021-01-01"]);
    expect(listDomain[2]).toEqual(["date", "<=", "2021-12-31"]);
    const chartDomain = model.getters.getChartDataSource(chartId).getComputedDomain();
    expect(chartDomain[0]).toBe("&");
    expect(chartDomain[1]).toEqual(["date", ">=", "2021-01-01"]);
    expect(chartDomain[2]).toEqual(["date", "<=", "2021-12-31"]);
});

test("Domain of date filter with year offset on pivot field", async function () {
    mockDate("2022-07-14 00:00:00");
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER, {
        pivot: { "PIVOT#1": { chain: "date", type: "date", offset: 1 } },
    });
    const pivotDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(pivotDomain[0]).toBe("&");
    expect(pivotDomain[1]).toEqual(["date", ">=", "2023-01-01"]);
    expect(pivotDomain[2]).toEqual(["date", "<=", "2023-12-31"]);
});

test("Domain of date filter with quarter offset on list field", async function () {
    mockDate("2022-07-14 00:00:00");
    const { model } = await createSpreadsheetWithList();
    /** @type GlobalFilter */
    const filter = {
        ...THIS_YEAR_GLOBAL_FILTER,
        defaultValue: "this_quarter",
    };
    await addGlobalFilter(model, filter, {
        list: { 1: { chain: "date", type: "date", offset: 2 } },
    });
    const listDomain = model.getters.getListComputedDomain("1");
    expect(listDomain[0]).toBe("&");
    expect(listDomain[1]).toEqual(["date", ">=", "2023-01-01"]);
    expect(listDomain[2]).toEqual(["date", "<=", "2023-03-31"]);
});

test("Domain of date filter with month offset on graph field", async function () {
    mockDate("2022-07-14 00:00:00");
    const { model } = await createSpreadsheetWithChart();
    const chartId = model.getters.getOdooChartIds()[0];
    /** @type GlobalFilter */
    const filter = {
        ...THIS_YEAR_GLOBAL_FILTER,
        defaultValue: "this_month",
    };
    await addGlobalFilter(model, filter, {
        chart: { [chartId]: { chain: "date", type: "date", offset: -2 } },
    });
    const chartDomain = model.getters.getChartDataSource(chartId).getComputedDomain();
    expect(chartDomain[0]).toBe("&");
    expect(chartDomain[1]).toEqual(["date", ">=", "2022-05-01"]);
    expect(chartDomain[2]).toEqual(["date", "<=", "2022-05-31"]);
});

test("Can import/export filters", async function () {
    mockDate("2022-07-14 00:00:00");
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                cells: {
                    A1: '=PIVOT.VALUE("1", "probability")',
                },
            },
        ],
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ fieldName: "foo" }],
                domain: [],
                measures: [{ id: "probability:avg", fieldName: "probability", aggregator: "avg" }],
                model: "partner",
                rows: [{ fieldName: "bar" }],
                context: {},
                fieldMatching: {
                    41: { type: "date", chain: "date" },
                    42: { type: "date", chain: "date" },
                },
            },
        },
        lists: {
            1: {
                id: 1,
                columns: ["foo", "contact_name"],
                domain: [],
                model: "partner",
                orderBy: [],
                context: {},
                fieldMatching: {
                    41: { type: "date", chain: "date" },
                    42: { type: "date", chain: "date" },
                },
            },
        },
        globalFilters: [
            {
                id: "41",
                type: "date",
                label: "This Year",
                defaultValue: "this_year",
            },
            {
                id: "42",
                type: "date",
                label: "This Month",
                defaultValue: "this_month",
            },
        ],
    };
    const { model } = await createModelWithDataSource({ spreadsheetData });

    expect(model.getters.getGlobalFilters().length).toBe(2);
    let [filter1, filter2] = model.getters.getGlobalFilters();
    expect(filter1.defaultValue).toBe("this_year");
    expect(model.getters.getGlobalFilterValue(filter1.id)).toEqual({
        type: "year",
        year: 2022,
    });
    expect(filter2.defaultValue).toBe("this_month");
    expect(model.getters.getGlobalFilterValue(filter2.id)).toEqual({
        type: "month",
        month: 7,
        year: 2022,
    });

    let computedDomain = model.getters.getPivotComputedDomain("1");
    expect(computedDomain.length).toBe(7, {
        message: "it should have updated the pivot domain",
    });
    let listDomain = model.getters.getListComputedDomain("1");
    expect(listDomain.length).toBe(7, {
        message: "it should have updated the list domain",
    });

    const newModel = new Model(model.exportData(), {
        custom: model.config.custom,
    });

    expect(newModel.getters.getGlobalFilters().length).toBe(2);
    [filter1, filter2] = model.getters.getGlobalFilters();
    expect(filter1.defaultValue).toBe("this_year");
    expect(model.getters.getGlobalFilterValue(filter1.id)).toEqual({
        type: "year",
        year: 2022,
    });
    expect(filter2.defaultValue).toBe("this_month");
    expect(model.getters.getGlobalFilterValue(filter2.id)).toEqual({
        type: "month",
        month: 7,
        year: 2022,
    });

    computedDomain = newModel.getters.getPivotComputedDomain("1");
    expect(computedDomain.length).toBe(7, {
        message: "it should have updated the pivot domain",
    });
    listDomain = newModel.getters.getListComputedDomain("1");
    expect(listDomain.length).toBe(7, {
        message: "it should have updated the list domain",
    });
});

test("Can import/export filters of only list", async function () {
    mockDate("2022-07-14 00:00:00");
    const spreadsheetData = {
        lists: {
            1: {
                id: 1,
                columns: ["foo", "contact_name"],
                domain: [],
                model: "partner",
                orderBy: [],
                context: {},
                fieldMatching: {
                    41: { type: "date", chain: "date" },
                    42: { type: "date", chain: "date" },
                },
            },
        },
        globalFilters: [
            {
                id: "41",
                type: "date",
                label: "This Year",
                defaultValue: "this_year",
            },
            {
                id: "42",
                type: "date",
                label: "This Month",
                defaultValue: "this_month",
            },
        ],
    };
    const { model } = await createModelWithDataSource({ spreadsheetData });

    let listDomain = model.getters.getListComputedDomain("1");
    expect(listDomain.length).toBe(7, {
        message: "it should have updated the list domain",
    });

    const newModel = new Model(model.exportData(), {
        custom: model.config.custom,
    });

    listDomain = newModel.getters.getListComputedDomain("1");
    expect(listDomain.length).toBe(7, {
        message: "it should have updated the list domain",
    });
});

test("Relational filter with undefined value", async function () {
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            label: "Relation Filter",
        },
        {
            pivot: {
                "PIVOT#1": {
                    field: "foo",
                    type: "char",
                },
            },
        }
    );
    const [filter] = model.getters.getGlobalFilters();
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: undefined,
    });
    const computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(computedDomain.length).toBe(0, {
        message: "it should not have updated the pivot domain",
    });
});

test("Relational filter including children", async function () {
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            label: "Relation Filter",
            modelName: "product",
        },
        {
            pivot: {
                "PIVOT#1": {
                    chain: "product_id",
                    type: "many2one",
                },
            },
        }
    );
    const [filter] = model.getters.getGlobalFilters();
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "child_of", ids: [42] },
    });
    expect(model.getters.getPivotComputedDomain("PIVOT#1")).toEqual([
        ["product_id", "child_of", [42]],
    ]);
});

test("Relational filter default to current user", async function () {
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        label: "User Filter",
        modelName: "res.users",
        defaultValue: { operator: "in", ids: "current_user" },
    });
    const [filter] = model.getters.getGlobalFilters();
    expect(model.getters.getGlobalFilterValue(filter.id)).toEqual({ operator: "in", ids: [7] });

    model.dispatch("SET_GLOBAL_FILTER_VALUE", { id: filter.id });
    expect(model.getters.getGlobalFilterValue(filter.id)).toBe(undefined, {
        message: "can clear automatic value",
    });
});

test("Can set a numeric global filter value to 0", async function () {
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(model, {
        id: "42",
        type: "numeric",
        label: "Numeric Filter",
        defaultValue: { operator: "=", targetValue: 1998 },
    });
    const [filter] = model.getters.getGlobalFilters();
    expect(model.getters.getGlobalFilterValue(filter.id)).toEqual({
        operator: "=",
        targetValue: 1998,
    });
    model.dispatch("SET_GLOBAL_FILTER_VALUE", {
        id: filter.id,
        value: { operator: "=", targetValue: 0 },
    });
    expect(model.getters.getGlobalFilterValue(filter.id)).toEqual({
        operator: "=",
        targetValue: 0,
    });
});

test("Get active filters with multiple filters", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    await addGlobalFilter(model, {
        id: "43",
        type: "date",
        label: "Date Filter",
    });
    await addGlobalFilter(model, {
        id: "44",
        type: "relation",
    });
    const [text] = model.getters.getGlobalFilters();
    expect(model.getters.getActiveFilterCount()).toBe(0);
    await setGlobalFilterValue(model, {
        id: text.id,
        value: { operator: "ilike", strings: ["Hello"] },
    });
    expect(model.getters.getActiveFilterCount()).toBe(1);
});

test("Get active filters with text filter enabled", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    const [filter] = model.getters.getGlobalFilters();
    expect(model.getters.getActiveFilterCount()).toBe(0);
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "ilike", strings: ["Hello"] },
    });
    expect(model.getters.getActiveFilterCount()).toBe(1);
});

test("domain generated with text filter", async function () {
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "text",
            label: "Text Filter",
        },
        {
            pivot: { "PIVOT#1": { chain: "name", type: "char" } },
        }
    );
    const [filter] = model.getters.getGlobalFilters();
    expect(model.getters.getPivotComputedDomain("PIVOT#1")).toEqual([]);
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "ilike", strings: ["Hello"] },
    });
    expect(model.getters.getPivotComputedDomain("PIVOT#1")).toEqual([["name", "ilike", "Hello"]]);
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "ilike", strings: ["Hello", "World"] },
    });
    expect(model.getters.getPivotComputedDomain("PIVOT#1")).toEqual([
        "|",
        ["name", "ilike", "Hello"],
        ["name", "ilike", "World"],
    ]);
});

test("restrict text filter to a range of values", async function () {
    const { model } = await createModelWithDataSource();
    const sheetId = model.getters.getActiveSheetId();
    setCellContent(model, "A1", "Hello");
    setCellContent(model, "A2", "World");
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangesOfAllowedValues: [toRangeData(sheetId, "A1:A2")],
    });

    expect(model.getters.getTextFilterOptions("42")).toEqual([
        { value: "Hello", formattedValue: "Hello" },
        { value: "World", formattedValue: "World" },
    ]);
});

test("duplicated values appear once in text filter with range", async function () {
    const { model } = await createModelWithDataSource();
    const sheetId = model.getters.getActiveSheetId();
    setCellContent(model, "A1", "3");
    setCellContent(model, "A2", "=3");
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangesOfAllowedValues: [toRangeData(sheetId, "A1:A2")],
    });

    expect(model.getters.getTextFilterOptions("42")).toEqual([{ value: "3", formattedValue: "3" }]);
});

test("numbers and dates are formatted in text filter with range", async function () {
    const { model } = await createModelWithDataSource();
    const sheetId = model.getters.getActiveSheetId();
    setCellContent(model, "A1", "2");
    setCellContent(model, "A2", "2");
    setCellFormat(model, "A1", "#,##0.00");
    setCellFormat(model, "A2", "dd-mm-yyyy");
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangesOfAllowedValues: [toRangeData(sheetId, "A1:A2")],
    });

    expect(model.getters.getTextFilterOptions("42")).toEqual([
        { value: "2", formattedValue: "2.00" },
        { value: "2", formattedValue: "01-01-1900" },
    ]);
});

test("falsy values appears (but not empty string) in text filter with range", async function () {
    const { model } = await createModelWithDataSource();
    const sheetId = model.getters.getActiveSheetId();
    setCellContent(model, "A1", "0");
    setCellContent(model, "A2", "FALSE");
    setCellContent(model, "A3", '=""');
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangesOfAllowedValues: [toRangeData(sheetId, "A1:A3")],
    });

    expect(model.getters.getTextFilterOptions("42")).toEqual([
        { value: "0", formattedValue: "0" },
        { value: "false", formattedValue: "FALSE" },
    ]);
});

test("default value appears in text filter with range", async function () {
    const { model } = await createModelWithDataSource();
    const sheetId = model.getters.getActiveSheetId();
    setCellContent(model, "A1", "Hello");
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangesOfAllowedValues: [toRangeData(sheetId, "A1")],
        defaultValue: { operator: "ilike", strings: ["World"] },
    });

    expect(model.getters.getTextFilterOptions("42")).toEqual([
        { value: "Hello", formattedValue: "Hello" },
        { value: "World", formattedValue: "World" },
    ]);
});

test("current value appears in text filter with range", async function () {
    const { model } = await createModelWithDataSource();
    const sheetId = model.getters.getActiveSheetId();
    setCellContent(model, "A1", "Hello");
    setCellContent(model, "A2", "World");
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangesOfAllowedValues: [toRangeData(sheetId, "A1:A2")],
    });
    await setGlobalFilterValue(model, {
        id: "42",
        value: { operator: "ilike", strings: ["World"] }, // set the value to one of the allowed values
    });

    setCellContent(model, "A2", "Bob"); // change the value of the cell
    expect(model.getters.getTextFilterOptions("42")).toEqual([
        { value: "Hello", formattedValue: "Hello" },
        { value: "Bob", formattedValue: "Bob" },
        { value: "World", formattedValue: "World" },
    ]);
});

test("default value appears once if the same value is in the text filter range", async function () {
    const { model } = await createModelWithDataSource();
    const sheetId = model.getters.getActiveSheetId();
    setCellContent(model, "A1", "Hello");
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangesOfAllowedValues: [toRangeData(sheetId, "A1")],
        defaultValue: { operator: "ilike", strings: ["Hello"] }, // same value as in A1
    });
    expect(model.getters.getTextFilterOptions("42")).toEqual([
        { value: "Hello", formattedValue: "Hello" },
    ]);
});

test("formatted default value appears once if the same value is in the text filter range", async function () {
    const { model } = await createModelWithDataSource();
    const sheetId = model.getters.getActiveSheetId();
    setCellContent(model, "A1", "0.3");
    setCellFormat(model, "A1", "0.00%");
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangesOfAllowedValues: [toRangeData(sheetId, "A1")],
        defaultValue: { operator: "ilike", strings: ["0.3"] },
    });
    await setGlobalFilterValue(model, {
        id: "42",
        value: { operator: "ilike", strings: ["0.3"] },
    });
    expect(model.getters.getTextFilterOptions("42")).toEqual([
        { value: "0.3", formattedValue: "30.00%" },
    ]);
});

test("errors and empty cells if the same value is in the text filter range", async function () {
    const { model } = await createModelWithDataSource();
    const sheetId = model.getters.getActiveSheetId();
    setCellContent(model, "A1", "Hello");
    setCellContent(model, "A2", "=1/0");
    setCellContent(model, "A3", "");
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangesOfAllowedValues: [toRangeData(sheetId, "A1:A3")],
        defaultValue: { operator: "ilike", strings: ["Hello"] }, // same value as in A1
    });
    expect(model.getters.getTextFilterOptions("42")).toEqual([
        { value: "Hello", formattedValue: "Hello" },
    ]);
});

test("add column before a text filter range", async function () {
    const { model } = await createModelWithDataSource();
    const sheetId = model.getters.getActiveSheetId();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangesOfAllowedValues: [toRangeData(sheetId, "A1:A2")],
    });
    addColumns(model, "before", "A", 1);

    expect(model.getters.getGlobalFilter("42").rangesOfAllowedValues[0].zone).toEqual(
        toZone("B1:B2")
    );
});

test("delete a text filter range", async function () {
    const { model } = await createModelWithDataSource();
    const sheetId = model.getters.getActiveSheetId();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangesOfAllowedValues: [toRangeData(sheetId, "A1:A2")],
    });
    deleteColumns(model, ["A"]);

    expect(model.getters.getGlobalFilter("42").rangesOfAllowedValues).toBe(undefined);
});

test("import/export a text filter range", async function () {
    const { model } = await createModelWithDataSource();
    const sheetId = model.getters.getActiveSheetId();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
        rangesOfAllowedValues: [toRangeData(sheetId, "A1:A2")],
    });
    // export
    const data = model.exportData();
    expect(data.globalFilters[0].rangesOfAllowedValues).toEqual(["Sheet1!A1:A2"]);
    // import
    const newModel = new Model(data);
    const ranges = newModel.getters.getGlobalFilter("42").rangesOfAllowedValues;
    expect(ranges.length).toBe(1);
    expect(ranges[0].zone).toEqual(toZone("A1:A2"));
    expect(ranges[0].sheetId).toBe(sheetId);
});

test("Get active filters with relation filter enabled", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        label: "Relation Filter",
    });
    const [filter] = model.getters.getGlobalFilters();
    expect(model.getters.getActiveFilterCount()).toBe(0);
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "in", ids: [1] },
    });
    expect(model.getters.getActiveFilterCount()).toBe(1);
});

test("Get active filters with date filter enabled", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    const [filter] = model.getters.getGlobalFilters();
    expect(model.getters.getActiveFilterCount()).toBe(0);
    const year = DateTime.now().year;
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: {
            type: "year",
            year,
        },
    });
    expect(model.getters.getActiveFilterCount()).toBe(1);
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: {
            type: "quarter",
            year,
            quarter: 1,
        },
    });
    expect(model.getters.getActiveFilterCount()).toBe(1);
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: {
            type: "quarter",
            year,
            quarter: 1,
        },
    });
    expect(model.getters.getActiveFilterCount()).toBe(1);
});

test("ODOO.FILTER.VALUE text filter", async function () {
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A10", `=ODOO.FILTER.VALUE("Text Filter")`);
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("#ERROR");
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Text Filter",
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("");
    const [filter] = model.getters.getGlobalFilters();
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "ilike", strings: ["Hello"] },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("Hello");
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "ilike", strings: ["Hello", "World"] },
    });
    expect(getCellValue(model, "A10")).toBe("Hello, World");
});

test("ODOO.FILTER.VALUE numeric filter", async function () {
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A10", `=ODOO.FILTER.VALUE("Numeric Filter")`);
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("#ERROR");
    await addGlobalFilter(model, {
        id: "42",
        type: "numeric",
        label: "Numeric Filter",
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("");
    const [filter] = model.getters.getGlobalFilters();
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: ">", targetValue: 1998 },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe(1998);
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "between", minimumValue: 1, maximumValue: 99 },
    });
    expect(getCellValue(model, "A10")).toBe(1);
    expect(getCellValue(model, "B10")).toBe(99);
});

test("ODOO.FILTER.VALUE date filter", async function () {
    mockDate("2022-03-10 00:00:00");
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A10", `=ODOO.FILTER.VALUE("Date Filter")`);
    await animationFrame();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    await animationFrame();
    const [filter] = model.getters.getGlobalFilters();
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: {
            type: "quarter",
            year: 2022,
            quarter: 1,
        },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe(toNumber("2022-01-01", DEFAULT_LOCALE));
    expect(getCellValue(model, "B10")).toBe(toNumber("2022-03-31", DEFAULT_LOCALE));
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: {
            type: "year",
            year: 2022,
        },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe(toNumber("2022-01-01", DEFAULT_LOCALE));
    expect(getCellValue(model, "B10")).toBe(toNumber("2022-12-31", DEFAULT_LOCALE));
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: {
            type: "month",
            year: 2022,
            month: 1,
        },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe(toNumber("2022-01-01", DEFAULT_LOCALE));
    expect(getCellValue(model, "B10")).toBe(toNumber("2022-01-31", DEFAULT_LOCALE));
    await setGlobalFilterValue(model, {
        id: filter.id,
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe(``);
    expect(getCellValue(model, "B10")).toBe(``);
});

test("ODOO.FILTER.VALUE date from/to without values", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    setCellContent(model, "A1", `=ODOO.FILTER.VALUE("Date Filter")`);
    expect(getEvaluatedCell(model, "A1").value).toBe("");
    expect(getEvaluatedCell(model, "B1").value).toBe("");
});

test("ODOO.FILTER.VALUE date from/to with only from defined", async function () {
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A1", `=ODOO.FILTER.VALUE("Date Filter")`);
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    await setGlobalFilterValue(model, {
        id: "42",
        value: {
            type: "range",
            from: "2020-01-01",
        },
    });
    expect(getEvaluatedCell(model, "A1").value).toBe(43831);
    expect(getEvaluatedCell(model, "A1").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "A1").formattedValue).toBe("1/1/2020");
    expect(getEvaluatedCell(model, "B1").value).toBe("");
});

test("ODOO.FILTER.VALUE date from/to with only to defined", async function () {
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A1", `=ODOO.FILTER.VALUE("Date Filter")`);
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    await setGlobalFilterValue(model, {
        id: "42",
        value: {
            type: "range",
            to: "2020-01-01",
        },
    });
    expect(getEvaluatedCell(model, "A1").value).toBe("");
    expect(getEvaluatedCell(model, "B1").value).toBe(43831);
    expect(getEvaluatedCell(model, "B1").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "B1").formattedValue).toBe("1/1/2020");
});

test("ODOO.FILTER.VALUE date from/to with from and to defined", async function () {
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A1", `=ODOO.FILTER.VALUE("Date Filter")`);
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    await setGlobalFilterValue(model, {
        id: "42",
        value: {
            type: "range",
            from: "2020-01-01",
            to: "2021-01-01",
        },
    });
    expect(getEvaluatedCell(model, "A1").value).toBe(43831);
    expect(getEvaluatedCell(model, "A1").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "A1").formattedValue).toBe("1/1/2020");
    expect(getEvaluatedCell(model, "B1").value).toBe(44197);
    expect(getEvaluatedCell(model, "B1").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "B1").formattedValue).toBe("1/1/2021");
});

test("ODOO.FILTER.VALUE relation filter", async function () {
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A10", `=ODOO.FILTER.VALUE("Relation Filter")`);
    await animationFrame();
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        label: "Relation Filter",
        modelName: "partner",
    });
    await animationFrame();
    const [filter] = model.getters.getGlobalFilters();
    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "in", ids: [1] },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("1");

    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "in", ids: [1, 2] },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("1, 2");

    await setGlobalFilterValue(model, {
        id: filter.id,
        value: { operator: "in", ids: [2] },
    });
    await animationFrame();
    expect(getCellValue(model, "A10")).toBe("2");
});

test("ODOO.FILTER.VALUE with escaped quotes in the filter label", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: 'my "special" filter',
        defaultValue: { operator: "ilike", strings: ["Jean-Jacques"] },
    });
    setCellContent(model, "A1", '=ODOO.FILTER.VALUE("my \\"special\\" filter")');
    expect(getCellValue(model, "A1")).toBe("Jean-Jacques");
});

test("ODOO.FILTER.VALUE formulas are updated when filter label is changed", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Cuillère",
    });
    setCellContent(
        model,
        "A10",
        `=ODOO.FILTER.VALUE("Cuillère") & ODOO.FILTER.VALUE( "Cuillère" )`
    );
    const [filter] = model.getters.getGlobalFilters();
    const newFilter = {
        ...filter,
        type: "date",
        label: "Interprete",
    };
    await editGlobalFilter(model, newFilter);
    expect(getCellFormula(model, "A10")).toBe(
        `=ODOO.FILTER.VALUE("Interprete") & ODOO.FILTER.VALUE("Interprete")`
    );
});

test("Exporting data does not remove value from model", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Cuillère",
    });
    await setGlobalFilterValue(model, {
        id: "42",
        value: { operator: "ilike", strings: ["Hello export bug"] },
    });
    const [filter] = model.getters.getGlobalFilters();
    expect(model.getters.getGlobalFilterValue(filter.id).strings).toEqual(["Hello export bug"]);
    model.exportData();
    expect(model.getters.getGlobalFilterValue(filter.id).strings).toEqual(["Hello export bug"]);
});

test("Can undo-redo a ADD_GLOBAL_FILTER", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Cuillère",
    });
    expect(model.getters.getGlobalFilters().length).toBe(1);
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getGlobalFilters().length).toBe(0);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getGlobalFilters().length).toBe(1);
});

test("Can undo-redo a REMOVE_GLOBAL_FILTER", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Cuillère",
    });
    await removeGlobalFilter(model, "42");
    expect(model.getters.getGlobalFilters().length).toBe(0);
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getGlobalFilters().length).toBe(1);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getGlobalFilters().length).toBe(0);
});

test("Can undo-redo a EDIT_GLOBAL_FILTER", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Cuillère",
    });
    await editGlobalFilter(model, {
        id: "42",
        type: "text",
        label: "Arthouuuuuur",
    });
    expect(model.getters.getGlobalFilters()[0].label).toBe("Arthouuuuuur");
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getGlobalFilters()[0].label).toBe("Cuillère");
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getGlobalFilters()[0].label).toBe("Arthouuuuuur");
});

test("Can undo-redo a MOVE_GLOBAL_FILTER", async function () {
    const { model } = await createModelWithDataSource();
    const filter1 = {
        id: 1,
        type: "text",
        label: "Filter 1",
    };
    const filter2 = {
        id: 2,
        type: "text",
        label: "Filter 2",
    };
    const filter3 = {
        id: 3,
        type: "text",
        label: "Filter 3",
    };
    addGlobalFilter(model, filter1, {});
    addGlobalFilter(model, filter2, {});
    addGlobalFilter(model, filter3, {});

    moveGlobalFilter(model, filter1.id, 1);
    expect(model.getters.getGlobalFilters()[1].id).toBe(filter1.id);

    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getGlobalFilters()[0].id).toBe(filter1.id);

    model.dispatch("REQUEST_REDO");
    expect(model.getters.getGlobalFilters()[1].id).toBe(filter1.id);
});

test("pivot headers won't change when adding a filter ", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        pivotType: "static",
    });
    expect(getCellValue(model, "A3")).toBe("xphone");
    expect(getCellValue(model, "A4")).toBe("xpad");
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            label: "Relation Filter",
            modelName: "product",
            defaultValue: { operator: "in", ids: [41] },
        },
        { pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } } }
    );
    expect(getCellValue(model, "A3")).toBe("xphone");
    expect(getCellValue(model, "B3")).toBe("");
    expect(getCellValue(model, "A4")).toBe("xpad");
    expect(getCellValue(model, "B4")).toBe(121);
});

test("load data only once if filter is not active (without default value)", async function () {
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                cells: {
                    A1: '=PIVOT.VALUE("1", "probability:sum")',
                },
            },
        ],
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ fieldName: "foo" }],
                domain: [],
                measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [{ fieldName: "bar" }],
                context: {},
            },
        },
        globalFilters: [
            {
                id: "filterId",
                type: "date",
                label: "my filter",
            },
        ],
    };
    const { model } = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, { model, method, kwargs }) {
            if (model === "partner" && method === "formatted_read_grouping_sets") {
                expect.step(`${model}/${method}`);
            }
        },
    });
    await waitForDataLoaded(model);
    expect.verifySteps(["partner/formatted_read_grouping_sets"]);
    expect(getCellValue(model, "A1")).toBe(131);
});

test("load data only once if filter is active (with a default value)", async function () {
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                cells: {
                    A1: '=PIVOT.VALUE("1", "probability:sum")',
                },
            },
        ],
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ fieldName: "foo" }],
                domain: [],
                measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [{ fieldName: "bar" }],
                context: {},
                fieldMatching: { filterId: { chain: "date", type: "date" } },
            },
        },
        globalFilters: [
            {
                id: "filterId",
                type: "date",
                label: "my filter",
                defaultValue: "this_year",
            },
        ],
    };
    const { model } = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, { model, method, kwargs }) {
            if (model === "partner" && method === "formatted_read_grouping_sets") {
                expect.step(`${model}/${method}`);
            }
        },
    });
    await waitForDataLoaded(model);
    expect.verifySteps(["partner/formatted_read_grouping_sets"]);
    expect(getCellValue(model, "A1")).toBe("");
});

test("don't reload data if an empty filter is added", async function () {
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                cells: {
                    A1: '=PIVOT.VALUE("1", "probability:sum")',
                },
            },
        ],
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ fieldName: "foo" }],
                domain: [],
                measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [{ fieldName: "bar" }],
                context: {},
            },
        },
    };
    const { model } = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, { model, method, kwargs }) {
            if (model === "partner" && method === "formatted_read_grouping_sets") {
                expect.step(`${model}/${method}`);
            }
        },
    });
    await waitForDataLoaded(model);
    expect.verifySteps(["partner/formatted_read_grouping_sets"]);
    expect(getCellValue(model, "A1")).toBe(131);
    addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "This month",
        defaultValue: undefined, // no default value!
    });
    expect(getCellValue(model, "A1")).toBe(131);
    expect.verifySteps([]);
});

test("don't load data if a filter is added but the data is not needed", async function () {
    const spreadsheetData = {
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ fieldName: "foo" }],
                domain: [],
                measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [{ fieldName: "bar" }],
                context: {},
                fieldMatching: {},
            },
        },
    };
    const { model } = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, { model, method, kwargs }) {
            if (model === "partner" && method === "formatted_read_grouping_sets") {
                expect.step(`${model}/${method}`);
            }
        },
    });
    expect.verifySteps([]);
    model.dispatch("ADD_GLOBAL_FILTER", {
        filter: {
            id: "42",
            type: "date",
            label: "This month",
            defaultValue: "this_month",
        },
        pivot: {
            1: { chain: "date", type: "date" },
        },
    });
    expect.verifySteps([]);
    setCellContent(model, "A1", `=PIVOT.VALUE("1", "probability:sum")`);
    expect(getCellValue(model, "A1")).toBe("Loading...");
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe("");
    expect.verifySteps(["partner/formatted_read_grouping_sets"]);
});

test("don't load data if a filter is activated but the data is not needed", async function () {
    const spreadsheetData = {
        pivots: {
            1: {
                type: "ODOO",
                columns: [{ fieldName: "foo" }],
                domain: [],
                measures: [{ id: "probability:sum", fieldName: "probability", aggregator: "sum" }],
                model: "partner",
                rows: [{ fieldName: "bar" }],
                context: {},
                fieldMatching: { filterId: { chain: "date", type: "date" } },
            },
        },
        globalFilters: [
            {
                id: "filterId",
                type: "date",
                label: "my filter",
            },
        ],
    };
    const { model } = await createModelWithDataSource({
        spreadsheetData,
        mockRPC: function (route, { model, method, kwargs }) {
            if (model === "partner" && method === "formatted_read_grouping_sets") {
                expect.step(`${model}/${method}`);
            }
        },
    });
    expect.verifySteps([]);
    const year = DateTime.now().year;
    model.dispatch("SET_GLOBAL_FILTER_VALUE", {
        id: "filterId",
        value: { type: "year", year },
    });

    expect.verifySteps([]);
    setCellContent(model, "A1", `=PIVOT.VALUE("1", "probability:sum")`);
    expect(getCellValue(model, "A1")).toBe("Loading...");
    await animationFrame();
    expect(getCellValue(model, "A1")).toBe("");
    expect.verifySteps(["partner/formatted_read_grouping_sets"]);
});

test("Default value defines value", async function () {
    const { model } = await createSpreadsheetWithPivot();
    const label = "This year";
    const defaultValue = { operator: "ilike", strings: ["value"] };
    await addGlobalFilter(model, {
        id: "42",
        type: "text",
        label,
        defaultValue,
    });
    const [filter] = model.getters.getGlobalFilters();
    expect(model.getters.getGlobalFilterValue(filter.id)).toEqual(defaultValue);
});

test("Default value defines value at model loading", async function () {
    const label = "This year";
    const defaultValue = { operator: "ilike", strings: ["value"] };
    const model = new Model({
        globalFilters: [{ type: "text", label, defaultValue, fields: {}, id: "1" }],
    });
    const [filter] = model.getters.getGlobalFilters();
    expect(model.getters.getGlobalFilterValue(filter.id)).toEqual(defaultValue);
});

test("filter display value of year filter is a range of dates", async function () {
    mockDate("2023-10-10 00:00:00");
    const { model } = await createSpreadsheetWithPivotAndList();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    const [filter] = model.getters.getGlobalFilters();
    const values = model.getters.getFilterDisplayValue(filter.label);
    expect(values[0][0].value).toBe(toNumber("2023-01-01", DEFAULT_LOCALE));
    expect(values[1][0].value).toBe(toNumber("2023-12-31", DEFAULT_LOCALE));
});

test("Export global filters for excel", async function () {
    const { model } = await createSpreadsheetWithPivotAndList();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER);
    const [filter] = model.getters.getGlobalFilters();
    const filterPlugin = model["handlers"].find(
        (handler) => handler instanceof GlobalFiltersCoreViewPlugin
    );
    const exportData = { styles: [], sheets: [], formats: {} };
    filterPlugin.exportForExcel(exportData);
    const filterSheet = exportData.sheets[0];
    expect(filterSheet).not.toBe(undefined, {
        message: "A sheet to export global filters was created",
    });
    expect(filterSheet.cells["A1"]).toBe("Filter");
    expect(filterSheet.cells["A2"]).toBe(filter.label);
    expect(filterSheet.cells["B1"]).toBe("Value");
    expect(filterSheet.cells["B2"]).toBe(
        String(model.getters.getFilterDisplayValue(filter.label)[0][0].value)
    );
    expect(filterSheet.cells["C2"]).toBe(
        String(model.getters.getFilterDisplayValue(filter.label)[1][0].value)
    );
    model.exportXLSX(); // should not crash
});

test("Export from/to global filters for excel", async function () {
    const { model } = await createModelWithDataSource();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "Date Filter",
    });
    await setGlobalFilterValue(model, {
        id: "42",
        value: {
            type: "range",
            from: "2020-01-01",
            to: "2021-01-01",
        },
    });
    const [filter] = model.getters.getGlobalFilters();
    const filterPlugin = model["handlers"].find(
        (handler) => handler instanceof GlobalFiltersCoreViewPlugin
    );
    const exportData = { styles: {}, formats: {}, sheets: [] };
    filterPlugin.exportForExcel(exportData);
    const filterSheet = exportData.sheets[0];
    expect(filterSheet.cells["A1"]).toBe("Filter");
    expect(filterSheet.cells["A2"]).toBe(filter.label);
    expect(filterSheet.cells["B1"]).toBe("Value");
    expect(filterSheet.cells["B2"]).toBe("43831");
    expect(filterSheet.cells["C2"]).toBe("44197");
    expect(filterSheet.formats["B2"]).toBe(1);
    expect(filterSheet.formats["C2"]).toBe(1);
    expect(exportData.formats[1]).toBe("m/d/yyyy");
    const { model: exportedModel } = await createModelWithDataSource({
        spreadsheetData: exportData,
    });
    const sheetId = exportData.sheets.at(-1).id;
    expect(getCell(exportedModel, "B2", sheetId).format).toBe("m/d/yyyy");
    expect(getCell(exportedModel, "C2", sheetId).format).toBe("m/d/yyyy");
});

test("Date filter automatic default value for years filter", async function () {
    const label = "This year";
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(model, {
        id: "1",
        type: "date",
        label,
        defaultValue: "this_year",
    });
    expect(model.getters.getGlobalFilterValue("1")).toEqual({
        type: "year",
        year: DateTime.local().year,
    });
});

test("Date filter automatic default value for month filter", async function () {
    mockDate("2022-03-10 00:00:00");
    const label = "This month";
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(model, {
        id: "1",
        type: "date",
        label,
        defaultValue: "this_month",
    });
    expect(model.getters.getGlobalFilterValue("1")).toEqual({
        type: "month",
        year: 2022,
        month: 3,
    });
});

test("Date filter automatic default value for quarter filter", async function () {
    mockDate("2022-12-10 00:00:00");
    const label = "This quarter";
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(model, {
        id: "1",
        type: "date",
        label,
        defaultValue: "this_quarter",
    });
    expect(model.getters.getGlobalFilterValue("1")).toEqual({
        type: "quarter",
        year: 2022,
        quarter: 4,
    });
});

test("Date filter automatic undefined values for from_to filter", async function () {
    const label = "From to";
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(model, {
        id: "1",
        type: "date",
        label,
    });
    expect(model.getters.getGlobalFilterValue("1")).toBe(undefined);
});

test("Date filter automatic default value at model loading", async function () {
    const label = "This year";
    const model = new Model({
        globalFilters: [
            {
                type: "date",
                label,
                defaultValue: "this_year",
                id: "1",
            },
        ],
    });
    expect(model.getters.getGlobalFilterValue("1")).toEqual({
        type: "year",
        year: DateTime.local().year,
    });
});

test("Relative date filter at model loading", async function () {
    const label = "Last Month";
    const defaultValue = "last_30_days";
    const model = new Model({
        globalFilters: [
            {
                type: "date",
                label,
                defaultValue,
                fields: {},
                id: "1",
            },
        ],
    });
    expect(model.getters.getGlobalFilterValue("1")).toEqual({
        type: "relative",
        period: defaultValue,
    });
});

test("Relative date filter display value", async function () {
    mockDate("2022-05-16 00:00:00");
    const label = "Last Month";
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label,
        defaultValue: "year_to_date",
    });
    const values = model.getters.getFilterDisplayValue(label);
    expect(values[0][0].value).toBe(toNumber("2022-01-01", DEFAULT_LOCALE));
    expect(values[1][0].value).toBe(toNumber("2022-05-16", DEFAULT_LOCALE));
});

test("Relative date filter domain value", async function () {
    mockDate("2022-05-16 00:00:00");
    const label = "Last Month";
    const { model } = await createSpreadsheetWithPivot();
    /**@type GlobalFilter */
    const filter = {
        id: "42",
        type: "date",
        label,
        defaultValue: "last_7_days",
    };
    await addGlobalFilter(model, filter, {
        pivot: { "PIVOT#1": { chain: "date", type: "date" } },
    });
    let computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(7);
    assertDateDomainEqual("date", "2022-05-10", "2022-05-16", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "year_to_date" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    assertDateDomainEqual("date", "2022-01-01", "2022-05-16", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "last_30_days" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(30);
    assertDateDomainEqual("date", "2022-04-17", "2022-05-16", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "last_90_days" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(90);
    assertDateDomainEqual("date", "2022-02-16", "2022-05-16", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "today" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(1);
    assertDateDomainEqual("date", "2022-05-16", "2022-05-16", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "yesterday" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(1);
    assertDateDomainEqual("date", "2022-05-15", "2022-05-15", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "month_to_date" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(16);
    assertDateDomainEqual("date", "2022-05-01", "2022-05-16", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "last_month" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(30);
    assertDateDomainEqual("date", "2022-04-01", "2022-04-30", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "last_12_months" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(365);
    assertDateDomainEqual("date", "2021-05-01", "2022-04-30", computedDomain);
});

test("Relative date filter with offset domain value", async function () {
    mockDate("2022-05-16 00:00:00");
    const label = "Last Month";
    const { model } = await createSpreadsheetWithPivot();
    /**@type GlobalFilter */
    const filter = {
        id: "42",
        type: "date",
        label,
        defaultValue: "last_7_days",
    };
    await addGlobalFilter(model, filter, {
        pivot: { "PIVOT#1": { chain: "date", type: "date", offset: -1 } },
    });
    let computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(7);
    assertDateDomainEqual("date", "2022-05-03", "2022-05-09", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "year_to_date" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    assertDateDomainEqual("date", "2021-01-01", "2021-05-16", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "last_30_days" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(30);
    assertDateDomainEqual("date", "2022-03-18", "2022-04-16", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "last_90_days" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(90);
    assertDateDomainEqual("date", "2021-11-18", "2022-02-15", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "today" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(1);
    assertDateDomainEqual("date", "2022-05-15", "2022-05-15", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "yesterday" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(1);
    assertDateDomainEqual("date", "2022-05-14", "2022-05-14", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "month_to_date" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(16);
    assertDateDomainEqual("date", "2022-04-01", "2022-04-16", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "last_month" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(31);
    assertDateDomainEqual("date", "2022-03-01", "2022-03-31", computedDomain);

    await setGlobalFilterValue(model, {
        id: "42",
        value: { type: "relative", period: "last_12_months" },
    });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(getDateDomainDurationInDays(computedDomain)).toBe(365);
    assertDateDomainEqual("date", "2020-05-01", "2021-04-30", computedDomain);
});

test("from_to date filter at model loading", async function () {
    const model = new Model({
        globalFilters: [
            {
                type: "date",
                label: "From To",
                fields: {},
                id: "1",
            },
        ],
    });
    expect(model.getters.getGlobalFilterValue("1")).toBe(undefined);
});

test("from_to date filter domain value on a date field", async function () {
    const { model } = await createSpreadsheetWithPivot();
    /**@type GlobalFilter */
    const filter = {
        id: "42",
        type: "date",
        label: "From To",
    };
    const value = {
        type: "range",
        from: "2022-01-01",
        to: "2022-05-16",
    };
    await addGlobalFilter(model, filter, {
        pivot: { "PIVOT#1": { chain: "date", type: "date" } },
    });
    await setGlobalFilterValue(model, { id: "42", value });
    const computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    assertDateDomainEqual("date", "2022-01-01", "2022-05-16", computedDomain);
});

test("from_to date filter domain value on a datetime field UTC+2", async function () {
    mockTimeZone(+2); // UTC+2
    const { model } = await createSpreadsheetWithPivot();
    /**@type GlobalFilter */
    const filter = {
        id: "42",
        type: "date",
        label: "From To",
    };
    const value = {
        type: "range",
        from: "2022-01-01",
        to: "2022-05-16",
    };
    await addGlobalFilter(model, filter, {
        pivot: { "PIVOT#1": { chain: "date", type: "datetime" } },
    });
    await setGlobalFilterValue(model, { id: "42", value });
    const computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    assertDateDomainEqual("date", "2021-12-31 22:00:00", "2022-05-16 21:59:59", computedDomain);
});

test("from_to date filter domain value on a datetime field UTC-2", async function () {
    mockTimeZone(-2); // UTC-2
    const { model } = await createSpreadsheetWithPivot();
    /**@type GlobalFilter */
    const filter = {
        id: "42",
        type: "date",
        label: "From To",
    };
    const value = {
        type: "range",
        from: "2022-01-01",
        to: "2022-05-16",
    };
    await addGlobalFilter(model, filter, {
        pivot: { "PIVOT#1": { chain: "date", type: "datetime" } },
    });
    await setGlobalFilterValue(model, { id: "42", value });
    const computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    assertDateDomainEqual("date", "2022-01-01 02:00:00", "2022-05-17 01:59:59", computedDomain);
});

test("set 'from_to' date filter domain value from specific date --> to specific date", async function () {
    const { model } = await createSpreadsheetWithPivot();
    /**@type GlobalFilter */
    const filter = {
        id: "42",
        type: "date",
        label: "From To",
    };
    const value = {
        type: "range",
        from: "2022-01-01",
        to: "2022-05-16",
    };
    await addGlobalFilter(model, filter, {
        pivot: { "PIVOT#1": { chain: "date", type: "date" } },
    });
    await setGlobalFilterValue(model, { id: "42", value });
    const computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    assertDateDomainEqual("date", "2022-01-01", "2022-05-16", computedDomain);
});

test("set 'from_to' date filter domain value from specific date", async function () {
    const { model } = await createSpreadsheetWithPivot();
    /**@type GlobalFilter */
    const filter = {
        id: "42",
        type: "date",
        label: "From To",
    };
    const value = {
        type: "range",
        from: "2022-01-01",
        to: undefined,
    };
    await addGlobalFilter(model, filter, {
        pivot: { "PIVOT#1": { chain: "date", type: "date" } },
    });
    await setGlobalFilterValue(model, { id: "42", value });
    const computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(computedDomain).toEqual([["date", ">=", "2022-01-01"]]);
});

test("set 'from_to' date filter domain value to specific date", async function () {
    const { model } = await createSpreadsheetWithPivot();
    /**@type GlobalFilter */
    const filter = {
        id: "42",
        type: "date",
        label: "From To",
    };
    const value = {
        type: "range",
        from: undefined,
        to: "2022-05-16",
    };
    await addGlobalFilter(model, filter, {
        pivot: { "PIVOT#1": { chain: "date", type: "date" } },
    });
    await setGlobalFilterValue(model, { id: "42", value });
    const computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(computedDomain).toEqual([["date", "<=", "2022-05-16"]]);
});

test("can clear 'from_to' date filter values", async function () {
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        label: "From To",
    });
    const [filter] = model.getters.getGlobalFilters();
    const value = {
        type: "range",
        from: "2022-01-01",
        to: "2022-05-16",
    };
    await setGlobalFilterValue(model, { id: "42", value });
    model.dispatch("SET_GLOBAL_FILTER_VALUE", { id: filter.id });
    expect(model.getters.getGlobalFilterValue(filter.id)).toEqual(undefined, {
        message: "can clear 'from_to' date filter values",
    });
});

test("A date filter without a year value yields an empty domain", async function () {
    mockDate("2022-05-16 00:00:00");
    const { model } = await createSpreadsheetWithPivot();
    const filter = {
        id: "43",
        type: "date",
        label: "This Year",
        defaultValue: "this_year",
    };
    await addGlobalFilter(model, filter, {
        pivot: { "PIVOT#1": { chain: "date", type: "date", offset: 0 } },
    });
    let computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    assertDateDomainEqual("date", "2022-01-01", "2022-12-31", computedDomain);
    model.dispatch("SET_GLOBAL_FILTER_VALUE", { id: filter.id });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(computedDomain).toEqual([]);
});

test("Date filter with automatic default without a year value yields an empty domain", async function () {
    mockDate("2022-05-16 00:00:00");
    const { model } = await createSpreadsheetWithPivot();
    const filter = {
        id: "43",
        type: "date",
        label: "This Year",
        defaultValue: "this_year",
    };
    await addGlobalFilter(model, filter, {
        pivot: { "PIVOT#1": { chain: "date", type: "date", offset: 0 } },
    });
    let computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    assertDateDomainEqual("date", "2022-01-01", "2022-12-31", computedDomain);
    model.dispatch("SET_GLOBAL_FILTER_VALUE", { id: filter.id });
    computedDomain = model.getters.getPivotComputedDomain("PIVOT#1");
    expect(computedDomain).toEqual([]);
});

test("Can set a value to a relation filter from the SET_MANY_GLOBAL_FILTER_VALUE command", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
    });
    model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
        filters: [{ filterId: "42", value: { operator: "in", ids: [31] } }],
    });
    expect(model.getters.getGlobalFilterValue("42")).toEqual({ operator: "in", ids: [31] });
    model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
        filters: [{ filterId: "42" }],
    });
    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);
});

test("Can set a value to a date filter from the SET_MANY_GLOBAL_FILTER_VALUE command", async function () {
    mockDate("2022-07-14 00:00:00");
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(model, {
        id: "42",
        type: "date",
        defaultValue: "this_month",
    });
    const newValue = { type: "month", year: 2016, month: 5 };
    model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
        filters: [{ filterId: "42", value: newValue }],
    });
    expect(model.getters.getGlobalFilterValue("42")).toEqual(newValue);
    model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
        filters: [{ filterId: "42" }],
    });
    expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);
});

test("getFiltersMatchingPivot return correctly matching filter according to cell formula", async function () {
    mockDate("2022-07-14 00:00:00");
    const serverData = getBasicServerData();
    serverData.models.partner.records = [
        {
            id: 10000,
            product_id: false,
        },
    ];
    const { model } = await createSpreadsheetWithPivot({
        serverData,
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                    <field name="date" interval="year" type="col"/>
                    <field name="date" interval="month" type="col"/>
                    <field name="date" interval="quarter" type="col"/>
                </pivot>`,
    });
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            label: "relational filter",
        },
        {
            pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } },
        }
    );
    await addGlobalFilter(
        model,
        {
            id: "43",
            type: "date",
            label: "date filter 1",
        },
        {
            pivot: { "PIVOT#1": { chain: "date", type: "date" } },
        }
    );
    const relationalFilters1 = getFiltersMatchingPivot(model, '=PIVOT.HEADER(1,"product_id",37)');
    expect(relationalFilters1).toEqual([{ filterId: "42", value: { operator: "in", ids: [37] } }]);
    const relationalFilters2 = getFiltersMatchingPivot(model, '=PIVOT.HEADER(1,"product_id","41")');
    expect(relationalFilters2).toEqual([{ filterId: "42", value: { operator: "in", ids: [41] } }]);
    const relationalFiltersWithNoneValue = getFiltersMatchingPivot(
        model,
        '=PIVOT.HEADER(1,"#product_id",1)'
    );
    expect(relationalFiltersWithNoneValue).toEqual([{ filterId: "42", value: undefined }]);
    const dateFilters1 = getFiltersMatchingPivot(model, '=PIVOT.HEADER(1,"date:month","08/2016")');
    expect(dateFilters1).toEqual([
        { filterId: "43", value: { type: "month", year: 2016, month: 8 } },
    ]);
    const december = getFiltersMatchingPivot(model, '=PIVOT.HEADER(1,"date:month","12/2016")');
    expect(december).toEqual([{ filterId: "43", value: { type: "month", year: 2016, month: 12 } }]);
    const q4 = getFiltersMatchingPivot(model, '=PIVOT.HEADER(1,"date:quarter","4/2016")');
    expect(q4).toEqual([{ filterId: "43", value: { type: "quarter", year: 2016, quarter: 4 } }]);
    const dateFilters2 = getFiltersMatchingPivot(model, '=PIVOT.HEADER(1,"date:year","2016")');
    expect(dateFilters2).toEqual([{ filterId: "43", value: { type: "year", year: 2016 } }]);
});

test("getFiltersMatchingPivot return an empty array if there is no pivot formula", async function () {
    const { model } = await createModelWithDataSource();
    const result = getFiltersMatchingPivot(model, "=1");
    expect(result).toEqual([]);
});

test("getFiltersMatchingPivot return correctly matching filter according to cell formula with multi-levels grouping", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                    <field name="date" interval="month" type="row"/>
                </pivot>`,
    });
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            label: "relational filter",
        },
        {
            pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } },
        }
    );
    await addGlobalFilter(
        model,
        {
            id: "43",
            type: "date",
            label: "date filter 1",
            dateValue: "this_month",
        },
        {
            pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } },
        }
    );
    const filters = getFiltersMatchingPivot(
        model,
        '=PIVOT.HEADER(1,"date:month","08/2016","product_id","41")'
    );
    expect(filters).toEqual([{ filterId: "42", value: { operator: "in", ids: [41] } }]);
});

test("getFiltersMatchingPivot return correctly matching filter according to cell formula with __count and positional argument", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="__count" type="measure"/>
                </pivot>`,
    });
    setCellContent(model, "B3", '=PIVOT.VALUE(1, "__count", "#product_id", 1)');
    await addGlobalFilter(
        model,
        {
            id: "42",
            label: "Relation",
            type: "relation",
        },
        { pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } } }
    );
    const filters = getFiltersMatchingPivot(model, getCellFormula(model, "B3"));
    expect(filters).toEqual([
        {
            filterId: "42",
            value: { operator: "in", ids: [37] },
        },
    ]);
});

test("getFiltersMatchingPivot return correctly matching filter according to cell formula with positional argument", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                    <pivot>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
    });
    setCellContent(model, "B3", '=PIVOT.VALUE(1, "probability", "#product_id", 1)');
    await addGlobalFilter(
        model,
        {
            id: "42",
            label: "Relation",
            type: "relation",
        },
        { pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } } }
    );
    const filters = getFiltersMatchingPivot(model, getCellFormula(model, "B3"));
    expect(filters).toEqual([
        {
            filterId: "42",
            value: { operator: "in", ids: [37] },
        },
    ]);
});

test("getFiltersMatchingPivot return correctly matching filter when there is a filter with no field defined", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
    });
    const filters = getFiltersMatchingPivot(model, getCellFormula(model, "B3"));
    expect(filters).toEqual([]);
});

test("getFiltersMatchingPivot return empty filter for cell formula without any argument", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                    <pivot>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
    });
    setCellContent(model, "B3", '=PIVOT.VALUE(1, "probability")');
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
        },
        { pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } } }
    );
    const filters = getFiltersMatchingPivot(model, getCellFormula(model, "B3"));
    expect(filters).toEqual([]);
});

test("getFiltersMatchingPivot return empty filter when no records is related to the pivot cell", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                    <pivot>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
    });
    setCellContent(model, "B3", '=PIVOT.VALUE(1, "probability", "#product_id", 1)');
    await addGlobalFilter(model, {
        id: "42",
        type: "relation",
        defaultValue: { operator: "in", ids: [1] },
        pivotFields: { 1: { field: "product_id", type: "many2one" } },
    });
    const filters = getFiltersMatchingPivot(model, getCellFormula(model, "B3"));
    expect(filters).toEqual([]);
});

test("field matching is removed when pivot is deleted", async function () {
    const { model } = await createSpreadsheetWithPivot();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER, {
        pivot: DEFAULT_FIELD_MATCHINGS,
    });
    const [pivotId] = model.getters.getPivotIds();
    const [filter] = model.getters.getGlobalFilters();
    const matching = {
        chain: "date",
        type: "date",
    };
    expect(model.getters.getPivotFieldMatching(pivotId, filter.id)).toEqual(matching);
    model.dispatch("REMOVE_PIVOT", { pivotId });
    expect(() => model.getters.getPivotFieldMatching(pivotId, filter.id)).toThrow(undefined, {
        message: "Pivot does not exist",
    });
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getPivotFieldMatching(pivotId, filter.id)).toEqual(matching);
    model.dispatch("REQUEST_REDO");
    expect(() => model.getters.getPivotFieldMatching(pivotId, filter.id)).toThrow(undefined, {
        message: "Pivot does not exist",
    });
});

test("field matching is removed when list is deleted", async function () {
    const { model } = await createSpreadsheetWithList();
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER, {
        list: DEFAULT_LIST_FIELD_MATCHINGS,
    });
    const [listId] = model.getters.getListIds();
    const [filter] = model.getters.getGlobalFilters();
    const matching = {
        chain: "date",
        type: "date",
    };
    expect(model.getters.getListFieldMatching(listId, filter.id)).toEqual(matching);
    model.dispatch("REMOVE_ODOO_LIST", { listId });
    expect(() => model.getters.getListFieldMatching(listId, filter.id)).toThrow(undefined, {
        message: "List does not exist",
    });
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getListFieldMatching(listId, filter.id)).toEqual(matching);
    model.dispatch("REQUEST_REDO");
    expect(() => model.getters.getListFieldMatching(listId, filter.id)).toThrow(undefined, {
        message: "List does not exist",
    });
});

test("field matching is removed when an Odoo chart is deleted", async function () {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_pie" });
    const sheetId = model.getters.getActiveSheetId();
    const [chartId] = model.getters.getChartIds(sheetId);
    await addGlobalFilter(model, THIS_YEAR_GLOBAL_FILTER, {
        chart: { [chartId]: { chain: "date", type: "date" } },
    });
    const [filter] = model.getters.getGlobalFilters();
    const matching = {
        chain: "date",
        type: "date",
    };
    expect(model.getters.getOdooChartFieldMatching(chartId, filter.id)).toEqual(matching);
    model.dispatch("DELETE_FIGURE", {
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId,
    });
    expect(() => model.getters.getOdooChartFieldMatching(chartId, filter.id)).toThrow(undefined, {
        message: "Chart does not exist",
    });
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getOdooChartFieldMatching(chartId, filter.id)).toEqual(matching);
    model.dispatch("REQUEST_REDO");
    expect(() => model.getters.getOdooChartFieldMatching(chartId, filter.id)).toThrow(undefined, {
        message: "Chart does not exist",
    });
});

test("getFiltersMatchingPivot return correctly matching filter with the 'measure' special field", async function () {
    const { model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                <field name="product_id" type="row"/>
                <field name="probability" type="measure"/>
                </pivot>`,
    });
    await addGlobalFilter(model, {
        id: "42",
        label: "fake",
        type: "relation",
    });
    const filters = getFiltersMatchingPivot(model, getCellFormula(model, "B2"));
    expect(filters).toEqual([]);
});

test("Reject date filters with invalid field Matchings", async () => {
    const { model } = await createSpreadsheetWithPivotAndList();
    insertChartInSpreadsheet(model);
    const chartId = model.getters.getOdooChartIds()[0];

    const filter = (label) => ({
        id: "42",
        label,
        type: "date",
    });
    const resultPivot = await addGlobalFilter(model, filter("fake1"), {
        pivot: { "PIVOT#1": { offset: -2 } },
    });
    expect(resultPivot.reasons).toEqual([CommandResult.InvalidFieldMatch]);
    const resultList = await addGlobalFilter(model, filter("fake2"), {
        list: { 1: { offset: -2 } },
    });
    expect(resultList.reasons).toEqual([CommandResult.InvalidFieldMatch]);
    const resultChart = await addGlobalFilter(model, filter("fake3"), {
        chart: { [chartId]: { offset: -2 } },
    });
    expect(resultChart.reasons).toEqual([CommandResult.InvalidFieldMatch]);
});

test("Can create a relative date filter with an empty default value", async () => {
    const { model } = await createSpreadsheetWithPivot();
    const filter = {
        id: "42",
        label: "test",
        type: "date",
    };
    const result = await addGlobalFilter(model, filter);
    expect(result.isSuccessful).toBe(true);
});

test("allowDispatch of MOVE_GLOBAL_FILTERS", function () {
    const model = new Model();
    const filter1 = {
        id: "1",
        type: "text",
        label: "Filter 1",
    };
    const filter2 = {
        id: "2",
        type: "text",
        label: "Filter 2",
    };
    addGlobalFilter(model, filter1, {});
    addGlobalFilter(model, filter2, {});

    let result = moveGlobalFilter(model, "notAnId", 1);
    expect(result.reasons).toEqual([CommandResult.FilterNotFound]);

    result = moveGlobalFilter(model, filter1.id, -1);
    expect(result.reasons).toEqual([CommandResult.InvalidFilterMove]);

    result = moveGlobalFilter(model, filter2.id, 1);
    expect(result.reasons).toEqual([CommandResult.InvalidFilterMove]);
});

test("can move a global filter", function () {
    const model = new Model();
    const filter1 = {
        id: 1,
        type: "text",
        label: "Filter 1",
    };
    const filter2 = {
        id: 2,
        type: "text",
        label: "Filter 2",
    };
    const filter3 = {
        id: 3,
        type: "text",
        label: "Filter 3",
    };
    addGlobalFilter(model, filter1, {});
    addGlobalFilter(model, filter2, {});
    addGlobalFilter(model, filter3, {});

    moveGlobalFilter(model, filter1.id, 1);
    expect(model.getters.getGlobalFilters()[1].id).toBe(filter1.id);

    moveGlobalFilter(model, filter1.id, 1);
    expect(model.getters.getGlobalFilters()[2].id).toBe(filter1.id);

    moveGlobalFilter(model, filter1.id, -2);
    expect(model.getters.getGlobalFilters()[0].id).toBe(filter1.id);
});

test("Spreadsheet pivot are not impacted by global filter", function () {
    // This test is to ensure that the start of evaluation do not crash.
    // It will be removed as soon as the feature is implemented in spreadsheet.

    new Model({
        sheets: [{ id: "1" }],
        pivots: [
            {
                name: "Pivot",
                type: "SPREADSHEET",
                dataSet: {
                    zone: toZone("A1:D5"),
                    sheetId: "1",
                },
                rows: [],
                columns: [],
                measures: [],
            },
        ],
        globalFilters: [
            {
                id: "1",
                type: "date",
                label: "This year",
                defaultValue: "this_year",
            },
        ],
    });
    expect(1).toBe(1);
});

test("Updating the pivot domain should keep the global filter domain", async () => {
    mockDate("2022-04-16 00:00:00");
    const { model, pivotId } = await createSpreadsheetWithPivot();
    const filter = {
        id: "43",
        type: "date",
        label: "This Year",
        defaultValue: "this_year",
    };
    await addGlobalFilter(model, filter, {
        pivot: { [pivotId]: { chain: "date", type: "date", offset: 0 } },
    });
    let computedDomain = new Domain(model.getters.getPivotComputedDomain(pivotId));
    expect(computedDomain.toString()).toBe(
        `["&", ("date", ">=", "2022-01-01"), ("date", "<=", "2022-12-31")]`
    );
    model.dispatch("UPDATE_ODOO_PIVOT_DOMAIN", {
        pivotId,
        domain: [["foo", "in", [55]]],
    });
    computedDomain = new Domain(model.getters.getPivotComputedDomain(pivotId));
    expect(computedDomain.toString()).toBe(
        `["&", ("foo", "in", [55]), "&", ("date", ">=", "2022-01-01"), ("date", "<=", "2022-12-31")]`
    );
    model.dispatch("REQUEST_UNDO");
    computedDomain = new Domain(model.getters.getPivotComputedDomain(pivotId));
    expect(computedDomain.toString()).toBe(
        `["&", ("date", ">=", "2022-01-01"), ("date", "<=", "2022-12-31")]`
    );
});

test("Updating the pivot should keep the global filter domain", async () => {
    mockDate("2022-04-16 00:00:00");
    const { model, pivotId } = await createSpreadsheetWithPivot();
    const filter = {
        id: "43",
        type: "date",
        label: "This Year",
        defaultValue: "this_year",
    };
    await addGlobalFilter(model, filter, {
        pivot: { [pivotId]: { chain: "date", type: "date", offset: 0 } },
    });
    let computedDomain = new Domain(model.getters.getPivotComputedDomain(pivotId));
    expect(computedDomain.toString()).toBe(
        `["&", ("date", ">=", "2022-01-01"), ("date", "<=", "2022-12-31")]`
    );
    model.dispatch("UPDATE_PIVOT", {
        pivotId,
        pivot: {
            ...model.getters.getPivotCoreDefinition(pivotId),
            colGroupBys: [],
            rowGroupBys: [],
        },
    });
    computedDomain = new Domain(model.getters.getPivotComputedDomain(pivotId));
    expect(computedDomain.toString()).toBe(
        `["&", ("date", ">=", "2022-01-01"), ("date", "<=", "2022-12-31")]`
    );
    model.dispatch("REQUEST_UNDO");
    computedDomain = new Domain(model.getters.getPivotComputedDomain(pivotId));
    expect(computedDomain.toString()).toBe(
        `["&", ("date", ">=", "2022-01-01"), ("date", "<=", "2022-12-31")]`
    );
});

test("Updating a non-odoo pivot should not crash on global filter", async () => {
    const grid = {
        A1: "Customer",
        B1: "Price",
        C1: `=PIVOT(1)`,
        A2: "Alice",
        B2: "10",
        A3: "",
        B3: "20",
        A4: "Olaf",
        B4: "30",
    };
    const model = createModelFromGrid(grid);
    const pivot = {
        name: "Pivot",
        type: "SPREADSHEET",
        dataSet: {
            zone: toZone("A1:B4"),
            sheetId: model.getters.getActiveSheetId(),
        },
        rows: [{ fieldName: "Customer", order: "asc" }],
        columns: [],
        measures: [{ id: "price", fieldName: "Price", aggregator: "sum" }],
    };
    model.dispatch("ADD_PIVOT", { pivot, pivotId: "1" });
    model.dispatch("UPDATE_PIVOT", {
        pivotId: "1",
        pivot: {
            ...pivot,
            rows: [],
        },
    });
    expect(1).toBe(1);
});

test("Updating the list domain should keep the global filter domain", async () => {
    mockDate("2022-04-16 00:00:00");
    const { model } = await createSpreadsheetWithList();
    const filter = {
        id: "43",
        type: "date",
        label: "This Year",
        defaultValue: "this_year",
    };
    await addGlobalFilter(model, filter, {
        list: { 1: { chain: "date", type: "date", offset: 0 } },
    });
    let computedDomain = new Domain(model.getters.getListComputedDomain("1"));
    expect(computedDomain.toString()).toBe(
        `["&", ("date", ">=", "2022-01-01"), ("date", "<=", "2022-12-31")]`
    );
    const [listId] = model.getters.getListIds();
    model.dispatch("UPDATE_ODOO_LIST_DOMAIN", {
        listId,
        domain: [["foo", "in", [55]]],
    });
    computedDomain = new Domain(model.getters.getListComputedDomain("1"));
    expect(computedDomain.toString()).toBe(
        `["&", ("foo", "in", [55]), "&", ("date", ">=", "2022-01-01"), ("date", "<=", "2022-12-31")]`
    );
    model.dispatch("REQUEST_UNDO");
    computedDomain = new Domain(model.getters.getListComputedDomain("1"));
    expect(computedDomain.toString()).toBe(
        `["&", ("date", ">=", "2022-01-01"), ("date", "<=", "2022-12-31")]`
    );
});

test("Can add a boolean filter", async () => {
    const model = new Model();
    const filter = {
        id: "42",
        label: "test",
        type: "boolean",
    };
    model.dispatch("ADD_GLOBAL_FILTER", { filter });
    model.dispatch("SET_GLOBAL_FILTER_VALUE", { id: "42", value: { operator: "set" } });
    expect(model.getters.getGlobalFilterValue("42")).toEqual({ operator: "set" });
});

test("Add a boolean filter with a default value", async () => {
    const model = new Model();
    const filter = {
        id: "42",
        label: "test",
        type: "boolean",
        defaultValue: { operator: "set" },
    };
    model.dispatch("ADD_GLOBAL_FILTER", { filter });
    expect(model.getters.getGlobalFilterValue("42")).toEqual({ operator: "set" });
});

test("Check boolean filter domain", async () => {
    const model = new Model();
    const filter = {
        id: "42",
        label: "test",
        type: "boolean",
    };
    model.dispatch("ADD_GLOBAL_FILTER", { filter });
    const fieldMatching = { chain: "active", type: "boolean" };
    expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toString()).toEqual("[]");
    model.dispatch("SET_GLOBAL_FILTER_VALUE", { id: "42", value: { operator: "set" } });
    expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toString()).toEqual(
        `[("active", "!=", False)]`
    );
    model.dispatch("SET_GLOBAL_FILTER_VALUE", { id: "42", value: { operator: "not set" } });
    expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toString()).toEqual(
        `[("active", "=", False)]`
    );
});

test("Can add a selection filter", async () => {
    const model = new Model();
    const filter = {
        id: "42",
        label: "test",
        type: "selection",
        resModel: "res.currency",
        selectionField: "position",
    };
    addGlobalFilterWithoutReload(model, filter);
    await setGlobalFilterValue(model, {
        id: "42",
        value: { operator: "in", selectionValues: ["after"] },
    });
    expect(model.getters.getGlobalFilterValue("42")).toEqual({
        operator: "in",
        selectionValues: ["after"],
    });
});

test("Check selection filter domain", async () => {
    const model = new Model();
    const filter = {
        id: "42",
        label: "test",
        type: "selection",
        resModel: "res.currency",
        selectionField: "position",
    };
    addGlobalFilterWithoutReload(model, filter);
    const fieldMatching = { chain: "position", type: "selection" };
    expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toString()).toEqual("[]");
    await setGlobalFilterValue(model, {
        id: "42",
        value: { operator: "in", selectionValues: ["after"] },
    });
    expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toString()).toEqual(
        `[("position", "in", ["after"])]`
    );
    await setGlobalFilterValue(model, {
        id: "42",
        value: { operator: "in", selectionValues: ["before"] },
    });
    expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toString()).toEqual(
        `[("position", "in", ["before"])]`
    );
    await setGlobalFilterValue(model, {
        id: "42",
        value: { operator: "in", selectionValues: ["after", "before"] },
    });
    expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toString()).toEqual(
        `[("position", "in", ["after", "before"])]`
    );
});

for (const operator of ["in", "not in", "child_of"]) {
    test(`relation global filter with operator ${operator}`, async () => {
        const model = new Model();
        const filter = {
            id: "42",
            label: "test",
            type: "relation",
            defaultValue: { operator, ids: [1, 2] },
        };
        await addGlobalFilter(model, filter);
        const fieldMatching = { chain: "product_id", type: "many2one" };
        expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toJson()).toEqual([
            ["product_id", operator, [1, 2]],
        ]);
    });
}

for (const operator of ["ilike", "not ilike"]) {
    test(`relation global filter with text operator ${operator}`, async () => {
        const model = new Model();
        const filter = {
            id: "42",
            label: "test",
            type: "relation",
            defaultValue: { operator, strings: ["hello", "world"] },
        };
        await addGlobalFilter(model, filter);
        const fieldMatching = { chain: "product_id", type: "many2one" };
        expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toJson()).toEqual([
            "|",
            ["product_id", operator, "hello"],
            ["product_id", operator, "world"],
        ]);
    });
}

test("text global filter with starts_with operator", async () => {
    const { model } = await createSpreadsheetWithPivot();
    const filter = {
        id: "42",
        label: "test",
        type: "text",
        defaultValue: { operator: "starts with", strings: ["hello", "world"] },
    };
    await addGlobalFilter(model, filter);
    const fieldMatching = { chain: "product_id", type: "many2one" };
    expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toJson()).toEqual([
        "|",
        ["product_id", "=ilike", "hello%"],
        ["product_id", "=ilike", "world%"],
    ]);
});

for (const operator of ["ilike", "not ilike"]) {
    test(`text global filter with contains operator ${operator}`, async () => {
        const model = new Model();
        const filter = {
            id: "42",
            label: "test",
            type: "text",
            defaultValue: { operator, strings: ["hello", "world"] },
        };
        await addGlobalFilter(model, filter);
        const fieldMatching = { chain: "foo", type: "char" };
        expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toJson()).toEqual([
            "|",
            ["foo", operator, "hello"],
            ["foo", operator, "world"],
        ]);
    });
}

for (const operator of ["in", "not in"]) {
    test(`text global filter with operator ${operator}`, async () => {
        const model = new Model();
        const filter = {
            id: "42",
            label: "test",
            type: "text",
            defaultValue: { operator, strings: ["hello", "world"] },
        };
        await addGlobalFilter(model, filter);
        const fieldMatching = { chain: "foo", type: "char" };
        expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toJson()).toEqual([
            ["foo", operator, ["hello", "world"]],
        ]);
    });
}

test("Can add a numeric filter", async () => {
    const model = new Model();
    const filter = {
        id: "42",
        label: "test",
        type: "numeric",
    };
    model.dispatch("ADD_GLOBAL_FILTER", { filter });
    model.dispatch("SET_GLOBAL_FILTER_VALUE", {
        id: "42",
        value: { operator: "=", targetValue: 1998 },
    });
    expect(model.getters.getGlobalFilterValue("42")).toEqual({
        operator: "=",
        targetValue: 1998,
    });
});

test("Can add a numeric filter with a default value", async () => {
    const model = new Model();
    const filter = {
        id: "42",
        label: "test",
        type: "numeric",
        defaultValue: { operator: "=", targetValue: 1998 },
    };
    model.dispatch("ADD_GLOBAL_FILTER", { filter });
    expect(model.getters.getGlobalFilterValue("42")).toEqual({
        operator: "=",
        targetValue: 1998,
    });
});

test("Check numeric filter domain", async () => {
    const model = new Model();
    const filter = {
        id: "42",
        label: "test",
        type: "numeric",
    };
    model.dispatch("ADD_GLOBAL_FILTER", { filter });
    const fieldMatching = { chain: "probability", type: "numeric" };
    expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toString()).toEqual("[]");
    model.dispatch("SET_GLOBAL_FILTER_VALUE", {
        id: "42",
        value: { operator: "=", targetValue: 10 },
    });
    expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toString()).toEqual(
        `[("probability", "=", 10)]`
    );
    model.dispatch("SET_GLOBAL_FILTER_VALUE", {
        id: "42",
        value: { operator: "between", minimumValue: 1, maximumValue: 99 },
    });
    expect(model.getters.getGlobalFilterDomain("42", fieldMatching).toString()).toEqual(
        `["&", ("probability", ">=", 1), ("probability", "<=", 99)]`
    );
});

test("Undo/Redo of global filter update", async () => {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    const filter = {
        id: "43",
        type: "date",
        label: "This Year",
        defaultValue: "this_year",
    };
    await addGlobalFilter(model, filter, {
        pivot: { [pivotId]: { chain: "date", type: "date", offset: 0 } },
    });
    expect(model.getters.getPivotFieldMatching(pivotId, filter.id)).toEqual({
        chain: "date",
        type: "date",
        offset: 0,
    });
    model.dispatch("EDIT_GLOBAL_FILTER", {
        filter,
        pivot: {
            [pivotId]: { chain: "date", type: "date", offset: -1 },
        },
    });
    expect(model.getters.getPivotFieldMatching(pivotId, filter.id)).toEqual({
        chain: "date",
        type: "date",
        offset: -1,
    });
    undo(model);
    expect(model.getters.getPivotFieldMatching(pivotId, filter.id)).toEqual({
        chain: "date",
        type: "date",
        offset: 0,
    });
    redo(model);
    expect(model.getters.getPivotFieldMatching(pivotId, filter.id)).toEqual({
        chain: "date",
        type: "date",
        offset: -1,
    });
});

test("Default value of text filter", () => {
    const model = new Model();
    let result = addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "text",
        label: "Default value cannot be a string, should be an array",
        defaultValue: { operator: "ilike", strings: "default value" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "2",
        type: "text",
        label: "Default value is an array",
        defaultValue: { operator: "ilike", strings: ["default value"] },
    });
    expect(result.isSuccessful).toBe(true);

    result = addGlobalFilterWithoutReload(model, {
        id: "3",
        type: "text",
        label: "Default value is empty",
    });
    expect(result.isSuccessful).toBe(true);

    result = addGlobalFilterWithoutReload(model, {
        id: "4",
        type: "text",
        label: "Default value cannot be a number",
        defaultValue: { operator: "ilike", strings: 5 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "5",
        type: "text",
        label: "Default value cannot be a boolean",
        defaultValue: { operator: "ilike", strings: false },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "6",
        type: "text",
        label: "Default value cannot be an empty array",
        defaultValue: { operator: "ilike", strings: [] },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);
});

test("Default value of selection filter", () => {
    const model = new Model();
    let result = addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "selection",
        label: "Default value cannot be a string, should be an array",
        resModel: "res.currency",
        selectionField: "position",
        defaultValue: { operator: "in", selectionValues: "default value" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "2",
        type: "selection",
        label: "Default value is an array",
        resModel: "res.currency",
        selectionField: "position",
        defaultValue: { operator: "in", selectionValues: ["default value"] },
    });
    expect(result.isSuccessful).toBe(true);

    result = addGlobalFilterWithoutReload(model, {
        id: "3",
        type: "selection",
        label: "Default value is empty",
        resModel: "res.currency",
        selectionField: "position",
    });
    expect(result.isSuccessful).toBe(true);

    result = addGlobalFilterWithoutReload(model, {
        id: "4",
        type: "selection",
        label: "Default value cannot be a number",
        resModel: "res.currency",
        selectionField: "position",
        defaultValue: { operator: "in", selectionValues: 5 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "5",
        type: "selection",
        label: "Default value cannot be a boolean",
        resModel: "res.currency",
        selectionField: "position",
        defaultValue: { operator: "in", selectionValues: false },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);
});

test("Default value of numeric filter", () => {
    const model = new Model();
    let result = addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "numeric",
        label: "Default value cannot be a boolean, should be a number",
        defaultValue: { operator: "=", value: true },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "2",
        type: "numeric",
        label: "Default value cannot be a string, should be a number",
        defaultValue: { operator: "=", value: "default value" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "2",
        type: "numeric",
        label: "Default value cannot be a number inside a string, should be a number",
        defaultValue: { operator: "=", value: "5" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "3",
        type: "numeric",
        label: "Default value cannot be an empty string",
        defaultValue: { operator: "=", value: "" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "4",
        type: "numeric",
        label: "Default value is empty (undefined)",
    });
    expect(result.isSuccessful).toBe(true);
});

test("Default value of date filter", () => {
    const model = new Model();
    let result = addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "date",
        label: "Default value should be a string, but a known value",
        defaultValue: "default value",
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "2",
        type: "date",
        label: "Default value is empty",
    });
    expect(result.isSuccessful).toBe(true);

    result = addGlobalFilterWithoutReload(model, {
        id: "3",
        type: "date",
        label: "Default value cannot be a number",
        defaultValue: 5,
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "4",
        type: "date",
        label: "Default value cannot be a boolean",
        defaultValue: false,
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    for (const value of [
        ...Object.keys(RELATIVE_PERIODS),
        "this_year",
        "this_month",
        "this_quarter",
    ]) {
        result = addGlobalFilterWithoutReload(model, {
            id: `5-${value}`,
            type: "date",
            label: `Default value is a known value: ${value}`,
            defaultValue: value,
        });
        expect(result.isSuccessful).toBe(true);
    }
});

test("Default value of relation filter", () => {
    const model = new Model();
    let result = addGlobalFilterWithoutReload(model, {
        id: "1",
        type: "relation",
        label: "Default value cannot be a string expect 'current_user', should be an array",
        defaultValue: { operator: "in", ids: "default value" },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "2",
        type: "relation",
        label: "Default value is an array",
        defaultValue: { operator: "in", ids: [1, 2, 3] },
    });
    expect(result.isSuccessful).toBe(true);

    result = addGlobalFilterWithoutReload(model, {
        id: "3",
        type: "relation",
        label: "Default value is empty",
    });
    expect(result.isSuccessful).toBe(true);

    result = addGlobalFilterWithoutReload(model, {
        id: "4",
        type: "relation",
        label: "Default value cannot be a number",
        defaultValue: { operator: "in", ids: 5 },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "5",
        type: "relation",
        label: "Default value cannot be a boolean",
        defaultValue: { operator: "in", ids: false },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "6",
        type: "relation",
        label: "Default value can be current_user",
        defaultValue: { operator: "in", ids: "current_user" },
    });
    expect(result.isSuccessful).toBe(true);

    result = addGlobalFilterWithoutReload(model, {
        id: "7",
        type: "relation",
        label: "Default value cannot be an array with a string",
        defaultValue: { operator: "in", ids: ["1"] },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);

    result = addGlobalFilterWithoutReload(model, {
        id: "8",
        type: "relation",
        label: "Default value cannot be an empty array",
        defaultValue: { operator: "in", ids: [] },
    });
    expect(result.isSuccessful).toBe(false);
    expect(result.reasons).toEqual(["InvalidValueTypeCombination"]);
});

test("Default value of boolean filter", () => {
    const model = new Model();

    let result = addGlobalFilterWithoutReload(model, {
        id: "2",
        type: "boolean",
        label: "Default value is set",
        defaultValue: { operator: "set" },
    });
    expect(result.isSuccessful).toBe(true);

    result = addGlobalFilterWithoutReload(model, {
        id: "3",
        type: "boolean",
        label: "Default value is empty",
    });
    expect(result.isSuccessful).toBe(true);
});
