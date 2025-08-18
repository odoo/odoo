import { describe, expect, test } from "@odoo/hoot";
import { load } from "@odoo/o-spreadsheet";
import { defineSpreadsheetActions, defineSpreadsheetModels } from "../helpers/data";

defineSpreadsheetModels();
defineSpreadsheetActions();

describe.current.tags("headless");

test("Odoo formulas are migrated", () => {
    const data = {
        version: 16,
        sheets: [
            {
                cells: {
                    A1: { content: `=PIVOT("1")` },
                    A2: { content: `=PIVOT.HEADER("1")` },
                    A3: { content: `=FILTER.VALUE("1")` },
                    A4: { content: `=LIST("1")` },
                    A5: { content: `=LIST.HEADER("1")` },
                    A6: { content: `=PIVOT.POSITION("1")` },
                    A7: { content: `=pivot("1")` },
                },
            },
        ],
    };
    const migratedData = load(data);
    expect(migratedData.sheets[0].cells.A1).toBe(`=PIVOT.VALUE("1")`);
    expect(migratedData.sheets[0].cells.A2).toBe(`=PIVOT.HEADER("1")`);
    expect(migratedData.sheets[0].cells.A3).toBe(`=ODOO.FILTER.VALUE("1")`);
    expect(migratedData.sheets[0].cells.A4).toBe(`=ODOO.LIST("1")`);
    expect(migratedData.sheets[0].cells.A5).toBe(`=ODOO.LIST.HEADER("1")`);
    expect(migratedData.sheets[0].cells.A6).toBe(`=ODOO.PIVOT.POSITION("1")`);
    expect(migratedData.sheets[0].cells.A7).toBe(`=PIVOT.VALUE("1")`);
});

test("Pivot 'day' arguments are migrated", () => {
    const data = {
        version: 16,
        odooVersion: 1,
        sheets: [
            {
                cells: {
                    A1: { content: `=ODOO.PIVOT("1","21/07/2022")` },
                    A2: { content: `=ODOO.PIVOT.HEADER("1","11/12/2022")` },
                    A3: { content: `=odoo.pivot("1","21/07/2021")` },
                    A4: { content: `=ODOO.PIVOT("1","test")` },
                    A5: { content: `=odoo.pivot("1","21/07/2021")+"21/07/2021"` },
                    A6: { content: `=BAD_FORMULA(` },
                },
            },
        ],
    };
    const migratedData = load(data);
    expect(migratedData.sheets[0].cells.A1).toBe(`=PIVOT.VALUE("1","07/21/2022")`);
    expect(migratedData.sheets[0].cells.A2).toBe(`=PIVOT.HEADER("1","12/11/2022")`);
    expect(migratedData.sheets[0].cells.A3).toBe(`=PIVOT.VALUE("1","07/21/2021")`);
    expect(migratedData.sheets[0].cells.A4).toBe(`=PIVOT.VALUE("1","test")`);
    expect(migratedData.sheets[0].cells.A5).toBe(`=PIVOT.VALUE("1","07/21/2021")+"21/07/2021"`);
    expect(migratedData.sheets[0].cells.A6).toBe(`=BAD_FORMULA(`);
});

test("Global filters: pivot fields is correctly added", () => {
    const data = {
        version: 16,
        globalFilters: [
            {
                id: "Filter1",
                type: "relation",
                label: "Relation Filter",
                fields: {
                    1: {
                        field: "foo",
                        type: "char",
                    },
                },
            },
        ],
        pivots: {
            1: {
                name: "test",
                measures: [],
                colGroupBys: [],
                rowGroupBys: [],
            },
        },
    };
    const migratedData = load(data);
    const filter = migratedData.globalFilters[0];
    const pivot = migratedData.pivots["1"];
    expect(pivot.fieldMatching).toEqual({
        Filter1: {
            chain: "foo",
            type: "char",
        },
    });
    expect(filter.fields).toBe(undefined);
});

test("Global filters: date is correctly migrated", () => {
    const data = {
        version: 16,
        globalFilters: [
            {
                id: "1",
                type: "date",
                rangeType: "year",
                defaultValue: { year: "last_year" },
            },
            {
                id: "2",
                type: "date",
                rangeType: "year",
                defaultValue: { year: "antepenultimate_year" },
            },
            {
                id: "3",
                type: "date",
                rangeType: "year",
                defaultValue: { year: "this_year" },
            },
        ],
    };
    const migratedData = load(data);
    const [f1, f2, f3] = migratedData.globalFilters;
    expect(f1.defaultValue).toBe(undefined);
    expect(f2.defaultValue).toBe(undefined);
    expect(f3.defaultValue).toBe(undefined);
});

