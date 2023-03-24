/** @odoo-module */

import { migrate, ODOO_VERSION } from "@spreadsheet/o_spreadsheet/migration";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

const { Model } = spreadsheet;

QUnit.module("spreadsheet > migrations");

QUnit.test("Odoo formulas are migrated", (assert) => {
    const data = {
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
    const migratedData = migrate(data);
    assert.strictEqual(migratedData.sheets[0].cells.A1.content, `=ODOO.PIVOT("1")`);
    assert.strictEqual(migratedData.sheets[0].cells.A2.content, `=ODOO.PIVOT.HEADER("1")`);
    assert.strictEqual(migratedData.sheets[0].cells.A3.content, `=ODOO.FILTER.VALUE("1")`);
    assert.strictEqual(migratedData.sheets[0].cells.A4.content, `=ODOO.LIST("1")`);
    assert.strictEqual(migratedData.sheets[0].cells.A5.content, `=ODOO.LIST.HEADER("1")`);
    assert.strictEqual(migratedData.sheets[0].cells.A6.content, `=ODOO.PIVOT.POSITION("1")`);
    assert.strictEqual(migratedData.sheets[0].cells.A7.content, `=ODOO.PIVOT("1")`);
});

QUnit.test("Pivot 'day' arguments are migrated", (assert) => {
    const data = {
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
    const migratedData = migrate(data);
    assert.strictEqual(migratedData.sheets[0].cells.A1.content, `=ODOO.PIVOT("1","07/21/2022")`);
    assert.strictEqual(
        migratedData.sheets[0].cells.A2.content,
        `=ODOO.PIVOT.HEADER("1","12/11/2022")`
    );
    assert.strictEqual(migratedData.sheets[0].cells.A3.content, `=odoo.pivot("1","07/21/2021")`);
    assert.strictEqual(migratedData.sheets[0].cells.A4.content, `=ODOO.PIVOT("1","test")`);
    assert.strictEqual(
        migratedData.sheets[0].cells.A5.content,
        `=odoo.pivot("1","07/21/2021")+"21/07/2021"`
    );
    assert.strictEqual(migratedData.sheets[0].cells.A6.content, `=BAD_FORMULA(`);
});

QUnit.test("Global filters: pivot fields is correctly added", (assert) => {
    const data = {
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
            },
        },
    };
    const migratedData = migrate(data);
    const filter = migratedData.globalFilters[0];
    const pivot = migratedData.pivots["1"];
    assert.deepEqual(pivot.fieldMatching, {
        Filter1: {
            chain: "foo",
            type: "char",
        },
    });
    assert.strictEqual(filter.fields, undefined);
});

QUnit.test("Global filters: date is correctly migrated", (assert) => {
    const data = {
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
    const migratedData = migrate(data);
    const [f1, f2, f3] = migratedData.globalFilters;
    assert.deepEqual(f1.defaultValue, { yearOffset: -1 });
    assert.deepEqual(f2.defaultValue, { yearOffset: -2 });
    assert.deepEqual(f3.defaultValue, { yearOffset: 0 });
});

QUnit.test("List name default is model name", (assert) => {
    const data = {
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
    const migratedData = migrate(data);
    assert.strictEqual(Object.values(migratedData.lists).length, 2);
    assert.strictEqual(migratedData.lists["1"].name, "Name");
    assert.strictEqual(migratedData.lists["2"].name, "Model");
});

QUnit.test("Pivot name default is model name", (assert) => {
    const data = {
        pivots: {
            1: {
                name: "Name",
                model: "Model",
            },
            2: {
                model: "Model",
            },
        },
    };
    const migratedData = migrate(data);
    assert.strictEqual(Object.values(migratedData.pivots).length, 2);
    assert.strictEqual(migratedData.pivots["1"].name, "Name");
    assert.strictEqual(migratedData.pivots["2"].name, "Model");
});

QUnit.test("fieldMatchings are moved from filters to their respective datasources", (assert) => {
    const data = {
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
    const migratedData = migrate(data);
    assert.deepEqual(migratedData.pivots["1"].fieldMatching, {
        Filter: { chain: "parent_id", type: "many2one" },
    });
    assert.deepEqual(migratedData.lists["1"].fieldMatching, {
        Filter: { chain: "parent_id", type: "many2one" },
    });
    assert.deepEqual(migratedData.sheets[0].figures[0].data.fieldMatching, {
        Filter: { chain: "parent_id", type: "many2one" },
    });
});

QUnit.test("fieldMatchings offsets are correctly preserved after migration", (assert) => {
    const data = {
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
    const migratedData = migrate(data);
    assert.deepEqual(migratedData.pivots["1"].fieldMatching, {
        Filter: { chain: "parent_id", type: "date", offset: "-1" },
    });
    assert.deepEqual(migratedData.lists["1"].fieldMatching, {
        Filter: { chain: "parent_id", type: "date", offset: "-1" },
    });
    assert.deepEqual(migratedData.sheets[0].figures[0].data.fieldMatching, {
        Filter: { chain: "parent_id", type: "date", offset: "-1" },
    });
});

QUnit.test("Odoo version is exported", (assert) => {
    const model = new Model();
    assert.strictEqual(model.exportData().odooVersion, ODOO_VERSION);
});
