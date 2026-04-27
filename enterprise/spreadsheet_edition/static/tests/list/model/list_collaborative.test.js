import { beforeEach, describe, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels, getBasicServerData } from "@spreadsheet/../tests/helpers/data";
import {
    getCellContent,
    getCellFormula,
    getCellValue,
} from "@spreadsheet/../tests/helpers/getters";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { ListUIPlugin } from "@spreadsheet/list";
import {
    setupCollaborativeEnv,
    spExpect,
} from "@spreadsheet_edition/../tests/helpers/collaborative_helpers";

describe.current.tags("headless");
defineSpreadsheetModels();

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

beforeEach(async () => {
    ({ alice, bob, charlie, network } = await setupCollaborativeEnv(getBasicServerData()));
});

test("Add a list", async () => {
    insertList(alice, "1");
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getListIds().length,
        1
    );
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => getCellValue(user, "A4"),
        "Loading..."
    );
    await animationFrame();
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue((user) => getCellValue(user, "A4"), 17);
});

test("Add two lists concurrently", async () => {
    await network.concurrent(() => {
        insertList(alice, "1");
        insertList(bob, "1", [0, 25]);
    });
    await waitForDataLoaded(alice);
    await waitForDataLoaded(bob);
    await waitForDataLoaded(charlie);
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getListIds(),
        ["1", "2"]
    );
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => getCellFormula(user, "A1"),
        `=ODOO.LIST.HEADER(1,"foo")`
    );
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => getCellFormula(user, "A26"),
        `=ODOO.LIST.HEADER(2,"foo")`
    );
    await animationFrame();

    spExpect([alice, bob, charlie]).toHaveSynchronizedValue((user) => getCellValue(user, "A4"), 17);
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => getCellValue(user, "A29"),
        17
    );
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue((user) => {
        const UIPlugin = user["handlers"].find(
            (handler) => handler instanceof ListUIPlugin,
            undefined
        );
        return Object.keys(UIPlugin.lists).length;
    }, 2);
});

test("Can undo a command before a INSERT_ODOO_LIST", async () => {
    setCellContent(bob, "A10", "Hello Alice");
    insertList(alice, "1");
    setCellContent(charlie, "A11", "Hello all");
    bob.dispatch("REQUEST_UNDO");
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => getCellContent(user, "A10"),
        ""
    );
});

test("Rename and remove a list concurrently", async () => {
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
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getListIds().length,
        0
    );
});

test("Re-insert and remove a list concurrently", async () => {
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
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getListIds().length,
        0
    );
});

test("remove and update a domain of a list concurrently", async () => {
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
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getListIds().length,
        0
    );
});

test("remove and update a sorting of a list concurrently", async () => {
    insertList(alice, "1");
    await network.concurrent(() => {
        const listDefinition = alice.getters.getListModelDefinition("1");
        alice.dispatch("REMOVE_ODOO_LIST", {
            listId: "1",
        });
        const orderBy = [{ name: "foo", asc: true }];
        bob.dispatch("UPDATE_ODOO_LIST", {
            listId: "1",
            list: {
                ...listDefinition,
                searchParams: {
                    ...listDefinition.searchParams,
                    orderBy: orderBy,
                },
            },
        });
    });
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getListIds().length,
        0
    );
});

test("Duplicate and remove list at the same time concurrently", async () => {
    insertList(alice, "1");
    await network.concurrent(() => {
        bob.dispatch("REMOVE_ODOO_LIST", {
            listId: "1",
        });
        alice.dispatch("DUPLICATE_ODOO_LIST", {
            listId: "1",
            newListId: "2",
        });
    });
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getListIds().length,
        0
    );
});

test("Duplicate list concurrently", async () => {
    insertList(alice, "1");
    await network.concurrent(() => {
        bob.dispatch("DUPLICATE_ODOO_LIST", {
            listId: "1",
            newListId: "2",
        });
        alice.dispatch("DUPLICATE_ODOO_LIST", {
            listId: "1",
            newListId: "2",
        });
    });
    const expectedListIds = ["1", "2", "3"];
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getListIds(),
        expectedListIds
    );
});

test("Duplicate and insert list concurrently", async () => {
    insertList(alice, "1");
    await network.concurrent(() => {
        bob.dispatch("DUPLICATE_ODOO_LIST", {
            listId: "1",
            newListId: "2",
        });
        insertList(alice, "2");
    });
    const expectedListIds = ["1", "2", "3"];
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getListIds(),
        expectedListIds
    );
});