test("List name default is model name", () => {
    const data = {
        version: 16,
        lists: {
            1: {
                name: "Name",
                model: "Model",
            },
            2: {
                model: "Model",
            },
        },
    };
    const migratedData = load(data);
    expect(Object.values(migratedData.lists).length).toBe(2);
    expect(migratedData.lists["1"].name).toBe("Name");
    expect(migratedData.lists["2"].name).toBe("Model");
});

test("Pivot name default is model name", () => {
    const data = {
        version: 16,
        pivots: {
            1: {
                name: "Name",
                model: "Model",
                measures: [],
                colGroupBys: [],
                rowGroupBys: [],
            },
            2: {
                model: "Model",
                measures: [],
                colGroupBys: [],
                rowGroupBys: [],
            },
        },
    };
    const migratedData = load(data);
    expect(Object.values(migratedData.pivots).length).toBe(2);
    expect(migratedData.pivots["1"].name).toBe("Name");
    expect(migratedData.pivots["2"].name).toBe("Model");
});

test("fieldMatchings are moved from filters to their respective datasources", () => {
    const data = {
        version: 16,
        globalFilters: [
            {
                id: "Filter",
                label: "MyFilter1",
                type: "relation",
                listFields: {
                    1: {
                        field: "parent_id",
                        type: "many2one",
                    },
                },
                pivotFields: {
                    1: {
                        field: "parent_id",
                        type: "many2one",
                    },
                },
                graphFields: {
                    fig1: {
                        field: "parent_id",
                        type: "many2one",
                    },
                },
            },
        ],
        pivots: {
            1: {
                name: "Name",
                measures: [],
                colGroupBys: [],
                rowGroupBys: [],
            },
        },
        lists: {
            1: {
                name: "Name",
            },
        },
        sheets: [
            {
                figures: [
                    {
                        id: "fig1",
                        tag: "chart",
                        data: {
                            type: "odoo_bar",
                            metaData: {},
                        },
                    },
                ],
            },
        ],
    };
    const migratedData = load(data);
    expect(migratedData.pivots["1"].fieldMatching).toEqual({
        Filter: { chain: "parent_id", type: "many2one" },
    });
    expect(migratedData.lists["1"].fieldMatching).toEqual({
        Filter: { chain: "parent_id", type: "many2one" },
    });
    expect(Object.values(migratedData.sheets[0].charts)[0].chart.fieldMatching).toEqual({
        Filter: { chain: "parent_id", type: "many2one" },
    });
});

test("fieldMatchings offsets are correctly preserved after migration", () => {
    const data = {
        version: 16,
        globalFilters: [
            {
                id: "Filter",
                label: "MyFilter1",
                type: "relation",
                listFields: {
                    1: {
                        field: "parent_id",
                        type: "date",
                        offset: "-1",
                    },
                },
                pivotFields: {
                    1: {
                        field: "parent_id",
                        type: "date",
                        offset: "-1",
                    },
                },
                graphFields: {
                    fig1: {
                        field: "parent_id",
                        type: "date",
                        offset: "-1",
                    },
                },
            },
        ],
        pivots: {
            1: {
                name: "Name",
                measures: [],
                colGroupBys: [],
                rowGroupBys: [],
            },
        },
        lists: {
            1: {
                name: "Name",
            },
        },
        sheets: [
            {
                figures: [
                    {
                        id: "fig1",
                        tag: "chart",
                        data: {
                            type: "odoo_bar",
                            metaData: {},
                        },
                    },
                ],
            },
        ],
    };
    const migratedData = load(data);
    expect(migratedData.pivots["1"].fieldMatching).toEqual({
        Filter: { chain: "parent_id", type: "date", offset: "-1" },
    });
    expect(migratedData.lists["1"].fieldMatching).toEqual({
        Filter: { chain: "parent_id", type: "date", offset: "-1" },
    });
    expect(Object.values(migratedData.sheets[0].charts)[0].chart.fieldMatching).toEqual({
        Filter: { chain: "parent_id", type: "date", offset: "-1" },
    });
});

