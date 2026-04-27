import { expect, test } from "@odoo/hoot";
import { animationFrame, mockTimeZone } from "@odoo/hoot-mock";
import { helpers, registries } from "@odoo/o-spreadsheet";
import { defineTestSpreadsheetEditionModels } from "@test_spreadsheet_edition/../tests/helpers/data";
import { createSpreadsheetTestAction } from "@test_spreadsheet_edition/../tests/helpers/helpers";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { getSpreadsheetActionModel } from "@spreadsheet_edition/../tests/helpers/webclient_helpers";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";

defineTestSpreadsheetEditionModels();

const { topbarMenuRegistry } = registries;

const revisionSelector = ".o-version-history-wrapper .o-version-history-item";
const panelSelector=".o-version-history";
const uuidGenerator = new helpers.UuidGenerator();

function createRevision(revisions, type, payload) {
    const len = revisions.length;
    const commands =
        type === "REMOTE_REVISION"
            ? [
                  {
                      sheetId: uuidGenerator.uuidv4(),
                      position: 0,
                      name: `sheet ${len + 2}`,
                      type: "CREATE_SHEET",
                  },
              ]
            : [];
    return {
        id: len + 1,
        name: `revision ${len + 1}`,
        serverRevisionId: revisions.at(-1)?.nextRevisionId || "START_REVISION",
        nextRevisionId: uuidGenerator.uuidv4(),
        version: "1",
        timestamp: "2023-09-09 13:00:00",
        user: [2, "Superman"],
        type,
        commands,
        ...payload,
    };
}

/**
 * 
 * @param {SpreadsheetAction} action 
 * @returns {Model}
 */
function actionModel(action) {
    return getSpreadsheetActionModel(action);
}

test("Open history version from the menu", async function () {
    const { env } = await createSpreadsheetTestAction("spreadsheet_test_action");
    patchWithCleanup(env.services.action, {
        doAction(action) {
            expect.step(JSON.stringify(action));
        },
    });
    const file = topbarMenuRegistry.getAll().find((item) => item.id === "file");
    const showHistory = file.children.find((item) => item.id === "version_history");
    await showHistory.execute(env);
    expect.verifySteps([
        JSON.stringify({
            type: "ir.actions.client",
            tag: "action_open_spreadsheet_history",
            params: {
                spreadsheet_id: 1,
                res_model: "spreadsheet.test",
            },
        }),
    ]);
});

test("load from the origin value", async function () {
    await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                expect.step(`fromSnapshot-${args.args[1]}`);
            }
        },
    });
    expect.verifySteps(["fromSnapshot-false"]);
});

test("load action from snapshot", async function () {
    await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                expect.step(`fromSnapshot-${args.args[1]}`);
            }
        },
        fromSnapshot: true,
    });
    expect.verifySteps(["fromSnapshot-true"]);
});

test("load from snapshot when missing revisions", async function () {
    await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                expect.step(`fromSnapshot-${args.args[1]}`);
                return {
                    data: {},
                    name: "test",
                    revisions: [
                        createRevision([], "REMOTE_REVISION", {
                            serverRevisionId: "wrong revision id",
                        }),
                    ],
                };
            }
            if (args.method === "action_open_spreadsheet") {
                expect.step(`editAction-${args.model}`);
                return {
                    type: "ir.actions.client",
                    tag: "spreadsheet_test_action",
                    params: {
                        spreadsheet_id: 1,
                    },
                };
            }
        },
    });
    expect.verifySteps(["fromSnapshot-false"]);

    let dialog = document.querySelector(".o_dialog");
    expect(dialog).not.toBe(null, { message: "Dialog to reload with snapshot opened" });
    await contains(dialog.querySelector("button.btn-primary")).click();
    expect.verifySteps(["fromSnapshot-true"]);
    await animationFrame();
    dialog = document.querySelector(".o_dialog");
    expect(dialog).not.toBe(null, { message: "Dialog to warn user of corrupted data" });
    await contains(dialog.querySelector("button.btn-primary")).click();
    expect.verifySteps(["editAction-spreadsheet.test"]);
});

