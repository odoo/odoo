/** @odoo-module **/

import { registries, helpers } from "@odoo/o-spreadsheet";
import { createSpreadsheetTestAction } from "./utils/helpers";
import {
    editInput,
    click,
    patchWithCleanup,
    triggerEvent,
    nextTick,
} from "@web/../tests/helpers/utils";
const { topbarMenuRegistry } = registries;

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

QUnit.module("Spreadsheet Test History Action", {}, function () {
    QUnit.test("Open history version from the menu", async function (assert) {
        const { env } = await createSpreadsheetTestAction(
            "spreadsheet_test_action"
        );
        patchWithCleanup(env.services.action, {
            doAction(action) {
                assert.step(JSON.stringify(action));
            },
        });
        const file = topbarMenuRegistry
            .getAll()
            .find((item) => item.id === "file");
        const showHistory = file.children.find(
            (item) => item.id === "version_history"
        );
        await showHistory.execute(env);
        assert.verifySteps([
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

    QUnit.test("load from the origin value", async function (assert) {
        await createSpreadsheetTestAction("action_open_spreadsheet_history", {
            mockRPC: async function (route, args) {
                if (args.method === "get_spreadsheet_history") {
                    assert.step(`fromSnapshot-${args.args[1]}`);
                }
            },
        });
        assert.verifySteps(["fromSnapshot-false"]);
    });

    QUnit.test("load action from snapshot", async function (assert) {
        await createSpreadsheetTestAction("action_open_spreadsheet_history", {
            mockRPC: async function (route, args) {
                if (args.method === "get_spreadsheet_history") {
                    assert.step(`fromSnapshot-${args.args[1]}`);
                }
            },
            fromSnapshot: true,
        });
        assert.verifySteps(["fromSnapshot-true"]);
    });

    QUnit.test(
        "load from snapshot when missing revisions",
        async function (assert) {
            await createSpreadsheetTestAction(
                "action_open_spreadsheet_history",
                {
                    mockRPC: async function (route, args) {
                        if (args.method === "get_spreadsheet_history") {
                            assert.step(`fromSnapshot-${args.args[1]}`);
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
                        if (args.method === "action_edit") {
                            assert.step(`editAction-${args.model}`);
                            return {
                                type: "ir.actions.client",
                                tag: "spreadsheet_test_action",
                                params: {
                                    spreadsheet_id: 1,
                                },
                            };
                        }
                    },
                }
            );
            assert.verifySteps(["fromSnapshot-false"]);

            let dialog = document.querySelector(".o_dialog");
            assert.ok(dialog !== null, "Dialog to reload with snapshot opened");
            await click(dialog, "button.btn-primary");
            assert.verifySteps(["fromSnapshot-true"]);
            await nextTick();
            dialog = document.querySelector(".o_dialog");
            assert.ok(dialog !== null, "Dialog to warn user of corrupted data");
            await click(dialog, "button.btn-primary");
            assert.verifySteps(["editAction-spreadsheet.test"]);
        }
    );

    QUnit.test("Side panel content", async function (assert) {
        await createSpreadsheetTestAction("action_open_spreadsheet_history", {
            mockRPC: async function (route, args) {
                if (args.method === "get_spreadsheet_history") {
                    const revisions = [];
                    revisions.push(
                        createRevision(revisions, "REMOTE_REVISION", {
                            name: "",
                        })
                    );
                    revisions.push(
                        createRevision(revisions, "REMOTE_REVISION")
                    );
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
        const revisions = document.querySelectorAll(
            ".o-sidePanel .o-version-history-item"
        );
        assert.strictEqual(revisions.length, 3, "3 revisions provided");

        // Revision info
        assert.equal(
            revisions[0].querySelector(".o-version-history-info").textContent,
            "Current Version"
        );
        assert.equal(
            revisions[1].querySelector(".o-version-history-info").textContent,
            "Sep 9, 2023, 2:00 PM",
            "if the revision has a name"
        );
        assert.notOk(
            revisions[2].querySelector(".o-version-history-info"),
            "if the revision has no name"
        );

        // Revision name
        assert.equal(
            revisions[0].querySelector(".o-version-history-item-text input")
                .value,
            "revision 3",
            "if the revision has a name"
        );
        assert.equal(
            revisions[1].querySelector(".o-version-history-item-text input")
                .value,
            "revision 2",
            "if the revision has a name"
        );
        assert.equal(
            revisions[2].querySelector(".o-version-history-item-text input")
                .value,
            "Sep 9, 2023, 2:00 PM",
            "if the revision does not have a name"
        );

        // contributors
        assert.equal(
            revisions[0].querySelector(".o-version-history-item-text input")
                .value,
            "revision 3",
            "if the revision has a name"
        );
        assert.equal(
            revisions[1].querySelector(".o-version-history-item-text input")
                .value,
            "revision 2",
            "if the revision has a name"
        );
        assert.equal(
            revisions[2].querySelector(".o-version-history-item-text input")
                .value,
            "Sep 9, 2023, 2:00 PM",
            "if the revision does not have a name"
        );
    });

    QUnit.test(
        "Side panel click loads the old version",
        async function (assert) {
            const { model } = await createSpreadsheetTestAction(
                "action_open_spreadsheet_history",
                {
                    mockRPC: async function (route, args) {
                        if (args.method === "get_spreadsheet_history") {
                            const revisions = [];
                            revisions.push(
                                createRevision(revisions, "REMOTE_REVISION")
                            );
                            revisions.push(
                                createRevision(revisions, "REMOTE_REVISION")
                            );
                            return {
                                data: {},
                                name: "test",
                                revisions,
                            };
                        }
                    },
                }
            );
            assert.strictEqual(model.getters.getSheetIds().length, 3);
            const revisions = document.querySelectorAll(
                ".o-sidePanel .o-version-history-item"
            );
            // rollback to the before last revision. i.e. undo a CREATE_SHEET
            await click([...revisions].at(-1));
            assert.strictEqual(model.getters.getSheetIds().length, 2);
        }
    );

    QUnit.test(
        "Side panel arrow keys navigates in the history",
        async function (assert) {
            const { model } = await createSpreadsheetTestAction(
                "action_open_spreadsheet_history",
                {
                    mockRPC: async function (route, args) {
                        if (args.method === "get_spreadsheet_history") {
                            const revisions = [];
                            revisions.push(
                                createRevision(revisions, "REMOTE_REVISION")
                            );
                            revisions.push(
                                createRevision(revisions, "REMOTE_REVISION")
                            );
                            revisions.push(
                                createRevision(revisions, "REMOTE_REVISION")
                            );
                            return {
                                data: {},
                                name: "test",
                                revisions,
                            };
                        }
                    },
                }
            );
            assert.strictEqual(model.getters.getSheetIds().length, 4);
            const target = document.querySelector(".o-version-history");
            await triggerEvent(target, null, "keydown", { key: "ArrowDown" });
            assert.strictEqual(model.getters.getSheetIds().length, 3);
            await triggerEvent(target, null, "keydown", { key: "ArrowDown" });
            assert.strictEqual(model.getters.getSheetIds().length, 2);
            await triggerEvent(target, null, "keydown", { key: "ArrowUp" });
            assert.strictEqual(model.getters.getSheetIds().length, 3);
            await triggerEvent(target, null, "keydown", { key: "ArrowUp" });
            assert.strictEqual(model.getters.getSheetIds().length, 4);
        }
    );

    QUnit.test("Load more revisions", async function (assert) {
        await createSpreadsheetTestAction("action_open_spreadsheet_history", {
            mockRPC: async function (route, args) {
                if (args.method === "get_spreadsheet_history") {
                    const revisions = [];
                    for (let i = 0; i < 75; i++) {
                        revisions.push(
                            createRevision(revisions, "REMOTE_REVISION")
                        );
                    }
                    return {
                        data: {},
                        name: "test",
                        revisions,
                    };
                }
            },
        });
        const revisions = document.querySelectorAll(
            ".o-sidePanel .o-version-history-item"
        );
        assert.strictEqual(
            revisions.length,
            50,
            "the first 50 revisions are loaded"
        );
        const loadMore = document.querySelector(
            ".o-sidePanel .o-version-history-load-more"
        );
        assert.ok(loadMore !== null, "Load more button is visible");
        await click(loadMore);
        const newRevisions = document.querySelectorAll(
            ".o-sidePanel .o-version-history-item"
        );
        assert.strictEqual(
            newRevisions.length,
            75,
            "the first 50 revisions are loaded"
        );
    });

    QUnit.test("Side panel > make copy", async function (assert) {
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
                        revisions.push(
                            createRevision(revisions, "REMOTE_REVISION")
                        );
                        return {
                            data: {},
                            name: "test",
                            revisions,
                        };
                    case "fork_history":
                        assert.strictEqual(args.kwargs.revision_id, 999);
                        assert.strictEqual(
                            args.kwargs.spreadsheet_snapshot.revisionId,
                            "I clicked o"
                        );
                        assert.step("forking");
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

        const revisions = document.querySelectorAll(
            ".o-sidePanel .o-version-history-item"
        );
        await click(revisions[1], null);
        await click(revisions[1], ".o-version-history-menu");

        const menuItems = document.querySelectorAll(".o-menu .o-menu-item");
        await click(menuItems[1], null);
        assert.verifySteps(["forking"]);
    });

    QUnit.test("Side panel > rename revision", async function (assert) {
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
                    assert.equal(args.args[0], 1); // spreadsheet Id
                    assert.equal(args.args[1], 1); // revision id
                    assert.equal(args.args[2], "test 11");
                    return true;
                }
            },
        });
        const nameInput = document.querySelector(".o-version-history-input");
        assert.ok(nameInput, "Can rename the revision");
        await click(nameInput);
        await editInput(nameInput, null, "test 11");
        await triggerEvent(nameInput, null, "focusout");
    });

    QUnit.test(
        "closing side panel rolls back to parent action",
        async function (assert) {
            await createSpreadsheetTestAction(
                "action_open_spreadsheet_history",
                {
                    mockRPC: async function (route, args) {
                        if (args.method === "get_spreadsheet_history") {
                            return {
                                data: {},
                                name: "test",
                                revisions: [
                                    createRevision([], "REMOTE_REVISION"),
                                ],
                            };
                        }
                        if (args.method === "action_edit") {
                            assert.step(`editAction-${args.model}`);
                            return {
                                type: "ir.actions.client",
                                tag: "spreadsheet_test_action",
                                params: {
                                    spreadsheet_id: 1,
                                },
                            };
                        }
                    },
                }
            );
            await click(document, ".o-sidePanelClose");
            assert.verifySteps(["editAction-spreadsheet.test"]);
        }
    );
});