test("group year/quarter/month filters to a single filter type", () => {
    const data = {
        version: 14,
        odooVersion: 5,
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "a relational filter",
                defaultValue: [2],
                defaultValueDisplayNames: ["Mitchell Admin"],
                modelName: "res.users",
            },
            {
                id: "2",
                type: "date",
                label: "a year relational filter",
                rangeType: "year",
                defaultsToCurrentPeriod: true,
            },
            {
                id: "3",
                type: "date",
                label: "a quarter relational filter",
                rangeType: "quarter",
                defaultsToCurrentPeriod: true,
            },
            {
                id: "4",
                type: "date",
                label: "a month relational filter",
                rangeType: "month",
                defaultsToCurrentPeriod: true,
            },
            {
                id: "5",
                type: "date",
                label: "a relative date filter",
                defaultValue: "last_week",
                rangeType: "relative",
                defaultsToCurrentPeriod: false,
            },
        ],
    };
    const migratedData = load(data);
    const filters = migratedData.globalFilters;
    expect(filters).toEqual([
        {
            id: "1",
            type: "relation",
            label: "a relational filter",
            defaultValue: { operator: "in", ids: [2] },
            defaultValueDisplayNames: ["Mitchell Admin"],
            modelName: "res.users",
        },
        {
            id: "2",
            type: "date",
            label: "a year relational filter",
            defaultValue: "this_year",
        },
        {
            id: "3",
            type: "date",
            label: "a quarter relational filter",
            defaultValue: "this_quarter",
        },
        {
            id: "4",
            type: "date",
            label: "a month relational filter",
            defaultValue: "this_month",
        },
        {
            id: "5",
            type: "date",
            label: "a relative date filter",
            defaultValue: "last_7_days",
        },
    ]);
});

test("Pivot are migrated from 6 to 9", () => {
    const data = {
        version: 16,
        pivots: {
            1: {
                name: "Name",
                model: "Model",
                measures: [],
                colGroupBys: [],
                rowGroupBys: [],
                fieldMatching: { 1: { chain: "foo", type: "char" } },
            },
        },
    };
    const migratedData = load(data);
    expect(Object.values(migratedData.pivots).length).toBe(1);
    expect(migratedData.pivots["1"]).toEqual({
        type: "ODOO",
        fieldMatching: { 1: { chain: "foo", type: "char" } },
        name: "Name",
        model: "Model",
        measures: [],
        columns: [],
        rows: [],
        formulaId: "1",
    });
});

test("Pivot are migrated from 9 to 10", () => {
    const data = {
        version: 16,
        odooVersion: 9,
        pivots: {
            1: {
                type: "ODOO",
                name: "Name",
                model: "res.model",
                measures: ["probability"],
                colGroupBys: ["foo"],
                rowGroupBys: ["create_date:month"],
                formulaId: "1",
            },
        },
    };
    const migratedData = load(data);
    expect(Object.values(migratedData.pivots).length).toBe(1);
    expect(migratedData.pivots["1"]).toEqual({
        type: "ODOO",
        name: "Name",
        model: "res.model",
        measures: [{ id: "probability", fieldName: "probability", aggregator: undefined }],
        columns: [{ fieldName: "foo", granularity: undefined, order: undefined }],
        rows: [{ fieldName: "create_date", granularity: "month", order: undefined }],
        formulaId: "1",
    });
});

test("Pivot formulas are migrated from 9 to 10", () => {
    const data = {
        version: 16,
        odooVersion: 9,
        sheets: [
            {
                cells: {
                    A1: { content: `=ODOO.PIVOT("1")` },
                    A2: { content: `=ODOO.PIVOT.HEADER("1")` },
                    A3: { content: `=ODOO.PIVOT.POSITION("1")` },
                    A4: { content: `=ODOO.PIVOT.TABLE("1")` },
                    A5: { content: `=odoo.pivot("1")` },
                },
            },
        ],
    };
    const migratedData = load(data);
    expect(migratedData.sheets[0].cells.A1).toBe(`=PIVOT.VALUE("1")`);
    expect(migratedData.sheets[0].cells.A2).toBe(`=PIVOT.HEADER("1")`);
    expect(migratedData.sheets[0].cells.A3).toBe(`=ODOO.PIVOT.POSITION("1")`);
    expect(migratedData.sheets[0].cells.A4).toBe(`=PIVOT("1")`);
    expect(migratedData.sheets[0].cells.A5).toBe(`=PIVOT.VALUE("1")`);
});