test("Side panel content", async function () {
    mockTimeZone(+1);
    await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                const revisions = [];
                revisions.push(
                    createRevision(revisions, "REMOTE_REVISION", {
                        name: "",
                    })
                );
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                revisions.push(
                    createRevision(revisions, "REMOTE_REVISION", {
                        user: [3, "Supergirl"],
                    })
                );
                return {
                    data: {},
                    name: "test",
                    revisions,
                };
            }
        },
    });
    expect(revisionSelector).toHaveCount(4, {
        message: "3 revisions provided + initial state",
    });

    // Revision info
    expect(`${revisionSelector}:eq(0) .o-sp-badge`).toHaveText("Current");
    expect(`${revisionSelector}:eq(1) .o-version-history-timestamp`).toHaveText(
        "Sep 9, 2023, 2:00 PM",
        { message: "if the revision has a name" }
    );
    expect(`${revisionSelector}:eq(2) .o-version-history-timestamp`).toHaveCount(0, {
        message: "if the revision has no name",
    });

    // Revision name
    expect(`${revisionSelector}:eq(0) .o-version-history-item-text input`).toHaveValue(
        "revision 3",
        { message: "if the revision has a name" }
    );
    expect(`${revisionSelector}:eq(1) .o-version-history-item-text input`).toHaveValue(
        "revision 2",
        { message: "if the revision has a name" }
    );
    expect(`${revisionSelector}:eq(2) .o-version-history-item-text input`).toHaveValue(
        "Sep 9, 2023, 2:00 PM",
        { message: "if the revision does not have a name" }
    );

    // contributors
    expect(`${revisionSelector}:eq(0) .o-version-history-item-text input`).toHaveValue(
        "revision 3",
        { message: "if the revision has a name" }
    );
    expect(`${revisionSelector}:eq(1) .o-version-history-item-text input`).toHaveValue(
        "revision 2",
        { message: "if the revision has a name" }
    );
    expect(`${revisionSelector}:eq(2) .o-version-history-item-text input`).toHaveValue(
        "Sep 9, 2023, 2:00 PM",
        { message: "if the revision does not have a name" }
    );
});

test("Clicking on initial state resets the data without any revisions", async function () {
    const { action } = await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                const revisions = [];
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                return {
                    data: {},
                    name: "test",
                    revisions,
                };
            }
        },
    });
    expect(actionModel(action).getters.getSheetIds().length).toBe(3);
    // rollback to before the first revision. i.e. undo all changes
    await contains(`${revisionSelector}:last`).click();
    expect(actionModel(action).getters.getSheetIds().length).toBe(1);
});

test("Side panel click loads the old version", async function () {
    const { action } = await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                const revisions = [];
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                return {
                    data: {},
                    name: "test",
                    revisions,
                };
            }
        },
    });
    expect(actionModel(action).getters.getSheetIds().length).toBe(3);
    // rollback to the before last revision. i.e. undo a CREATE_SHEET
    await contains(`${revisionSelector}:eq(-2)`).click();
    expect(actionModel(action).getters.getSheetIds().length).toBe(2);
});

test("Side panel arrow keys navigates in the history", async function () {
    const { action } = await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                const revisions = [];
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                return {
                    data: {},
                    name: "test",
                    revisions,
                };
            }
        },
    });
    expect(actionModel(action).getters.getSheetIds().length).toBe(4);
    const target = () => document.querySelector(".o-version-history");
    await contains(target()).press("ArrowDown");
    expect(actionModel(action).getters.getSheetIds().length).toBe(3);
    await contains(target()).press("ArrowDown");
    expect(actionModel(action).getters.getSheetIds().length).toBe(2);
    await contains(target()).press("ArrowUp");
    expect(actionModel(action).getters.getSheetIds().length).toBe(3);
    await contains(target()).press("ArrowUp");
    expect(actionModel(action).getters.getSheetIds().length).toBe(4);
});

