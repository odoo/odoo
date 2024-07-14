/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";

import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { getCellContent, getCellFormula, getCellValue } from "@spreadsheet/../tests/utils/getters";
import { setupCollaborativeEnv } from "../../utils/collaborative_helpers";
import { PivotDataSource } from "@spreadsheet/pivot/pivot_data_source";
import { waitForDataSourcesLoaded } from "@spreadsheet/../tests/utils/model";

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

/**
 * Get a pivot definition, a data source and a pivot model (already loaded)
 */
async function getPivotReady(model, pivotId) {
    const definition = {
        metaData: {
            colGroupBys: ["foo"],
            rowGroupBys: ["bar"],
            activeMeasures: ["probability"],
            resModel: "partner",
        },
        searchParams: {
            domain: [],
            context: {},
            groupBy: [],
            orderBy: [],
        },
        name: "Partner",
    };
    const dataSourceId = model.getters.getPivotDataSourceId(pivotId);
    const dataSource = model.config.custom.dataSources.add(
        dataSourceId,
        PivotDataSource,
        definition
    );
    await dataSource.load();
    return { definition, dataSource };
}

/**
 * Insert a given pivot
 * @param {Model} model
 * @param {Object} params
 * @param {Object} params.definition Pivot definition
 * @param {PivotDataSource} params.dataSource Pivot data source (ready)
 * @param {string} [params.dataSourceId]
 * @param {[number, number]} [params.anchor]
 */
function insertPreloadedPivot(model, params) {
    const { definition, dataSource } = params;
    const structure = dataSource.getTableStructure();
    const sheetId = model.getters.getActiveSheetId();
    const { cols, rows, measures } = structure.export();
    const table = {
        cols,
        rows,
        measures,
    };
    model.dispatch("INSERT_PIVOT", {
        sheetId,
        col: params.anchor ? params.anchor[0] : 0,
        row: params.anchor ? params.anchor[1] : 0,
        table,
        id: params.pivotId,
        definition,
    });
    const columns = [];
    for (let col = 0; col <= table.cols[table.cols.length - 1].length; col++) {
        columns.push(col);
    }
    model.dispatch("AUTORESIZE_COLUMNS", { sheetId, cols: columns });
}

/**
 * Add a basic pivot in the current spreadsheet of model
 * @param {Model} model
 */
export async function insertPivot(model) {
    const { definition, dataSource } = await getPivotReady(model, "1");
    insertPreloadedPivot(model, {
        definition,
        dataSource,
        pivotId: "1",
    });
    await waitForDataSourcesLoaded(model);
}

let alice, bob, charlie, network;

QUnit.module("spreadsheet_edition > Pivot collaborative", {
    async beforeEach() {
        const env = await setupCollaborativeEnv(getBasicServerData());
        alice = env.alice;
        bob = env.bob;
        charlie = env.charlie;
        network = env.network;
    },
});

QUnit.test("Rename a pivot", async (assert) => {
    assert.expect(1);
    await insertPivot(alice);
    alice.dispatch("RENAME_ODOO_PIVOT", { pivotId: 1, name: "Test" });
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => user.getters.getPivotName(1),
        "Test"
    );
});

QUnit.test("Add a pivot", async (assert) => {
    assert.expect(7);
    await insertPivot(alice);
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => user.getters.getPivotIds().length,
        1
    );
    const cellFormulas = {
        B1: `=ODOO.PIVOT.HEADER(1,"foo",1)`, // header col
        A3: `=ODOO.PIVOT.HEADER(1,"bar","false")`, // header row
        B2: `=ODOO.PIVOT.HEADER(1,"foo",1,"measure","probability")`, // measure
        B3: `=ODOO.PIVOT(1,"probability","bar","false","foo",1)`, // value
        F1: `=ODOO.PIVOT.HEADER(1)`, // total header rows
        A5: `=ODOO.PIVOT.HEADER(1)`, // total header cols
    };
    for (const [cellXc, formula] of Object.entries(cellFormulas)) {
        assert.spreadsheetIsSynchronized(
            [alice, bob, charlie],
            (user) => getCellContent(user, cellXc),
            formula
        );
    }
});