test("Pivot formulas using pivot positions are migrated (11 to 12)", () => {
    const data = {
        version: 16,
        odooVersion: 9,
        sheets: [
            {
                cells: {
                    A1: {
                        content: `=-PIVOT.VALUE("1","balance","account_id",ODOO.PIVOT.POSITION("1","account_id",12),"date:quarter","4/"&ODOO.FILTER.VALUE("Year"))`,
                    },
                    A2: {
                        content: `=PIVOT.HEADER("1","account_id",ODOO.PIVOT.POSITION("1","account_id",14))`,
                    },
                    A3: { content: `=ODOO.PIVOT.POSITION("1","account_id",14)` },
                    A4: { content: `=ODOO.PIVOT.POSITION("1",14)` },
                },
            },
        ],
    };
    const migratedData = load(data);
    expect(migratedData.sheets[0].cells.A1).toBe(
        `=-PIVOT.VALUE("1","balance","#account_id",12,"date:quarter","4/"&ODOO.FILTER.VALUE("Year"))`
    );
    expect(migratedData.sheets[0].cells.A2).toBe(`=PIVOT.HEADER("1","#account_id",14)`);
    expect(migratedData.sheets[0].cells.A3).toBe(`=ODOO.PIVOT.POSITION("1","account_id",14)`);
    expect(migratedData.sheets[0].cells.A4).toBe(`=ODOO.PIVOT.POSITION("1",14)`);
});

test("Pivot sorted columns are migrated (12 to 13)", () => {
    const data = {
        version: 23,
        odooVersion: 12,
        sheets: [],
        pivots: {
            1: {
                name: "test",
                sortedColumn: { groupId: [[], []], measure: "testMeasure", order: "desc" },
                columns: [],
                rows: [],
                measures: [{ id: "testMeasure:sum", fieldName: "testMeasure", aggregator: "sum" }],
            },
            2: {
                name: "test2",
                sortedColumn: { groupId: [[], [1]], measure: "testMeasure", order: "desc" },
                columns: [{ fieldName: "product_id" }],
                rows: [],
                measures: [{ id: "testMeasure:sum", fieldName: "testMeasure", aggregator: "sum" }],
            },
            3: {
                name: "test",
                // sortedColumn is not in the measures
                sortedColumn: { groupId: [[], []], measure: "testMeasure", order: "desc" },
                columns: [],
                rows: [],
                measures: [],
            },
        },
    };
    const migratedData = load(data);
    expect(migratedData.pivots["1"].sortedColumn).toEqual({
        domain: [],
        measure: "testMeasure:sum",
        order: "desc",
    });
    expect(migratedData.pivots["2"].sortedColumn).toBe(undefined);
    expect(migratedData.pivots["3"].sortedColumn).toBe(undefined);
});

test("Chart cumulatedStart is set to true if cumulative at migration", () => {
    const data = {
        version: 18.0,
        odooVersion: 9,
        sheets: [
            {
                figures: [
                    {
                        id: "fig1",
                        tag: "chart",
                        data: {
                            type: "odoo_bar",
                            metaData: {
                                cumulatedStart: undefined,
                                cumulative: true,
                            },
                            cumulative: true,
                        },
                    },
                    {
                        id: "fig2",
                        tag: "chart",
                        data: {
                            type: "odoo_bar",
                            metaData: {
                                cumulative: false,
                            },
                            cumulative: false,
                        },
                    },
                    {
                        id: "fig3",
                        tag: "chart",
                        data: {
                            type: "odoo_bar",
                            metaData: {
                                cumulative: true,
                                cumulatedStart: false,
                            },
                            cumulative: true,
                            cumulatedStart: false,
                        },
                    },
                ],
            },
        ],
    };
    const migratedData = load(data);
    const sheet = migratedData.sheets[0];

    const chartData1 = Object.values(sheet.charts)[0].chart;
    expect(chartData1.metaData.cumulatedStart).toBe(true);
    expect(chartData1.cumulatedStart).toBe(true);

    const chartData2 = Object.values(sheet.charts)[1].chart;
    expect(chartData2.metaData.cumulatedStart).toBe(false);
    expect(chartData2.cumulatedStart).toBe(false);

    const chartData3 = Object.values(sheet.charts)[2].chart;
    expect(chartData3.metaData.cumulatedStart).toBe(false);
    expect(chartData3.cumulatedStart).toBe(false);
});

test("text global filter default value is now an array of strings", () => {
    const data = {
        version: "18.3.0",
        globalFilters: [
            {
                id: "1",
                type: "text",
                defaultValue: "foo",
                rangeOfAllowedValues: "Sheet1!A1:A2",
            },
            {
                id: "2",
                type: "text",
            },
            {
                id: "3",
                type: "text",
                defaultValue: "",
            },
        ],
    };
    const migratedData = load(data);
    expect(migratedData.globalFilters[0].defaultValue).toEqual({
        operator: "ilike",
        strings: ["foo"],
    });
    expect(migratedData.globalFilters[0].rangeOfAllowedValues).toBe(undefined);
    expect(migratedData.globalFilters[0].rangesOfAllowedValues).toEqual(["Sheet1!A1:A2"]);
    expect(migratedData.globalFilters[1].defaultValue).toBe(undefined);
    expect(migratedData.globalFilters[1].rangeOfAllowedValues).toBe(undefined);
    expect(migratedData.globalFilters[1].rangesOfAllowedValues).toBe(undefined);
    expect(migratedData.globalFilters[2].defaultValue).toBe(undefined);
});

