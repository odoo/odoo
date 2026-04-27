import { beforeEach, describe, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { defineSpreadsheetModels, getBasicServerData } from "@spreadsheet/../tests/helpers/data";
import {
    getCellContent,
    getCellFormula,
    getCellValue,
} from "@spreadsheet/../tests/helpers/getters";
import {
    insertPivot,
    setupCollaborativeEnv,
    spExpect,
} from "@spreadsheet_edition/../tests/helpers/collaborative_helpers";

describe.current.tags("headless");
defineSpreadsheetModels();

/**
 * @typedef {import("@spreadsheet").OdooSpreadsheetModel} Model
 * @typedef {import("@spreadsheet").OdooPivotDefinition} OdooPivotDefinition
 */

let alice, bob, charlie, network;

beforeEach(async () => {
    ({ alice, bob, charlie, network } = await setupCollaborativeEnv(getBasicServerData()));
});

test("Rename a pivot", async () => {
    await insertPivot(alice);
    alice.dispatch("RENAME_PIVOT", { pivotId: "PIVOT#1", name: "Test" });
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getPivotName("PIVOT#1"),
        "Test"
    );
});

test("Add a pivot", async () => {
    await insertPivot(alice);
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getPivotIds().length,
        1
    );
    const cellFormulas = {
        B1: `=PIVOT.HEADER(1,"foo",1)`, // header col
        A3: `=PIVOT.HEADER(1,"bar",FALSE)`, // header row
        B2: `=PIVOT.HEADER(1,"foo",1,"measure","probability:sum")`, // measure
        B3: `=PIVOT.VALUE(1,"probability:sum","bar",FALSE,"foo",1)`, // value
        F1: `=PIVOT.HEADER(1)`, // total header rows
        A5: `=PIVOT.HEADER(1)`, // total header cols
    };
    for (const [cellXc, formula] of Object.entries(cellFormulas)) {
        spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
            (user) => getCellContent(user, cellXc),
            formula
        );
    }
});

test("Add a pivot in another sheet", async () => {
    alice.dispatch("CREATE_SHEET", {
        sheetId: "sheetId",
        name: "Sheet",
    });
    alice.dispatch("ACTIVATE_SHEET", {
        sheetIdFrom: alice.getters.getActiveSheetId(),
        sheetIdTo: "sheetId",
    });
    insertPivot(alice, "sheetId");
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getPivotIds(),
        ["PIVOT#1"]
    );
    // Let the evaluation and the data sources do what they need to do
    // before Bob and Charlie activate the second sheet to see the new pivot.
    await animationFrame();
    bob.dispatch("ACTIVATE_SHEET", {
        sheetIdFrom: alice.getters.getActiveSheetId(),
        sheetIdTo: "sheetId",
    });
    charlie.dispatch("ACTIVATE_SHEET", {
        sheetIdFrom: alice.getters.getActiveSheetId(),
        sheetIdTo: "sheetId",
    });
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => getCellFormula(user, "B1"),
        `=PIVOT.HEADER(1,"foo",1)`
    );

    spExpect([alice, bob, charlie]).toHaveSynchronizedValue((user) => getCellValue(user, "B4"), 11);
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue((user) => getCellValue(user, "B1"), 1);
});

test("Rename and remove a pivot concurrently", async () => {
    await insertPivot(alice);
    await network.concurrent(() => {
        alice.dispatch("RENAME_PIVOT", {
            pivotId: "PIVOT#1",
            name: "test",
        });
        bob.dispatch("REMOVE_PIVOT", {
            pivotId: "PIVOT#1",
        });
    });
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getPivotIds().length,
        0
    );
});

test("Insert and remove a pivot concurrently", async () => {
    await insertPivot(alice);
    await network.concurrent(() => {
        const table = alice.getters.getPivot("PIVOT#1").getTableStructure().export();
        alice.dispatch("INSERT_PIVOT", {
            pivotId: "PIVOT#1",
            col: 0,
            row: 0,
            sheetId: alice.getters.getActiveSheetId(),
            table,
        });
        bob.dispatch("REMOVE_PIVOT", {
            pivotId: "PIVOT#1",
        });
    });
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getPivotIds().length,
        0
    );
});

test("update and remove a pivot concurrently", async () => {
    await insertPivot(alice);
    await network.concurrent(() => {
        alice.dispatch("UPDATE_PIVOT", {
            pivotId: "PIVOT#1",
            pivot: {
                type: "ODOO",
                ...alice.getters.getPivotCoreDefinition("PIVOT#1"),
                columns: [],
            },
        });
        bob.dispatch("REMOVE_PIVOT", {
            pivotId: "PIVOT#1",
        });
    });
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getPivotIds().length,
        0
    );
});

test("Duplicate and remove a pivot concurrently", async () => {
    await insertPivot(alice);
    await network.concurrent(() => {
        bob.dispatch("REMOVE_PIVOT", {
            pivotId: "PIVOT#1",
        });
        alice.dispatch("DUPLICATE_PIVOT", {
            pivotId: "PIVOT#1",
            newPivotId: "2",
        });
    });
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getPivotIds().length,
        0
    );
});