QUnit.test("Add two pivots concurrently", async (assert) => {
    assert.expect(6);
    const { definition: def1, dataSource: ds1 } = await getPivotReady(alice, "1");
    const { definition: def2, dataSource: ds2 } = await getPivotReady(bob, "1");
    await network.concurrent(() => {
        insertPreloadedPivot(alice, {
            definition: def1,
            dataSource: ds1,
            pivotId: "1",
        });
        insertPreloadedPivot(bob, {
            definition: def2,
            dataSource: ds2,
            anchor: [0, 25],
            pivotId: "1",
        });
    });
    assert.spreadsheetIsSynchronized([alice, bob, charlie], (user) => user.getters.getPivotIds(), [
        "1",
        "2",
    ]);
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => getCellFormula(user, "B1"),
        `=ODOO.PIVOT.HEADER(1,"foo",1)`
    );
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => getCellFormula(user, "B26"),
        `=ODOO.PIVOT.HEADER(2,"foo",1)`
    );
    await waitForDataSourcesLoaded(alice);
    await waitForDataSourcesLoaded(bob);
    await waitForDataSourcesLoaded(charlie);

    assert.spreadsheetIsSynchronized([alice, bob, charlie], (user) => getCellValue(user, "B4"), 11);
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => getCellValue(user, "B29"),
        11
    );
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) =>
            Object.values(user.config.custom.dataSources._dataSources).filter(
                (ds) => ds instanceof PivotDataSource
            ).length,
        2
    );
});

QUnit.test("Add a pivot in another sheet", async (assert) => {
    const { definition: def1, dataSource: ds1 } = await getPivotReady(alice, "1");
    alice.dispatch("CREATE_SHEET", {
        sheetId: "sheetId",
        name: "Sheet",
    });
    alice.dispatch("ACTIVATE_SHEET", {
        sheetIdFrom: alice.getters.getActiveSheetId(),
        sheetIdTo: "sheetId",
    });
    insertPreloadedPivot(alice, {
        definition: def1,
        dataSource: ds1,
        pivotId: "1",
    });
    assert.spreadsheetIsSynchronized([alice, bob, charlie], (user) => user.getters.getPivotIds(), [
        "1",
    ]);
    // Let the evaluation and the data sources do what they need to do
    // before Bob and Charlie activate the second sheet to see the new pivot.
    await nextTick();
    bob.dispatch("ACTIVATE_SHEET", {
        sheetIdFrom: alice.getters.getActiveSheetId(),
        sheetIdTo: "sheetId",
    });
    charlie.dispatch("ACTIVATE_SHEET", {
        sheetIdFrom: alice.getters.getActiveSheetId(),
        sheetIdTo: "sheetId",
    });
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => getCellFormula(user, "B1"),
        `=ODOO.PIVOT.HEADER(1,"foo",1)`
    );

    assert.spreadsheetIsSynchronized([alice, bob, charlie], (user) => getCellValue(user, "B4"), 11);
    assert.spreadsheetIsSynchronized([alice, bob, charlie], (user) => getCellValue(user, "B1"), 1);
});

QUnit.test("Rename and remove a pivot concurrently", async (assert) => {
    await insertPivot(alice);
    await network.concurrent(() => {
        alice.dispatch("RENAME_ODOO_PIVOT", {
            pivotId: "1",
            name: "test",
        });
        bob.dispatch("REMOVE_PIVOT", {
            pivotId: "1",
        });
    });
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => user.getters.getPivotIds().length,
        0
    );
});

QUnit.test("Re-insert and remove a pivot concurrently", async (assert) => {
    await insertPivot(alice);
    await network.concurrent(() => {
        const structure = alice.getters.getPivotDataSource("1").getTableStructure();
        const table = structure.export();
        alice.dispatch("RE_INSERT_PIVOT", {
            id: "1",
            col: 0,
            row: 0,
            sheetId: alice.getters.getActiveSheetId(),
            table,
        });
        bob.dispatch("REMOVE_PIVOT", {
            pivotId: "1",
        });
    });
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => user.getters.getPivotIds().length,
        0
    );
});