test("global filter default value have operators", () => {
    const data = {
        version: "18.4.14",
        globalFilters: [
            {
                id: "1",
                type: "text",
                defaultValue: ["foo"],
            },
            {
                id: "2",
                type: "relation",
                modelName: "res.partner",
                defaultValue: [1],
            },
            {
                id: "3",
                type: "relation",
                modelName: "res.company",
                defaultValue: [2],
                includeChildren: true,
            },
            {
                id: "4",
                type: "boolean",
                defaultValue: [true],
            },
            {
                id: "5",
                type: "boolean",
                defaultValue: [false],
            },
            {
                id: "6",
                type: "boolean",
                defaultValue: [true, false],
            },
        ],
    };
    const migratedData = load(data);
    expect(migratedData.globalFilters[0].defaultValue).toEqual({
        operator: "ilike",
        strings: ["foo"],
    });
    expect(migratedData.globalFilters[1].defaultValue).toEqual({
        operator: "in",
        ids: [1],
    });
    expect(migratedData.globalFilters[2].defaultValue).toEqual({
        operator: "child_of",
        ids: [2],
    });
    expect(migratedData.globalFilters[3].defaultValue).toEqual({ operator: "set" });
    expect(migratedData.globalFilters[4].defaultValue).toEqual({ operator: "not set" });
    expect(migratedData.globalFilters[5].defaultValue).toBe(undefined);
});

test("Date with antepenultimate_year is not supported anymore", () => {
    const data = {
        version: "1",
        globalFilters: [
            {
                id: "1",
                type: "date",
                defaultValue: { year: "antepenultimate_year" },
                rangeType: "fixedPeriod",
            },
        ],
    };
    const migratedData = load(data);
    expect(migratedData.globalFilters[0].defaultValue).toBe(undefined);
});

test("Default value is now undefined", () => {
    const data = {
        version: "1",
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "a relation filter",
                defaultValue: [],
            },
        ],
    };
    const migratedData = load(data);
    expect(migratedData.globalFilters[0].defaultValue).toBe(undefined);
});

test("period values are correctly renamed/removed", () => {
    const data = {
        version: 14,
        odooVersion: 5,
        globalFilters: [
            {
                id: "1",
                type: "date",
                label: "My label",
                rangeType: "relative",
                defaultValue: "last_six_month",
            },
            {
                id: "2",
                type: "date",
                label: "My label",
                rangeType: "relative",
                defaultValue: "last_three_years",
            },
            {
                id: "3",
                type: "date",
                label: "My label",
                rangeType: "relative",
                defaultValue: "last_month",
            },
            {
                id: "4",
                type: "date",
                label: "My label",
                rangeType: "relative",
                defaultValue: "last_week",
            },
            {
                id: "5",
                type: "date",
                label: "My label",
                rangeType: "relative",
                defaultValue: "last_three_months",
            },
            {
                id: "6",
                type: "date",
                label: "My label",
                rangeType: "relative",
                defaultValue: "last_year",
            },
        ],
    };
    const migratedData = load(data);
    const filters = migratedData.globalFilters;
    expect(filters[0].defaultValue).toBe(undefined);
    expect(filters[1].defaultValue).toBe(undefined);
    expect(filters[2].defaultValue).toBe("last_30_days");
    expect(filters[3].defaultValue).toBe("last_7_days");
    expect(filters[4].defaultValue).toBe("last_90_days");
    expect(filters[5].defaultValue).toBe("last_12_months");
});

test("Date filters are migrated", () => {
    const data = {
        version: 14,
        odooVersion: 5,
        globalFilters: [
            {
                id: "1",
                type: "date",
                label: "Fixed Period",
                rangeType: "fixedPeriod",
                disabledPeriods: ["quarter"],
            },
            {
                id: "2",
                type: "date",
                label: "Relative",
                rangeType: "relative",
            },
            {
                id: "3",
                type: "date",
                label: "From/to",
                rangeType: "fromTo",
            },
        ],
    };
    const migratedData = load(data);
    const filters = migratedData.globalFilters;
    expect(filters[0].rangeType).toBe(undefined);
    expect(filters[1].rangeType).toBe(undefined);
    expect(filters[2].rangeType).toBe(undefined);

    expect(filters[0].disabledPeriods).toBe(undefined);
});
