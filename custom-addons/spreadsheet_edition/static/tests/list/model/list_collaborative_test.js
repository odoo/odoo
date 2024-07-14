/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";

import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { getCellContent, getCellFormula, getCellValue } from "@spreadsheet/../tests/utils/getters";
import { setCellContent } from "@spreadsheet/../tests/utils/commands";
import { setupCollaborativeEnv } from "../../utils/collaborative_helpers";
import { ListDataSource } from "@spreadsheet/list/list_data_source";
import { waitForDataSourcesLoaded } from "@spreadsheet/../tests/utils/model";

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

function insertList(model, id, anchor = [0, 0]) {
    const { definition, columns } = getListPayload();
    return model.dispatch("INSERT_ODOO_LIST", {
        sheetId: model.getters.getActiveSheetId(),
        col: anchor[0],
        row: anchor[1],
        id,
        definition,
        columns,
        linesNumber: 5,
    });
}

function getListPayload() {
    return {
        definition: {
            metaData: {
                resModel: "partner",
                columns: ["foo", "probability"],
            },
            searchParams: {
                domain: [],
                context: {},
                orderBy: [],
            },
            limit: 5,
        },
        columns: [
            { name: "foo", type: "integer" },
            { name: "probability", type: "integer" },
        ],
    };
}

let alice, bob, charlie, network;

QUnit.module("spreadsheet_edition > List collaborative", {
    async beforeEach() {
        const env = await setupCollaborativeEnv(getBasicServerData());
        alice = env.alice;
        bob = env.bob;
        charlie = env.charlie;
        network = env.network;
    },
});

QUnit.test("Add a list", async (assert) => {
    insertList(alice, "1");
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => user.getters.getListIds().length,
        1
    );
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => getCellValue(user, "A4"),
        "Loading..."
    );
    await nextTick();
    assert.spreadsheetIsSynchronized([alice, bob, charlie], (user) => getCellValue(user, "A4"), 17);
});

QUnit.test("Add two lists concurrently", async (assert) => {
    assert.expect(6);
    await network.concurrent(() => {
        insertList(alice, "1");
        insertList(bob, "1", [0, 25]);
    });
    await waitForDataSourcesLoaded(alice);
    await waitForDataSourcesLoaded(bob);
    await waitForDataSourcesLoaded(charlie);
    assert.spreadsheetIsSynchronized([alice, bob, charlie], (user) => user.getters.getListIds(), [
        "1",
        "2",
    ]);
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => getCellFormula(user, "A1"),
        `=ODOO.LIST.HEADER(1,"foo")`
    );
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => getCellFormula(user, "A26"),
        `=ODOO.LIST.HEADER(2,"foo")`
    );
    await nextTick();

    assert.spreadsheetIsSynchronized([alice, bob, charlie], (user) => getCellValue(user, "A4"), 17);
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => getCellValue(user, "A29"),
        17
    );
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) =>
            Object.values(user.config.custom.dataSources._dataSources).filter(
                (ds) => ds instanceof ListDataSource
            ).length,
        2
    );
});

QUnit.test("Can undo a command before a INSERT_ODOO_LIST", async (assert) => {
    assert.expect(1);
    setCellContent(bob, "A10", "Hello Alice");
    insertList(alice, "1");
    setCellContent(charlie, "A11", "Hello all");
    bob.dispatch("REQUEST_UNDO");
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => getCellContent(user, "A10"),
        ""
    );
});

QUnit.test("Rename and remove a list concurrently", async (assert) => {
    insertList(alice, "1");
    await network.concurrent(() => {
        alice.dispatch("RENAME_ODOO_LIST", {
            listId: "1",
            name: "test",
        });
        bob.dispatch("REMOVE_ODOO_LIST", {
            listId: "1",
        });
    });
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => user.getters.getListIds().length,
        0
    );
});

QUnit.test("Re-insert and remove a list concurrently", async (assert) => {
    insertList(alice, "1");
    await network.concurrent(() => {
        const { columns } = getListPayload();
        alice.dispatch("RE_INSERT_ODOO_LIST", {
            id: "1",
            col: 0,
            row: 0,
            sheetId: alice.getters.getActiveSheetId(),
            linesNumber: 5,
            columns,
        });
        bob.dispatch("REMOVE_ODOO_LIST", {
            listId: "1",
        });
    });
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => user.getters.getListIds().length,
        0
    );
});

QUnit.test("remove and update a domain of a list concurrently", async (assert) => {
    insertList(alice, "1");
    await network.concurrent(() => {
        alice.dispatch("REMOVE_ODOO_LIST", {
            listId: "1",
        });
        bob.dispatch("UPDATE_ODOO_LIST_DOMAIN", {
            listId: "1",
            domain: [["foo", "in", [55]]],
        });
    });
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => user.getters.getListIds().length,
        0
    );
});