test("Load more revisions", async function () {
    await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                const revisions = [];
                for (let i = 0; i < 75; i++) {
                    revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                }
                return {
                    data: {},
                    name: "test",
                    revisions,
                };
            }
        },
    });
    expect(revisionSelector).toHaveCount(50, { message: "the first 50 revisions are loaded" });
    const loadMore = document.querySelector(".o-version-history-wrapper .o-version-history-load-more");
    expect(loadMore).not.toBe(null, { message: "Load more button is visible" });
    await contains(loadMore).click();
    expect(revisionSelector).toHaveCount(76, {
        message: "the first 50 revisions are loaded + the initial state",
    });
});

test("Side panel > make copy", async function () {
    await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            switch (args.method) {
                case "get_spreadsheet_history":
                    const revisions = [];
                    revisions.push(
                        createRevision(revisions, "REMOTE_REVISION", {
                            id: 999,
                            nextRevisionId: "I clicked o",
                        })
                    );
                    revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                    return {
                        data: {},
                        name: "test",
                        revisions,
                    };
                case "fork_history":
                    expect(args.kwargs.revision_id).toBe(999);
                    expect(args.kwargs.spreadsheet_snapshot.revisionId).toBe("I clicked o");
                    expect.step("forking");
                    // placeholder return
                    return {
                        type: "ir.actions.client",
                        tag: "reload",
                    };
                default:
                    break;
            }
        },
    });

    await contains(`${revisionSelector}:eq(1)`).click();
    await contains(`${revisionSelector}:eq(1) .o-version-history-menu`).click();

    const menuItems = document.querySelectorAll(".o_popover .o-dropdown-item");
    await contains(menuItems[0]).click();
    expect.verifySteps(["forking"]);
});

test("Side panel > rename revision", async function () {
    await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                return {
                    data: {},
                    name: "test",
                    revisions: [createRevision([], "REMOTE_REVISION")],
                };
            }
            if (args.method === "rename_revision") {
                expect.step("renamed");
                expect(args.args[0]).toBe(1); // spreadsheet Id
                expect(args.args[1]).toBe(1); // revision id
                expect(args.args[2]).toBe("test 11");
                return true;
            }
        },
    });
    const nameInput = document.querySelector(".o-version-history-item-text input");
    expect(nameInput).not.toBe(null, { message: "Can rename the revision" });
    await contains(nameInput).click();
    await contains(nameInput).edit("test 11");
    expect.verifySteps(["renamed"]);
});

test("First revision should not be editable", async function () {
    await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                return {
                    data: {},
                    name: "test",
                    revisions: [createRevision([], "REMOTE_REVISION")],
                };
            }
        },
    });

    const historyItems = document.querySelectorAll(".o-version-history-item-text");
    expect(historyItems).toHaveCount(2); // One should be an input, the other a span
    expect(historyItems[0].querySelector("input")).toHaveCount(1);
    expect(historyItems[1].querySelector("span")).toHaveCount(1);
    expect(historyItems[0].querySelector("span")).toBe(null);
    expect(historyItems[1].querySelector("input")).toBe(null);
});

test("Side panel > restore revision and confirm", async function () {
    await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            switch (args.method) {
                case "get_spreadsheet_history":
                    const revisions = [];
                    revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                    revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                    return {
                        data: {},
                        name: "test",
                        revisions,
                    };
                case "restore_spreadsheet_version":
                    expect.step("restored");
                    expect(args.kwargs.revision_id).toBe(1);
                    // placeholder return
                    return {
                        type: "ir.actions.client",
                        tag: "reload",
                    };
                default:
                    break;
            }
        },
    });
    await contains(`${revisionSelector}:eq(1)`).click();
    await contains(`${revisionSelector}:eq(1) .o-version-history-menu`).click();
    await contains(".o_popover .o-dropdown-item:eq(1)").click();
    await contains(".o_dialog .btn-primary").click();

    expect.verifySteps(["restored"]);
});

