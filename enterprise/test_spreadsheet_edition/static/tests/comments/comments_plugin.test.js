import { describe, expect, test } from "@odoo/hoot";
import { Model, helpers } from "@odoo/o-spreadsheet";
import { addColumns, deleteColumns, redo, undo } from "@spreadsheet/../tests/helpers/commands";
import { getBasicServerData } from "@spreadsheet/../tests/helpers/data";
import {
    setupCollaborativeEnv,
    spExpect,
} from "@spreadsheet_edition/../tests/helpers/collaborative_helpers";
import { defineTestSpreadsheetEditionModels } from "@test_spreadsheet_edition/../tests/helpers/data";

describe.current.tags("headless");
defineTestSpreadsheetEditionModels();

const { toCartesian, toZone } = helpers;

test("Simple thread creation", () => {
    const model = new Model({ sheets: [{ id: "sh1" }] });
    const threadId = 1;
    const cellPosition = { sheetId: "sh1", ...toCartesian("A1") };

    model.dispatch("ADD_COMMENT_THREAD", { ...cellPosition, threadId });
    expect(model.getters.getThreadInfo(threadId)).toEqual({
        ...cellPosition,
        threadId,
        isResolved: false,
    });
    const threadIds = model.getters.getCellThreads(cellPosition);
    expect(threadIds).toEqual([{ threadId, isResolved: false }]);

    undo(model);
    expect(model.getters.getThreadInfo(threadId)).toEqual(undefined);
    expect(model.getters.getCellThreads(cellPosition)).toBe(undefined);

    redo(model);
    expect(model.getters.getThreadInfo(threadId)).toEqual({
        ...cellPosition,
        threadId,
        isResolved: false,
    });
    expect(model.getters.getCellThreads(cellPosition)).toEqual([{ threadId, isResolved: false }]);
});

test("Multiple threads on the same cell", () => {
    const model = new Model({ sheets: [{ id: "sh1" }] });
    const cellPosition = { sheetId: "sh1", ...toCartesian("A1") };

    model.dispatch("ADD_COMMENT_THREAD", { ...cellPosition, threadId: 1 });
    model.dispatch("ADD_COMMENT_THREAD", { ...cellPosition, threadId: 2 });
    const threadIds = model.getters.getCellThreads(cellPosition);
    expect(threadIds).toEqual([
        { threadId: 1, isResolved: false },
        { threadId: 2, isResolved: false },
    ]);
    undo(model);
    expect(model.getters.getCellThreads(cellPosition)).toEqual([
        { threadId: 1, isResolved: false },
    ]);
    undo(model);
    expect(model.getters.getCellThreads(cellPosition)).toBe(undefined);
    redo(model);
    expect(model.getters.getCellThreads(cellPosition)).toEqual([
        { threadId: 1, isResolved: false },
    ]);
    redo(model);
    expect(model.getters.getCellThreads(cellPosition)).toEqual([
        { threadId: 1, isResolved: false },
        { threadId: 2, isResolved: false },
    ]);
});

test("Thread on merged cell", () => {
    const model = new Model();
    const threadId = 1;
    const sheetId = model.getters.getActiveSheetId();
    const cellPosition = { sheetId, ...toCartesian("A1") };
    model.dispatch("ADD_MERGE", {
        sheetId,
        target: [toZone("A1:B2")],
        force: true,
    });
    model.dispatch("ADD_COMMENT_THREAD", { ...cellPosition, threadId });
    expect(model.getters.getThreadInfo(threadId)).toEqual({
        ...cellPosition,
        threadId,
        isResolved: false,
    });
});

test("Thread removed on sheet deletion", () => {
    const model = new Model();
    model.dispatch("CREATE_SHEET", { sheetId: "sh2" });
    model.dispatch("ADD_COMMENT_THREAD", { sheetId: "sh2", col: 1, row: 1, threadId: 1 });
    expect(model.getters.getSpreadsheetThreads(["sh2"])).toEqual([
        { sheetId: "sh2", col: 1, row: 1, threadId: 1, isResolved: false },
    ]);
    model.dispatch("DELETE_SHEET", { sheetId: "sh2" });
    expect(model.getters.getSpreadsheetThreads(["sh2"])).toEqual([]);
});

test("can add a column in a duplicated sheet", () => {
    const model = new Model();
    const activeSheetId = model.getters.getActiveSheetId();
    model.dispatch("DUPLICATE_SHEET", { sheetId: activeSheetId, sheetIdTo: "sh2"});
    addColumns(model, "before", "B", 1, "sh2");
    expect(model.getters.getSpreadsheetThreads(["sh2"])).toEqual([]);
});

