/** @odoo-module */

import { migrate, upgradeRevisions, ODOO_VERSION } from "@spreadsheet/o_spreadsheet/migration";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { buildViewLink } from "@spreadsheet/ir_ui_menu/odoo_menu_link_cell";

const { Model } = spreadsheet;
const { markdownLink } = spreadsheet.helpers;

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

QUnit.test("Pivot measures are correctly migrated", (assert) => {
    const data = {
        pivots: {
            1: {
                measures: [{ field: "foo" }, { field: "bar", operator: "max" }],
            },
        },
    };
    const migratedData = migrate(data);
    assert.deepEqual(migratedData.pivots["1"].measures, ["foo", "bar"]);
});

QUnit.test("Global filters: modelName is replaced by model", (assert) => {
    const data = {
        globalFilters: [
            {
                id: "1",
                modelName: "foo",
            },
        ],
    };
    const migratedData = migrate(data);
    const [f1] = migratedData.globalFilters;
    assert.strictEqual(f1.modelName, undefined);
    assert.strictEqual(f1.model, "foo");
});

QUnit.test("Migrate odoo chart definition", (assert) => {
    const data = {
        sheets: [
            {
                figures: [
                    {
                        id: "ID",
                        tag: "chart",
                        data: {
                            title: "Opportunities",
                            background: "#FFFFFF",
                            legendPosition: "top",
                            metaData: {
                                groupBy: ["stage_id", "country_id"],
                                measure: "__count",
                                order: "ASC",
                                resModel: "crm.lead",
                                stacked: true,
                            },
                            searchParams: {
                                comparison: null,
                                context: {},
                                domain: [],
                                groupBy: ["stage_id", "country_id"],
                                orderBy: [],
                            },
                            type: "odoo_bar",
                        },
                    },
                ],
            },
        ],
    };
    const migratedData = migrate(data);
    const figures = migratedData.sheets[0].figures;
    assert.strictEqual(figures.length, 1);
    const chart = figures[0];
    assert.strictEqual(chart.data.dataSourceDefinition.id, "ID");
    assert.strictEqual(chart.data.dataSourceDefinition.groupBy.length, 2);
    assert.strictEqual(chart.data.dataSourceDefinition.groupBy[0], "stage_id");
    assert.strictEqual(chart.data.dataSourceDefinition.groupBy[1], "country_id");
    assert.strictEqual(chart.data.dataSourceDefinition.measure, "__count");
    assert.deepEqual(chart.data.dataSourceDefinition.orderBy, { field: "__count", asc: true });
    assert.strictEqual(chart.data.dataSourceDefinition.stacked, true);
    assert.strictEqual(chart.data.dataSourceDefinition.model, "crm.lead");
    assert.strictEqual(chart.data.dataSourceDefinition.domain.length, 0);
    assert.strictEqual(chart.data.metaData, undefined);
    assert.strictEqual(chart.data.searchParams, undefined);
});

QUnit.test("view links: modelName is replaced by model", (assert) => {
    const content = markdownLink(
        "label",
        buildViewLink({
            name: "action name",
            viewType: "kanban",
            action: {
                domain: [],
                context: {},
                modelName: "res.partner",
                views: [],
            },
        })
    );
    const data = {
        sheets: [
            {
                cells: {
                    A1: { content },
                },
            },
        ],
    };
    const migratedData = migrate(data);
    const A1 = migratedData.sheets[0].cells.A1;
    assert.strictEqual(
        A1.content,
        markdownLink(
            "label",
            buildViewLink({
                name: "action name",
                viewType: "kanban",
                action: {
                    domain: [],
                    context: {},
                    views: [],
                    model: "res.partner",
                },
            })
        )
    );
});

QUnit.test("INSERT_PIVOT cmd metaData and searchParams", (assert) => {
    const revision = {
        type: "REMOTE_REVISION",
        commands: [
            {
                type: "INSERT_PIVOT",
                sheetId: "Sheet1",
                col: 0,
                row: 0,
                table: {
                    cols: [],
                    rows: [],
                    measures: ["debit_limit"],
                },
                id: "1",
                dataSourceId: "9ce3",
                definition: {
                    metaData: {
                        colGroupBys: ["country_id"],
                        rowGroupBys: ["parent_id"],
                        activeMeasures: ["debit_limit"],
                        resModel: "res.partner",
                        sortedColumn: {
                            groupId: [[], [48]],
                            measure: "debit_limit",
                            order: "asc",
                            originIndexes: [0],
                        },
                    },
                    searchParams: {
                        comparison: null,
                        context: { default_country_id: 99 },
                        domain: [["country_id", "in", [1, 2]]],
                        groupBy: [],
                        orderBy: [],
                    },
                    name: "Contact by Country",
                },
            },
        ],
    };
    upgradeRevisions([revision]);
    upgradeRevisions([revision]); // test idempotence
    assert.deepEqual(revision.commands, [
        {
            type: "INSERT_PIVOT",
            sheetId: "Sheet1",
            col: 0,
            row: 0,
            table: {
                cols: [],
                rows: [],
                measures: ["debit_limit"],
            },
            dataSourceId: "9ce3",
            definition: {
                id: "1",
                colGroupBys: ["country_id"],
                rowGroupBys: ["parent_id"],
                measures: ["debit_limit"],
                model: "res.partner",
                orderBy: { field: "debit_limit", asc: true, groupId: [[], [48]] },
                context: { default_country_id: 99 },
                domain: [["country_id", "in", [1, 2]]],
                name: "Contact by Country",
            },
        },
    ]);
});