test("Side panel > restore revision and cancel", async function () {
    await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            switch (args.method) {
                case "get_spreadsheet_history":
                    const revisions = [];
                    revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                    revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                    return {
                        data: {},
                        name: "test",
                        revisions,
                    };
                case "restore_spreadsheet_version":
                    throw new Error("should not be called");
                default:
                    break;
            }
        },
    });
    await contains(`${revisionSelector}:eq(1)`).click();
    await contains(`${revisionSelector}:eq(1) .o-version-history-menu`).click();
    await contains(".o_popover .o-dropdown-item:eq(1)").click();
    await contains(".o_dialog footer .btn:eq(2)").click();

    expect(".o_dialog").toHaveCount(0);
});

test("Side panel > restore revision but copy instead", async function () {
    await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            switch (args.method) {
                case "get_spreadsheet_history":
                    const revisions = [];
                    revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                    revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                    return {
                        data: {},
                        name: "test",
                        revisions,
                    };
                case "fork_history":
                    expect.step("forking");
                    // placeholder return
                    return {
                        type: "ir.actions.client",
                        tag: "reload",
                    };
                case "restore_spreadsheet_version":
                    throw new Error("should not be called");
                default:
                    break;
            }
        },
    });
    await contains(`${revisionSelector}:eq(1)`).click();
    await contains(`${revisionSelector}:eq(1) .o-version-history-menu`).click();
    await contains(".o_popover .o-dropdown-item:eq(1)").click();
    await contains(".o_dialog footer .btn:eq(1)").click();

    expect.verifySteps(["forking"]);
});

test("closing side panel rolls back to parent action", async function () {
    await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                return {
                    data: {},
                    name: "test",
                    revisions: [createRevision([], "REMOTE_REVISION")],
                };
            }
            if (args.method === "action_open_spreadsheet") {
                expect.step(`editAction-${args.model}`);
                return {
                    type: "ir.actions.client",
                    tag: "spreadsheet_test_action",
                    params: {
                        spreadsheet_id: 1,
                    },
                };
            }
        },
    });
    await contains(".o-version-history-wrapper div.header>div:nth-child(2)").click();
    expect.verifySteps(["editAction-spreadsheet.test"]);
});


test("Undo/redo revisions are rolled back", async function () {
    const { action } = await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                const revisions = [];
                revisions.push(
                    createRevision(revisions, "REMOTE_REVISION", { name: "Create sheet" }),
                );
                const originalRevId = revisions.at(-1).nextRevisionId;
                revisions.push(
                    createRevision(revisions, "REVISION_UNDONE", {
                        name: "Undo sheet creation",
                        commands: undefined,
                        undoneRevisionId: originalRevId,
                    }),
                );
                revisions.push(
                    createRevision(revisions, "REVISION_REDONE", {
                        name: "Redo sheet creation",
                        commands: undefined,
                        redoneRevisionId: originalRevId,
                    }),
                );
                return { data: {}, name: "test", revisions };
            }
        },
    });
    expect(actionModel(action).getters.getSheetIds().length).toBe(2);

    await contains(panelSelector).press("ArrowDown");
    expect(actionModel(action).getters.getSheetIds().length).toBe(1);
    await contains(panelSelector).press("ArrowDown");
    expect(actionModel(action).getters.getSheetIds().length).toBe(2);
    await contains(panelSelector).press("ArrowUp");
    expect(actionModel(action).getters.getSheetIds().length).toBe(1);
    await contains(panelSelector).press("ArrowUp");
    expect(actionModel(action).getters.getSheetIds().length).toBe(2);
});

