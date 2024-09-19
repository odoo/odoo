import { describe, expect, test } from "@odoo/hoot";
import { ODOO_VERSION } from "@spreadsheet/o_spreadsheet/migration";
import { Model, load } from "@odoo/o-spreadsheet";
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
    expect(f1.defaultValue).toEqual({ yearOffset: -1 });
    expect(f2.defaultValue).toEqual({ yearOffset: -2 });
    expect(f3.defaultValue).toEqual({ yearOffset: 0 });
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
    expect(migratedData.sheets[0].figures[0].data.fieldMatching).toEqual({
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
    expect(migratedData.sheets[0].figures[0].data.fieldMatching).toEqual({
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
            defaultValue: [2],
            defaultValueDisplayNames: ["Mitchell Admin"],
            modelName: "res.users",
        },
        {
            id: "2",
            type: "date",
            label: "a year relational filter",
            rangeType: "fixedPeriod",
            defaultValue: "this_year",
        },
        {
            id: "3",
            type: "date",
            label: "a quarter relational filter",
            rangeType: "fixedPeriod",
            defaultValue: "this_quarter",
        },
        {
            id: "4",
            type: "date",
            label: "a month relational filter",
            rangeType: "fixedPeriod",
            defaultValue: "this_month",
        },
        {
            id: "5",
            type: "date",
            label: "a relative date filter",
            rangeType: "relative",
            defaultValue: "last_week",
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
                measures: [],
            },
            2: {
                name: "test2",
                sortedColumn: { groupId: [[], [1]], measure: "testMeasure", order: "desc" },
                columns: [{ fieldName: "product_id" }],
                rows: [],
                measures: [],
            },
        },
    };
    const migratedData = load(data);
    expect(migratedData.pivots["1"].sortedColumn).toEqual({
        domain: [],
        measure: "testMeasure",
        order: "desc",
    });
    expect(migratedData.pivots["2"].sortedColumn).toBe(undefined);
});

test("Odoo version is exported", () => {
    const model = new Model();
    expect(model.exportData().odooVersion).toBe(ODOO_VERSION);
});