QUnit.test("INSERT_ODOO_LIST cmd metaData and searchParams", (assert) => {
    const revision = {
        type: "REMOTE_REVISION",
        commands: [
            {
                type: "INSERT_ODOO_LIST",
                sheetId: "Sheet1",
                col: 0,
                row: 0,
                id: "1",
                definition: {
                    metaData: {
                        resModel: "res.partner",
                        columns: ["name", "email"],
                    },
                    searchParams: {
                        domain: ["&", ["name", "=", "Raoul"], ["user_id", "=", 2]],
                        context: { default_country_id: 99 },
                        orderBy: [{ name: "email", asc: true }],
                    },
                    name: "Contacts",
                },
                dataSourceId: "bfa8",
                linesNumber: 80,
                columns: [
                    { name: "name", type: "char" },
                    { name: "email", type: "char" },
                ],
            },
        ],
    };
    upgradeRevisions([revision]);
    upgradeRevisions([revision]); // test idempotence
    assert.deepEqual(revision.commands, [
        {
            type: "INSERT_ODOO_LIST",
            sheetId: "Sheet1",
            col: 0,
            row: 0,
            definition: {
                id: "1",
                model: "res.partner",
                columns: ["name", "email"],
                domain: ["&", ["name", "=", "Raoul"], ["user_id", "=", 2]],
                context: { default_country_id: 99 },
                orderBy: [{ field: "email", asc: true }],
                name: "Contacts",
            },
            dataSourceId: "bfa8",
            linesNumber: 80,
        },
    ]);
});

QUnit.test("CREATE_CHART cmd metaData and searchParams", (assert) => {
    const revision = {
        type: "REMOTE_REVISION",
        commands: [
            {
                type: "CREATE_CHART",
                sheetId: "Sheet1",
                id: "123",
                position: { x: 10, y: 10 },
                definition: {
                    metaData: {
                        groupBy: ["country_id"],
                        measure: "debit_limit",
                        order: "ASC",
                        resModel: "res.partner",
                    },
                    searchParams: {
                        comparison: null,
                        context: { default_country_id: 99 },
                        domain: [("country_id", "!=", false)],
                    },
                    stacked: true,
                    title: "Contact",
                    legendPosition: "top",
                    verticalAxisPosition: "left",
                    type: "odoo_line",
                    dataSourceId: "5688",
                    id: "123",
                },
            },
        ],
    };
    upgradeRevisions([revision]);
    upgradeRevisions([revision]); // test idempotence
    assert.deepEqual(revision.commands, [
        {
            type: "CREATE_CHART",
            sheetId: "Sheet1",
            id: "123",
            position: { x: 10, y: 10 },
            definition: {
                dataSourceDefinition: {
                    id: "123",
                    groupBy: ["country_id"],
                    measure: "debit_limit",
                    orderBy: { field: "debit_limit", asc: true },
                    model: "res.partner",
                    context: { default_country_id: 99 },
                    domain: [("country_id", "!=", false)],
                },
                stacked: true,
                title: "Contact",
                legendPosition: "top",
                verticalAxisPosition: "left",
                type: "odoo_line",
                dataSourceId: "5688",
                id: "123",
            },
        },
    ]);
});

QUnit.test("ADD_GLOBAL_FILTER, EDIT_GLOBAL_FILTER cmd metaData and searchParams", (assert) => {
    const revision = {
        type: "REMOTE_REVISION",
        commands: [
            {
                type: "ADD_GLOBAL_FILTER",
                id: "122",
                filter: {
                    id: "122",
                    type: "relation",
                    label: "country",
                    modelName: "res.country",
                },
                pivot: {},
                list: {},
                chart: {},
            },
            {
                type: "EDIT_GLOBAL_FILTER",
                id: "122",
                filter: {
                    id: "122",
                    type: "relation",
                    label: "country",
                    modelName: "res.country",
                },
                pivot: {},
                list: {},
                chart: {},
            },
        ],
    };
    upgradeRevisions([revision]);
    upgradeRevisions([revision]); // test idempotence
    assert.deepEqual(revision.commands, [
        {
            type: "ADD_GLOBAL_FILTER",
            id: "122",
            filter: {
                id: "122",
                type: "relation",
                label: "country",
                model: "res.country",
            },
            pivot: {},
            list: {},
            chart: {},
        },
        {
            type: "EDIT_GLOBAL_FILTER",
            id: "122",
            filter: {
                id: "122",
                type: "relation",
                label: "country",
                model: "res.country",
            },
            pivot: {},
            list: {},
            chart: {},
        },
    ]);
});

QUnit.test("UPDATE_CELL view link modelName", (assert) => {
    const revision = {
        type: "REMOTE_REVISION",
        commands: [
            {
                type: "UPDATE_CELL",
                sheetId: "Sheet1",
                col: 0,
                row: 0,
                content: markdownLink(
                    "label",
                    buildViewLink({
                        name: "action name",
                        viewType: "kanban",
                        action: {
                            domain: [],
                            context: {},
                            modelName: "res.partner",
                            views: [],
                        },
                    })
                ),
            },
        ],
    };
    upgradeRevisions([revision]);
    upgradeRevisions([revision]); // test idempotence
    assert.deepEqual(revision.commands, [
        {
            type: "UPDATE_CELL",
            sheetId: "Sheet1",
            col: 0,
            row: 0,
            content: markdownLink(
                "label",
                buildViewLink({
                    name: "action name",
                    viewType: "kanban",
                    action: {
                        domain: [],
                        context: {},
                        views: [],
                        model: "res.partner",
                    },
                })
            ),
        },
    ]);
});