test("Datasources are re-evaluated if their domain is altered", async function () {
    const { action } = await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                const revisions = [];
                revisions.push(
                    createRevision(revisions, "REMOTE_REVISION", { name: "Create sheet" }),
                );
                revisions.push(
                    createRevision(revisions, "REMOTE_REVISION", {
                        name: "edit list definition",
                        commands: [
                            {
                                listId: "1",
                                domain: [["name", "=", "test"]],
                                type: "UPDATE_ODOO_LIST_DOMAIN",
                            },
                        ],
                    }),
                );
                return {
                    data: {
                        version: 14,
                        sheets: [
                            {
                                id: "sh1",
                                name: "Sheet 1",
                                cells: {
                                    A1: { content: '=ODOO.LIST(1,1,"name")' },
                                },
                            },
                        ],
                        lists: {
                            1: {
                                columns: ["name"],
                                domain: [["name", "=", "tabouret"]],
                                model: "partner",
                                context: {},
                                orderBy: [],
                                id: "1",
                                name: "Pipeline",
                                fieldMatching: {},
                            },
                        },
                    },
                    name: "test",
                    revisions,
                };
            }
            if (args.method === "web_search_read") {
                expect.step(JSON.stringify(args.kwargs.domain));
            }
        },
    });
    expect(actionModel(action).getters.getListDefinition("1").domain).toEqual([
        ["name", "=", "test"],
    ]);
    await contains(panelSelector).press("ArrowDown");
    await waitForDataLoaded(actionModel(action));
    expect(actionModel(action).getters.getListDefinition("1").domain).toEqual([
        ["name", "=", "tabouret"],
    ]);
    await contains(panelSelector).press("ArrowUp");
    await waitForDataLoaded(actionModel(action));
    expect(actionModel(action).getters.getListDefinition("1").domain).toEqual([
        ["name", "=", "test"],
    ]);
    expect.verifySteps([
        `[["name","=","test"]]`,
        `[["name","=","tabouret"]]`,
        `[["name","=","test"]]`,
    ]);
});

test("Selection and scroll are preserved when switching revision", async function () {
    const { action } = await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                const revisions = [];
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                return { data: {}, name: "test", revisions };
            }
        },
    });
    let model = actionModel(action);
    const sheetIds = model.getters.getSheetIds();
    model.dispatch("ACTIVATE_SHEET", {
        sheetIdFrom: model.getters.getActiveSheetId(),
        sheetIdTo: sheetIds[2],
    });
    model.selection.selectCell(5, 5);
    model.dispatch("SET_VIEWPORT_OFFSET", { offsetX: 30, offsetY: 30 });
    await animationFrame();

    // rollback to the before last revision. i.e. undo a CREATE_SHEET in the first spot
    // -> the first sheet is deleted
    await contains(`${revisionSelector}:eq(1)`).click();
    await animationFrame();
    await animationFrame();
    model = actionModel(action);

    expect(model.getters.getActivePosition()).toEqual({ sheetId: sheetIds[2], row: 5, col: 5 });
    expect(model.getters.getActiveSheetDOMScrollInfo()).toEqual({ scrollX: 30, scrollY: 30 });
});


test("Default currency is provided to the model", async function () {
    const default_currency = {
        id: 1,
        name: "Euro",
        symbol: "€",
        position: "after",
        decimalPlaces: 2,
    };
    const { action } = await createSpreadsheetTestAction("action_open_spreadsheet_history", {
        mockRPC: async function (route, args) {
            if (args.method === "get_spreadsheet_history") {
                const revisions = [];
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                revisions.push(createRevision(revisions, "REMOTE_REVISION"));
                return { data: {}, name: "test", revisions, default_currency };
            }
            if (args.method === "get_company_currency_for_spreadsheet") {
                expect.step("get_default_currency");
            }
        },
    });
    const model = actionModel(action);
    expect(model.getters.getCompanyCurrencyFormat()).toEqual("#,##0.00[$€]");
    expect.verifySteps([]);
});
