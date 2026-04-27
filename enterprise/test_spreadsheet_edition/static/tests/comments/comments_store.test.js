// Add a test here we can see the message of a currently hidden sheet (should unhide the sheet)
import { defineTestSpreadsheetEditionModels } from "@test_spreadsheet_edition/../tests/helpers/data";
import { describe, expect, test } from "@odoo/hoot";
import { stores } from "@odoo/o-spreadsheet";
import { CommentsStore } from "@spreadsheet_edition/bundle/comments/comments_store";
import { setupWithThreads } from "@test_spreadsheet_edition/../tests/helpers/helpers";

describe.current.tags("headless");
defineTestSpreadsheetEditionModels();

const { CellPopoverStore } = stores;

test("Change thread visibility", async () => {
    const { env } = await setupWithThreads();
    const commentsStore = env.getStore(CommentsStore);
    expect(commentsStore.areCommentsActive).toBe(true);
    commentsStore.toggleComments();
    expect(commentsStore.areCommentsActive).toBe(false);
    commentsStore.toggleComments();
    expect(commentsStore.areCommentsActive).toBe(true);
});

test("Open a comment thread", async () => {
    const { model, env } = await setupWithThreads();
    const commentsStore = env.getStore(CommentsStore);
    model.dispatch("RESIZE_SHEETVIEW", { width: 1000, height: 1000 }); // Require a viewport big enough to display the popover
    const threadId = 1;
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("ADD_COMMENT_THREAD", { sheetId, col: 0, row: 0, threadId });
    commentsStore.openCommentThread(threadId);
    const popoverStore = env.getStore(CellPopoverStore);
    expect(popoverStore.persistentCellPopover.type).toBe("OdooCellComment");
});

test("Opening a thread makes the threads visible", async () => {
    const { model, env } = await setupWithThreads();
    const commentsStore = env.getStore(CommentsStore);
    const popoverStore = env.getStore(CellPopoverStore);
    model.dispatch("RESIZE_SHEETVIEW", { width: 1000, height: 1000 }); // require a viewport to display the popover
    const threadId = 1;
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("ADD_COMMENT_THREAD", { sheetId, col: 0, row: 0, threadId });
    commentsStore.toggleComments();
    expect(popoverStore.persistentCellPopover.type).toBe(undefined);
    commentsStore.openCommentThread(threadId);
    expect(popoverStore.persistentCellPopover.type).toBe("OdooCellComment");
});

test("Scrolling the viewport should close the comments popover", async () => {
    const { model, env } = await setupWithThreads();
    const commentsStore = env.getStore(CommentsStore);
    model.dispatch("RESIZE_SHEETVIEW", { width: 1000, height: 1000 }); // Require a viewport big enough to display the popover
    const threadId = 1;
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("ADD_COMMENT_THREAD", { sheetId, col: 0, row: 0, threadId });
    commentsStore.openCommentThread(threadId);
    const popoverStore = env.getStore(CellPopoverStore);
    expect(popoverStore.persistentCellPopover.type).toBe("OdooCellComment");
    model.dispatch("SET_VIEWPORT_OFFSET", { offsetX: 100, offsetY: 0 });
    expect(popoverStore.persistentCellPopover.type).toBe(undefined);
});

test("Selecting a resolved thread closes the popover", async () => {
    const { model, env } = await setupWithThreads();
    const commentsStore = env.getStore(CommentsStore);
    const popoverStore = env.getStore(CellPopoverStore);
    model.dispatch("RESIZE_SHEETVIEW", { width: 1000, height: 1000 }); // Require a viewport big enough to display the popover
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("ADD_COMMENT_THREAD", { sheetId, col: 0, row: 0, threadId: 1 });
    model.dispatch("ADD_COMMENT_THREAD", { sheetId, col: 0, row: 1, threadId: 2 });
    model.dispatch("EDIT_COMMENT_THREAD", {
        sheetId,
        col: 0,
        row: 1,
        threadId: 2,
        isResolved: true,
    });
    commentsStore.openCommentThread(1);
    expect(popoverStore.persistentCellPopover.type).toBe("OdooCellComment");
    commentsStore.openCommentThread(2);
    expect(popoverStore.persistentCellPopover.type).toBe(undefined);
});