test("Thread moved on sheet structure change", () => {
    const model = new Model();
    const threadId = 1;
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("ADD_COMMENT_THREAD", { sheetId, ...toCartesian("B2"), threadId: 1 });
    expect(model.getters.getThreadInfo(threadId)).toEqual({
        sheetId,
        ...toCartesian("B2"),
        threadId,
        isResolved: false,
    });
    addColumns(model, "before", "B", 1);
    expect(model.getters.getThreadInfo(threadId)).toEqual({
        sheetId,
        ...toCartesian("C2"),
        threadId,
        isResolved: false,
    });
    deleteColumns(model, ["C"]);
    expect(model.getters.getThreadInfo(threadId)).toEqual(undefined);
});

test("Can cut/paste a thread", () => {
    const model = new Model();
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("ADD_COMMENT_THREAD", {
        sheetId,
        ...toCartesian("B2"),
        threadId: 1,
    });
    model.selection.selectCell(1, 1);
    model.dispatch("CUT");
    model.dispatch("PASTE", { target: [toZone("C2")] });
    expect(model.getters.getThreadInfo(1)).toEqual({
        sheetId,
        ...toCartesian("C2"),
        threadId: 1,
        isResolved: false,
    });
});

test("Threads are not affected by copy/paste", () => {
    const model = new Model();
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("ADD_COMMENT_THREAD", {
        sheetId,
        ...toCartesian("B2"),
        threadId: 1,
    });
    model.selection.selectCell(1, 1);
    model.dispatch("COPY");
    model.dispatch("PASTE", { target: [toZone("C2")] });
    expect(model.getters.getThreadInfo(1)).toEqual({
        sheetId,
        ...toCartesian("B2"),
        threadId: 1,
        isResolved: false,
    });
});

test("Threads are not affected by paste from clipboard os", () => {
    const model = new Model();
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("ADD_COMMENT_THREAD", {
        sheetId,
        ...toCartesian("B2"),
        threadId: 1,
    });
    model.dispatch("COPY");
    model.selection.selectCell(1, 1);
    model.dispatch("PASTE_FROM_OS_CLIPBOARD", {
        target: [toZone("C2")],
        text: "coucou",
        pasteOption: {},
        clipboardContent: {
            ["text/plain"]: "Copy in OS clipboard",
        },
    });
    model.dispatch("COPY");
    model.dispatch("PASTE", { target: [toZone("C2")] });
    expect(model.getters.getThreadInfo(1)).toEqual({
        sheetId,
        ...toCartesian("B2"),
        threadId: 1,
        isResolved: false,
    });
});

test("Resolve/re-open a thread", () => {
    const model = new Model();
    const threadId = 1;
    const sheetId = model.getters.getActiveSheetId();
    const createPayload = { sheetId, ...toCartesian("B2"), threadId };
    const resolvedThread = { ...createPayload, isResolved: true };
    const openThread = { ...createPayload, isResolved: false };
    model.dispatch("ADD_COMMENT_THREAD", createPayload);
    model.dispatch("EDIT_COMMENT_THREAD", resolvedThread);
    expect(model.getters.getThreadInfo(1)).toEqual(resolvedThread);
    undo(model);
    expect(model.getters.getThreadInfo(1)).toEqual(openThread);
    redo(model);
    expect(model.getters.getThreadInfo(1)).toEqual(resolvedThread);
});

test("Threads are imported/exported", () => {
    const model = new Model();
    const threadId = 1;
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("ADD_COMMENT_THREAD", { sheetId, ...toCartesian("B2"), threadId });

    const newModel = new Model(model.exportData());
    expect(newModel.getters.getSpreadsheetThreads([sheetId])).toEqual([
        { sheetId, ...toCartesian("B2"), threadId, isResolved: false },
    ]);
});

test("collaborative: Insert comment on sheet structure change", async () => {
    const env = await setupCollaborativeEnv(getBasicServerData());
    const { alice, bob, charlie, network } = env;
    const sheetId = alice.getters.getActiveSheetId();

    await network.concurrent(() => {
        addColumns(alice, "before", "B", 1);
        bob.dispatch("ADD_COMMENT_THREAD", { sheetId, col: 4, row: 4, threadId: 1 });
    });

    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getSpreadsheetThreads([sheetId]),
        [{ sheetId, col: 5, row: 4, threadId: 1, isResolved: false }]
    );
});

test("collaborative: Parallel insertion of comments", async () => {
    const env = await setupCollaborativeEnv(getBasicServerData());
    const { alice, bob, charlie, network } = env;
    const sheetId = alice.getters.getActiveSheetId();

    await network.concurrent(() => {
        alice.dispatch("ADD_COMMENT_THREAD", { sheetId, col: 1, row: 1, threadId: 2 });
        bob.dispatch("ADD_COMMENT_THREAD", { sheetId, col: 4, row: 4, threadId: 1 });
    });

    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getSpreadsheetThreads([sheetId]),
        [
            { sheetId, col: 1, row: 1, threadId: 2, isResolved: false },
            { sheetId, col: 4, row: 4, threadId: 1, isResolved: false },
        ]
    );
    undo(alice);
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getSpreadsheetThreads([sheetId]),
        [{ sheetId, col: 4, row: 4, threadId: 1, isResolved: false }]
    );
});
